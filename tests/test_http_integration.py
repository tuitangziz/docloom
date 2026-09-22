"""Real loopback HTTP + Streamlit flow, with an explicitly simulated model."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from streamlit.testing.v1 import AppTest

from docloom.providers import CompatibleAPI


def test_review_then_send_over_real_http():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path, body))
            packet = json.loads(body['messages'][1]['content'])
            quote = packet['sources'][0]['text']
            content = json.dumps({'answer': '这是模拟 API 的集成测试回答。[S1]', 'citations': [{'source_id':'S1', 'quote':quote}], 'insufficient_evidence':False}, ensure_ascii=False)
            raw = json.dumps({'choices':[{'message':{'content':content}}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        next(b for b in app.button if b.label == '载入演示资料').click().run()
        app.text_input(key='api_base').set_value(f'http://127.0.0.1:{server.server_port}/v1')
        app.text_input(key='api_model').set_value('simulated-model')
        app.text_input(key='api_key').set_value('synthetic-integration-key')
        app.text_area(key='question_input').set_value('GPU 工作站提前多久预约')
        next(b for b in app.button if b.label == '检索资料').click().run()
        assert not requests, 'Retrieval must not transmit documents'
        next(b for b in app.button if b.label == '发送片段并生成回答').click().run()
        assert not app.exception
        assert app.session_state.answer.mode == '模型回答'
        assert len(requests) == 1 and requests[0][0] == '/v1/chat/completions'
        assert requests[0][1]['max_tokens'] == 1200
        assert 'synthetic-integration-key' not in json.dumps(requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_modern_api_parameters():
    import httpx
    def handler(request):
        body = json.loads(request.content)
        assert body['max_completion_tokens'] == 1200
        assert 'max_tokens' not in body
        assert body['messages'][0]['role'] == 'developer'
        return httpx.Response(200, json={'choices':[{'message':{'content':'{}'}}]})
    original = [{'role':'system','content':'Test prompt'}]
    provider = CompatibleAPI('https://provider.example/v1', 'test-model', 'synthetic-test-key', httpx.MockTransport(handler), modern_parameters=True)
    provider.complete(original)
    assert original[0]['role'] == 'system'
