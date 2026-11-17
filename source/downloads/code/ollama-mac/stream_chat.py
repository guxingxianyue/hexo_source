"""Stream local Ollama chat and report client-observed latency. Python 3.10+."""

import argparse
import json
import sys
import time
from urllib import error, parse, request


def consume_stream(response, started, output):
    first_visible = None
    final = None
    for raw_line in response:
        if not raw_line.strip():
            continue
        event = json.loads(raw_line)
        if not isinstance(event, dict):
            raise ValueError("Expected an NDJSON object")
        if event.get("error"):
            raise RuntimeError(str(event["error"]))
        message = event.get("message", {})
        if not isinstance(message, dict):
            raise ValueError("Invalid message in stream")
        text = message.get("content", "")
        if not isinstance(text, str):
            raise ValueError("Invalid content in stream")
        if text:
            if first_visible is None:
                first_visible = time.perf_counter() - started
            output.write(text)
            output.flush()
        if event.get("done") is True:
            final = event
            break
    if final is None:
        raise RuntimeError("Connection ended without done=true; output is incomplete")
    output.write("\n")
    if final.get("done_reason") != "stop":
        raise RuntimeError("Generation ended abnormally: " + str(final.get("done_reason")))
    duration = final.get("eval_duration", 0)
    return {
        "first_visible_seconds": round(first_visible, 3) if first_visible is not None else None,
        "client_total_seconds": round(time.perf_counter() - started, 3),
        "load_seconds": round(final.get("load_duration", 0) / 1e9, 3),
        "decode_tokens_per_second": round(final.get("eval_count", 0) * 1e9 / duration, 2)
        if duration > 0 else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    url = parse.urlsplit(args.base_url)
    if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1")
            or url.username or url.password or url.path not in ("", "/")
            or url.query or url.fragment):
        raise ValueError("This demo accepts HTTP loopback addresses only")
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": True, "think": False, "keep_alive": "5m",
        "options": {"num_ctx": 4096, "num_predict": 512},
    }
    req = request.Request(args.base_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    opener = request.build_opener(request.ProxyHandler({}))
    started = time.perf_counter()
    try:
        with opener.open(req, timeout=120) as response:
            stats = consume_stream(response, started, sys.stdout)
    except error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    print(json.dumps(stats, ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
