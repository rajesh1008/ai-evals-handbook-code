"""A tiny OpenAI-compatible chat-completions server for testing the LOCAL-MODEL plumbing without a model.

It is NOT a model. Every reply is a fixed placeholder string, so anything it produces is test data only:
    python3 mock_server.py 8765      # then LOCAL_LLM_BASE_URL=http://127.0.0.1:8765/v1
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPLY = '{"action": "ask_income", "confidence": 50, "groups": [], "codes": {}, "sentences": []}'
CALLS = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return
        CALLS.append(req)
        prompt = " ".join(m.get("content", "") for m in req.get("messages", []))
        body = json.dumps({"id": "mock", "object": "chat.completion", "model": req.get("model", "mock"),
                           "choices": [{"index": 0, "finish_reason": "stop",
                                        "message": {"role": "assistant", "content": REPLY}}],
                           "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": 12}}).encode()
        self.send_response(200); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)


def serve(port=0):
    s = ThreadingHTTPServer(("127.0.0.1", port), H)
    return s


if __name__ == "__main__":
    srv = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
    print(f"mock OpenAI-compatible server on http://127.0.0.1:{srv.server_address[1]}/v1 (placeholder replies only)")
    srv.serve_forever()
