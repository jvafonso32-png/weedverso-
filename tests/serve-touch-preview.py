"""Isolated UI preview: synthetic state in memory, external connections blocked."""
import copy
import json
import mimetypes
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP = Path(__file__).resolve().parents[1] / 'app'
LOCK = threading.Lock()
STATE = {
    'appName': 'weedverso', 'userName': 'Prévia', 'lastDate': datetime.now().strftime('%Y-%m-%d'),
    'xp': 0, 'streak': 0, 'routineDone': False, 'habits': [],
    'balances': {'conta': {'label': 'Conta de teste', 'amount': 1000}, 'vale1': {'label': 'Alimentação teste', 'amount': 300}, 'vale2': {'label': 'Refeição teste', 'amount': 200}},
    'tx': [{'id': 'demo-wallet', 'account': 'conta', 'type': 'out', 'value': 12.5, 'note': 'Almoço de demonstração com descrição completa', 'category': 'Almoço', 'categoryKey': 'almoco', 'at': '2026-10-09T00:30:00Z'}],
    'credit': {'name': 'Cartão de teste', 'used': 100, 'reserved': 60, 'tx': [{'id': 'demo-card', 'type': 'expense', 'value': 100, 'desc': 'Compra de demonstração', 'category': 'Compras', 'categoryKey': 'compras', 'at': '2026-10-07T12:00:00Z'}]},
    'investments': {'total': 500, 'history': [{'type': 'add', 'value': 500, 'balanceAfter': 500, 'note': 'Aporte de demonstração', 'at': '2026-10-07T12:00:00Z'}]},
    'debtors': [{'id': 'demo-debtor', 'name': 'Pessoa de teste', 'amount': 400, 'installmentValue': 100, 'installments': 4, 'installmentsPaid': 0, 'payDate': '2026-11-01', 'paid': False, 'payments': [], 'reason': 'loan'}],
    'myDebts': [{'id': 'demo-debt', 'name': 'Conta de demonstração', 'amount': 100, 'installmentValue': 100, 'installments': 4, 'installmentsPaid': 0, 'payDate': '2026-11-05', 'paid': False, 'payments': [], 'reason': 'house'}],
    'goals': [], 'skills': {}, 'routineLog': [], 'dailyStats': {}, 'focusSession': {'habitId': '', 'secondsLeft': 1500, 'running': False},
    'preserveSentinel': {'mustRemain': 'unchanged'},
}
WRITES = 0

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_body(self, body, mime='application/json', status=200):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "connect-src 'self'")
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data):
        self.send_body(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {'/api/state', '/__test/state'}:
            with LOCK:
                self.send_json(copy.deepcopy(STATE) if path == '/api/state' else {'state': copy.deepcopy(STATE), 'writes': WRITES})
        elif path == '/api/session':
            self.send_json({'authenticated': True, 'authEnabled': False})
        elif path.startswith('/api/'):
            self.send_json({})
        elif path == '/sw.js':
            self.send_body(b'', 'text/javascript', 404)
        else:
            file = (APP / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
            if not file.is_relative_to(APP.resolve()) or not file.is_file():
                self.send_body(b'Not found', 'text/plain', 404)
                return
            body = file.read_bytes()
            if file.name == 'index.html':
                body = body.replace(b'<script>', b'<script>window.WEEDVERSO_API_BASE=location.origin;</script><script>', 1)
                banner = '<div style="max-width:1080px;margin:0 auto 12px;padding:10px;border:1px solid #39ff8f;border-radius:12px;color:#bdf7d4;font-size:13px;line-height:1.4">Prévia local · dados fictícios · nenhuma conexão com seus registros reais</div>'
                body = body.replace(b'<body data-theme="dark">', b'<body data-theme="dark">' + banner.encode('utf-8'), 1)
            self.send_body(body, mimetypes.guess_type(str(file))[0] or 'application/octet-stream')

    def do_PUT(self):
        global STATE, WRITES
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        with LOCK:
            STATE = data
            WRITES += 1
        self.send_json({'ok': True})

    def do_POST(self):
        global STATE, WRITES
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if urlparse(self.path).path == '/api/state-sync' and body:
            with LOCK:
                STATE = json.loads(body)
                WRITES += 1
        self.send_json({'ok': True})

if __name__ == '__main__':
    print('Synthetic preview: http://127.0.0.1:8951 (no production data)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8951), Handler).serve_forever()
