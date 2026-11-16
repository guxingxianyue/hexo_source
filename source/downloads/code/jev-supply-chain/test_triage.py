"""Offline wire-contract and routing tests. No credentials or network calls."""

import copy
import json
import unittest
from pathlib import Path

import httpx2
from typesafe_sdk import RetryPolicy, TypeSafeClient

from triage import MODEL, OWNER_CRITERIA, SEVERITY_LEVELS, build_facts, classify


def fixture() -> dict:
    return {
        "model": MODEL,
        "answers": {
            "owner": {
                "type": "choice",
                "choice": "procurement",
                "confidence": 0.92,
                "probabilities": {"procurement": 0.94, "logistics": 0.02, "quality": 0.02, "finance": 0.02},
            },
            "in_scope": {"type": "noul", "noul": 0.99},
            "impact_known": {"type": "noul", "noul": 0.98},
            "severity": {
                "type": "score",
                "score": 2.75,
                "confidence": 0.75,
                "legend": {str(i): text for i, text in enumerate(SEVERITY_LEVELS)},
                "probabilities": {"0": 0.01, "1": 0.03, "2": 0.16, "3": 0.80},
            },
            "firm_commitment": {"type": "noul", "noul": 0.12},
        },
        "usage": {"input_tokens": 800, "output_tokens": 80},
    }


class TriageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(Path(__file__).with_name("sample-event.json").read_text(encoding="utf-8"))
        self.body = fixture()
        self.calls = []

    def run_classification(self, handler=None) -> dict:
        def transport(request: httpx2.Request) -> httpx2.Response:
            self.calls.append(request)
            if handler:
                return handler(request)
            return httpx2.Response(200, json=self.body)

        with TypeSafeClient(
            api_key="offline-test-key",
            model=MODEL,
            transport=httpx2.MockTransport(transport),
            retry=RetryPolicy(max_retries=1, backoff_initial=0, backoff_max=0),
        ) as client:
            return classify(self.event, client)

    def test_valid_request_and_priority_draft(self) -> None:
        result = self.run_classification()
        self.assertEqual("create_priority_draft", result["mode"])
        self.assertEqual(80, result["facts"]["shortage_qty"])
        request = self.calls[0]
        self.assertEqual("/v1/systemone", request.url.path)
        payload = json.loads(request.content)
        self.assertEqual(MODEL, payload["model"])
        self.assertIsInstance(payload["state"], dict)
        self.assertIsInstance(payload["questions"]["severity"]["criteria"], list)
        self.assertEqual(set(OWNER_CRITERIA), set(payload["questions"]["owner"]["criteria"]))
        self.assertEqual(MODEL, result["actual_model"])

    def test_out_of_scope_overrides_strong_choice(self) -> None:
        self.body["answers"]["in_scope"]["noul"] = 0.02
        self.assertEqual("general_queue", self.run_classification()["mode"])

    def test_ambiguous_owner_goes_to_review(self) -> None:
        self.body["answers"]["owner"]["probabilities"] = {
            "procurement": 0.6, "logistics": 0.2, "quality": 0.1, "finance": 0.1,
        }
        self.assertEqual("manual_review", self.run_classification()["mode"])

    def test_unknown_impact_is_not_treated_as_low_impact(self) -> None:
        self.body["answers"]["impact_known"]["noul"] = 0.4
        self.assertEqual("uncertain_impact", self.run_classification()["reason"])

    def test_unsettled_score_goes_to_review(self) -> None:
        self.body["answers"]["severity"]["confidence"] = 0.2
        self.assertEqual("uncertain_impact", self.run_classification()["reason"])

    def test_boundary_probability_goes_to_review(self) -> None:
        self.body["answers"]["severity"].update(
            score=1.6, confidence=0.6,
            probabilities={"0": 0.0, "1": 0.4, "2": 0.6, "3": 0.0},
        )
        self.assertEqual("impact_near_threshold", self.run_classification()["reason"])

    def test_low_explicit_impact_creates_routine_draft(self) -> None:
        self.body["answers"]["severity"].update(
            score=0.0, confidence=1.0,
            probabilities={"0": 1.0, "1": 0.0, "2": 0.0, "3": 0.0},
        )
        self.assertEqual("create_triage_draft", self.run_classification()["mode"])

    def test_hard_rule_does_not_call_model(self) -> None:
        self.event["as_of"] = "2026-10-06T10:00:00+08:00"
        result = self.run_classification()
        self.assertEqual("erp_overdue_and_shortage", result["reason"])
        self.assertEqual([], self.calls)

    def test_missing_answer_fails_to_review(self) -> None:
        del self.body["answers"]["in_scope"]
        self.assertEqual("manual_review", self.run_classification()["mode"])

    def test_invalid_distribution_fails_to_review(self) -> None:
        self.body["answers"]["owner"]["probabilities"]["procurement"] = 0.1
        self.assertEqual("manual_review", self.run_classification()["mode"])

    def test_rate_limit_is_retried_once(self) -> None:
        def handler(request):
            if len(self.calls) == 1:
                return httpx2.Response(429, headers={"retry-after-ms": "0"}, json={"detail": "test limit"})
            return httpx2.Response(200, json=self.body)

        self.assertEqual("create_priority_draft", self.run_classification(handler)["mode"])
        self.assertEqual(2, len(self.calls))

    def test_unauthorized_is_not_retried(self) -> None:
        result = self.run_classification(
            lambda request: httpx2.Response(401, json={"detail": "test authentication error"})
        )
        self.assertEqual("manual_review", result["mode"])
        self.assertEqual(1, len(self.calls))

    def test_missing_timezone_is_rejected(self) -> None:
        self.event["as_of"] = "2026-10-04T10:00:00"
        with self.assertRaises(ValueError):
            build_facts(self.event)

    def test_timezone_offsets_are_compared_as_instants(self) -> None:
        self.event["as_of"] = "2026-10-05T10:00:01+00:00"
        self.assertTrue(build_facts(self.event).delivery_window_exceeded)

    def test_negative_stock_is_rejected(self) -> None:
        self.event["on_hand_qty"] = -1
        with self.assertRaises(ValueError):
            build_facts(self.event)

    def test_input_is_not_mutated(self) -> None:
        original = copy.deepcopy(self.event)
        self.run_classification()
        self.assertEqual(original, self.event)


if __name__ == "__main__":
    unittest.main(verbosity=2)
