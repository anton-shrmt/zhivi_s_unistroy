"""Local-only QA fixture. Serves the current release with mock endpoints, never CRM.
Run: python3 release_header/qa/final-2026-10-06/form_fixture.py
Use /?qa=success, /?qa=error or /?qa=slow. Synthetic data only.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LOG = HERE / 'mock-requests.jsonl'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        case = parse_qs(parsed.query).get('qa', [''])[0]
        if parsed.path in ['/', '/index.html'] and case in ['success', 'error', 'slow']:
            text = (ROOT / 'index.html').read_text()
            endpoint = '/__qa__/submit?case=' + case
            text = text.replace("endpoint: '',", "endpoint: '" + endpoint + "',", 1)
            text = text.replace('dryRun: true,', 'dryRun: false,', 1)
            config = '<script>window.UNISTROY_HEADER_CONFIG={callbackEndpoint:' + json.dumps(endpoint) + '};</script>'
            text = text.replace('<script src="header/templates.js', config + '\n<script src="header/templates.js', 1)
            data = text.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/__qa__/submit':
            self.send_error(404); return
        case = parse_qs(parsed.query).get('case', ['error'])[0]
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with LOG.open('a') as output:
            output.write(json.dumps({'case':case,'body':data}, ensure_ascii=False)+'\n')
        if case == 'slow': time.sleep(2)
        status = 500 if case == 'error' else 200
        result = json.dumps({'ok':status == 200}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def log_message(self, *args):
        pass

print('QA fixture: http://127.0.0.1:4184/?qa=success', flush=True)
ThreadingHTTPServer(('127.0.0.1', 4184), Handler).serve_forever()
