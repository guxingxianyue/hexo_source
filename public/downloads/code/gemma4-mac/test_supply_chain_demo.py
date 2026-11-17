import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import supply_chain_demo as demo


class DemoTest(unittest.TestCase):
    def setUp(self):
        self.event = json.loads((Path(__file__).parent / "sample-event.json").read_text(encoding="utf-8"))
        self.valid = {
            "issue_type": "delivery_delay",
            "promised_date": None,
            "evidence": "目前争取2026-10-08发货，但暂时不能保证",
            "summary": "交付存在延迟风险，发货日期尚未承诺。",
        }

    def envelope(self, result=None):
        return {"message": {"content": json.dumps(self.valid if result is None else result)},
                "done": True, "done_reason": "stop", "eval_count": 20, "eval_duration": 1_000_000_000}

    def test_inventory_is_calculated_by_code(self):
        self.assertEqual(demo.inventory_facts(self.event),
                         {"available_quantity": 100, "shortage_quantity": 300})

    def test_surplus_does_not_create_negative_shortage(self):
        self.event["required_quantity"] = 50
        self.assertEqual(demo.inventory_facts(self.event)["shortage_quantity"], 0)

    def test_corrupt_inventory_is_rejected(self):
        self.event["locked_quantity"] = 200
        with self.assertRaises(ValueError):
            demo.inventory_facts(self.event)

    def test_boolean_is_not_an_inventory_number(self):
        self.event["required_quantity"] = True
        with self.assertRaises(ValueError):
            demo.inventory_facts(self.event)

    def test_valid_extraction(self):
        self.assertEqual(demo.validate_extraction(self.envelope(), self.event), self.valid)

    def test_fabricated_evidence_is_rejected(self):
        self.valid["evidence"] = "已经确认按时交货"
        with self.assertRaises(ValueError):
            demo.validate_extraction(self.envelope(), self.event)

    def test_invalid_calendar_date_is_rejected(self):
        self.valid["promised_date"] = "2026-02-30"
        with self.assertRaises(ValueError):
            demo.validate_extraction(self.envelope(), self.event)

    def test_extra_fields_are_rejected(self):
        self.valid["execute_payment"] = True
        with self.assertRaises(ValueError):
            demo.validate_extraction(self.envelope(), self.event)

    def test_invalid_enum_is_rejected(self):
        self.valid["issue_type"] = "auto_purchase"
        with self.assertRaises(ValueError):
            demo.validate_extraction(self.envelope(), self.event)

    def test_truncated_json_is_rejected(self):
        with self.assertRaises(ValueError):
            demo.validate_extraction({"message": {"content": "{"}}, self.event)

    def test_empty_summary_is_rejected(self):
        self.valid["summary"] = ""
        with self.assertRaises(ValueError):
            demo.validate_extraction(self.envelope(), self.event)

    def test_no_decode_tokens_has_no_fake_throughput(self):
        self.assertIsNone(demo.metrics({})["output_tokens_per_second"])

    def test_local_http_payload_and_response(self):
        testcase = self
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                data = json.dumps(testcase.envelope()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            payload = demo.build_payload(self.event, "gemma4:e4b")
            result = demo.call_ollama(payload, f"http://127.0.0.1:{server.server_port}")
            self.assertEqual(demo.validate_extraction(result, self.event), self.valid)
            self.assertEqual(captured[0][0], "/api/chat")
            self.assertEqual(captured[0][1]["format"], demo.OUTPUT_SCHEMA)
            self.assertFalse(captured[0][1]["stream"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_remote_url_is_rejected_before_sending(self):
        with self.assertRaises(ValueError):
            demo.call_ollama({}, "http://example.com")


if __name__ == "__main__":
    unittest.main()
