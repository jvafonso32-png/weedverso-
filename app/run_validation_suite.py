from __future__ import annotations

import contextlib
import copy
import importlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Callable


APP_DIR = Path(__file__).resolve().parent
LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import shared_state as shared_state_mod
import share_publish as share_publish_mod
import telegram_bot as telegram_bot_mod


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    duration_ms: int
    extra: dict = field(default_factory=dict)


class ValidationFailure(RuntimeError):
    pass


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise ValidationFailure(f"{message} | esperado={expected!r} atual={actual!r}")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def chunk_text(text: str, max_len: int = 3500) -> list[str]:
    parts: list[str] = []
    current = []
    current_len = 0
    for line in text.splitlines():
        addition = len(line) + 1
        if current and current_len + addition > max_len:
            parts.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += addition
    if current:
        parts.append("\n".join(current))
    return parts or [text]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    def http_error_303(self, req, fp, code, msg, headers):
        return fp

    def http_error_307(self, req, fp, code, msg, headers):
        return fp

    def http_error_308(self, req, fp, code, msg, headers):
        return fp


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_runtime_data(app_copy: Path) -> None:
    data_dir = app_copy / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json(data_dir / "shared_state.json", copy.deepcopy(shared_state_mod.DEFAULT_STATE))
    write_json(
        data_dir / "publish_runtime.json",
        {
            "version": 0,
            "updatedAt": "",
            "reason": "",
            "stateHash": "",
            "lastLinks": {},
            "notifications": {"telegram": "idle", "discord": "idle"},
        },
    )
    write_json(data_dir / "telegram_runtime.json", {"testMode": False, "updatedAt": ""})
    write_json(data_dir / "telegram_chats.json", [])
    test_dir = data_dir / "telegram_test_state"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)


def make_app_copy(temp_root: Path) -> Path:
    target = temp_root / "app"
    shutil.copytree(
        APP_DIR,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "logs", ".env", ".env.recovered-original", "*.pyc", "*.pyo"),
    )
    clean_runtime_data(target)
    return target


def request(
    method: str,
    url: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    allow_redirects: bool = True,
    cookie_jar: CookieJar | None = None,
    timeout: int = 10,
):
    request_obj = urllib.request.Request(url, data=body, method=method)
    for key, value in (headers or {}).items():
        request_obj.add_header(key, value)

    handlers = []
    if cookie_jar is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookie_jar))
    if not allow_redirects:
        handlers.append(NoRedirectHandler())
    opener = urllib.request.build_opener(*handlers)

    try:
        with opener.open(request_obj, timeout=timeout) as response:
            payload = response.read()
            return response.status, response.headers, payload
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        return exc.code, exc.headers, payload


def wait_for_health(url: str, process: subprocess.Popen[str], timeout_sec: int = 15) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=2)
            raise ValidationFailure(f"Servidor caiu antes de responder | stdout={stdout.strip()} | stderr={stderr.strip()}")
        try:
            status, _, body = request("GET", url, timeout=2)
            if status == 200 and json.loads(body.decode("utf-8")).get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise ValidationFailure(f"Servidor nao respondeu em {url}")


@contextlib.contextmanager
def isolated_api_server(env_map: dict[str, str]):
    with tempfile.TemporaryDirectory(prefix="weedverso-api-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        app_copy = make_app_copy(temp_dir)
        env_file = "\n".join(f"{key}={value}" for key, value in env_map.items())
        write_text(app_copy / ".env", env_file + "\n")

        env = os.environ.copy()
        env.update(env_map)
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [sys.executable, "-u", "api_server.py"],
            cwd=app_copy,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            wait_for_health(f"http://127.0.0.1:{env_map['WEEDVERSO_PORT']}/health", process)
            yield app_copy, process
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

def run_live_local_smoke() -> tuple[str, dict]:
    status, _, body = request("GET", "http://127.0.0.1:8765/health")
    assert_equal(status, 200, "Health local deve responder 200")
    health = json.loads(body.decode("utf-8"))
    assert_equal(health.get("status"), "ok", "Health local deve estar ok")

    status, _, body = request("GET", "http://127.0.0.1:8765/api/session")
    assert_equal(status, 200, "Sessao local deve responder 200")
    session_data = json.loads(body.decode("utf-8"))
    assert_true(session_data.get("authenticated") is True, "Sessao local deve estar autenticada")

    status, _, body = request("GET", "http://127.0.0.1:8765/api/state")
    assert_equal(status, 200, "Estado local deve responder 200")
    state_data = json.loads(body.decode("utf-8"))
    counts = {
        "userName": state_data.get("userName"),
        "tx": len(state_data.get("tx") or []),
        "credit_tx": len((state_data.get("credit") or {}).get("tx") or []),
        "goals": len(state_data.get("goals") or []),
        "debtors": len(state_data.get("debtors") or []),
        "myDebts": len(state_data.get("myDebts") or []),
    }
    detail = (
        "Servico local ativo; user={user}; tx={tx}; cartao={credit_tx}; objetivos={goals}; "
        "devedores={debtors}; minhas_dividas={myDebts}"
    ).format(user=counts["userName"], **counts)
    return detail, counts


def run_shared_state_persistence_test() -> tuple[str, dict]:
    with tempfile.TemporaryDirectory(prefix="weedverso-state-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        state_file = temp_dir / "shared_state.json"
        seed = copy.deepcopy(shared_state_mod.DEFAULT_STATE)
        with shared_state_mod.using_state_file(state_file, seed_state=seed):
            shared_state_mod.add_balance_transaction("conta", "in", 125.5, "Pix cliente")
            shared_state_mod.add_balance_transaction("vale1", "out", 12.3, "Mercado")
            shared_state_mod.add_credit_transaction("expense", 89.9, "Uber")
            shared_state_mod.add_credit_transaction("payment", 25, "Pagamento")
            shared_state_mod.add_credit_transaction("reserve-in", 40, "Reserva")
            shared_state_mod.add_goal("Viagem", 1000)
            shared_state_mod.move_goal("Viagem", "deposit", 250)
            state = shared_state_mod.read_state()

        assert_true(state_file.exists(), "Arquivo de estado temporario precisa existir")
        assert_equal(round(state["balances"]["conta"]["amount"], 2), 125.5, "Conta deve persistir entrada")
        assert_equal(round(state["balances"]["vale1"]["amount"], 2), -12.3, "VA mercado deve persistir saida")
        assert_equal(round(state["credit"]["used"], 2), 64.9, "Cartao deve considerar gasto menos pagamento")
        assert_equal(round(state["credit"]["reserved"], 2), 40.0, "Reserva do cartao deve persistir")
        assert_equal(len(state["goals"]), 1, "Objetivo deve existir")
        assert_equal(round(state["goals"][0]["saved"], 2), 250.0, "Objetivo deve salvar deposito")
        detail = "Persistencia ok para conta, VA, cartao, reserva e objetivos em arquivo isolado"
        extra = {
            "conta": state["balances"]["conta"]["amount"],
            "vale1": state["balances"]["vale1"]["amount"],
            "card_used": state["credit"]["used"],
            "card_reserved": state["credit"]["reserved"],
            "goal_saved": state["goals"][0]["saved"],
        }
        return detail, extra


def run_telegram_flow_test() -> tuple[str, dict]:
    with tempfile.TemporaryDirectory(prefix="weedverso-telegram-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        state_file = temp_dir / "telegram-state.json"
        seed = copy.deepcopy(shared_state_mod.DEFAULT_STATE)
        seed["debtors"] = [
            {
                "id": "deb-1",
                "name": "Carlos",
                "amount": 120.0,
                "note": "pix atrasado",
                "payDate": "2026-04-20",
                "paid": False,
                "paidAt": "",
                "at": "2026-04-10T10:00:00",
            }
        ]
        seed["myDebts"] = [
            {
                "id": "mydeb-1",
                "name": "Notebook",
                "amount": 250.0,
                "installmentValue": 250.0,
                "installments": 5,
                "installmentsPaid": 2,
                "note": "parcelado",
                "payDate": "2026-04-25",
                "paid": False,
                "paidAt": "",
                "at": "2026-04-08T09:00:00",
            }
        ]
        chat_id = 7121051643

        with shared_state_mod.using_state_file(state_file, seed_state=seed):
            cases = [
                ("/entrada conta 150 salario", "Entrada registrada em"),
                ("remover ultima transacao", "Ultima transacao apagada"),
                ("25 entrada conta", "Entrada registrada em"),
                ("/saida vale1 20 mercado", "Saida registrada em"),
                ("/cartao 89,90 uber", "Gasto registrado no cartao"),
                ("40 pagamento cartao fatura", "Pagamento registrado no cartao"),
                ("55 entrada reserva cartao", "Reserva do cartao reforcada"),
                ("/objetivo criar Viagem | 1000", "Objetivo criado"),
                ("/objetivo entrada Viagem | 300", "Entrada registrada em"),
                ("saida 50 do objetivo Viagem", "Saida registrada em"),
                ("acrescentar 15 de rendimento no objetivo Viagem", "Rendimento registrado em"),
                ("remover ultima transacao", "Ultima transacao apagada"),
                ("12,55 rendimento ganho em objetivo", "Rendimento registrado em"),
                ("saldo objetivo", "OBJETIVOS ATIVOS"),
                ("entrou 25 na conta presente", "Entrada registrada em"),
                ("ganho 1 real conta para ajuste de saldos", "Entrada registrada em"),
                ("ganho 1 real conta", "Entrada registrada em"),
                ("ganhei 1 real em conta como pagamento", "Entrada registrada em"),
                ("gastei 12,50 no cartao cafe", "Gasto registrado no cartao"),
                ("novo devedor Lucas 50", "Devedor cadastrado"),
                ("nova divida Celular 120 em 3 parcelas", "Divida cadastrada"),
                ("adicionar mais 50 na categoria devedor para Carlos", "Saldo devedor atualizado"),
                ("acrescentar 2 parcelas na divida Notebook", "Parcelas ajustadas em"),
                ("pagar parcela da divida Notebook", "Pagamento registrado para"),
                ("apagar transacao 1", "Transacao 1 apagada"),
                ("quanto tenho na conta", "Saldo em Conta"),
                ("Devedores", "DEVEDORES"),
                ("Minhas dividas", "MINHAS DIVIDAS"),
            ]
            replies = []
            for text, expected_fragment in cases:
                _, reply = telegram_bot_mod.route_message({"chat": {"id": chat_id}, "text": text})
                replies.append({"input": text, "reply": reply})
                assert_true(expected_fragment in reply, f"Resposta do Telegram deve conter '{expected_fragment}' para '{text}'")

            _, fallback_reply = telegram_bot_mod.route_message({"chat": {"id": chat_id}, "text": "blabla comando maluco"})
            assert_equal(fallback_reply, "Desculpe meu senhor, programe melhor.", "Fallback do Telegram deve usar o novo texto")

            debtors_reply = next(item["reply"] for item in replies if item["input"] == "Devedores")
            debts_reply = next(item["reply"] for item in replies if item["input"] == "Minhas dividas")
            assert_true("Total a receber:" in debtors_reply, "Resumo de devedores deve destacar total a receber")
            assert_true("\n\n1. " in debtors_reply, "Resposta de devedores deve separar itens em blocos")
            assert_true("Parcelas:" in debts_reply, "Resposta de dividas deve destacar progresso das parcelas")
            assert_true("\n\n1. " in debts_reply, "Resposta de dividas deve separar itens em blocos")
            assert_true(
                len(telegram_bot_mod.split_telegram_text(debts_reply, max_len=120)) > 1,
                "Resposta longa de dividas deve quebrar em multiplos blocos para o Telegram",
            )

            state = shared_state_mod.read_state()

        assert_true(telegram_bot_mod.is_allowed(chat_id) is True, "Chat autorizado configurado deve ser aceito")
        assert_true(telegram_bot_mod.is_allowed(999999999) is False, "Chat aleatorio nao deve ser aceito")
        carlos_debtor = next(item for item in state["debtors"] if item.get("name") == "Carlos")
        lucas_debtor = next(item for item in state["debtors"] if item.get("name") == "Lucas")
        notebook_debt = next(item for item in state["myDebts"] if item.get("name") == "Notebook")
        celular_debt = next(item for item in state["myDebts"] if item.get("name") == "Celular")
        assert_equal(len(state["tx"]), 6, "Fluxos de conta devem gravar 6 transacoes")
        assert_equal(len(state["credit"]["tx"]), 4, "Fluxos do cartao devem gravar 4 transacoes")
        assert_equal(len(state["goals"]), 1, "Fluxo de objetivos deve criar 1 objetivo")
        assert_equal(round(carlos_debtor["amount"], 2), 170.0, "Devedor deve aceitar acrescimo por frase natural")
        assert_equal(round(lucas_debtor["amount"], 2), 50.0, "Fluxo natural deve permitir criar novo devedor")
        assert_equal(notebook_debt["installments"], 7, "Divida existente deve aceitar parcelas extras")
        assert_equal(notebook_debt["installmentsPaid"], 2, "Apagar transacao deve desfazer pagamento de parcela")
        assert_equal(celular_debt["installments"], 3, "Fluxo natural deve criar nova divida parcelada")
        assert_equal(len(state["myDebts"]), 2, "Fluxo natural deve permitir criar nova divida")
        assert_equal(round(state["goals"][0]["saved"], 2), 262.55, "Fluxo do objetivo deve persistir ordem livre, objetivo implicito e desfazer ultima transacao correta")
        detail = "Telegram simulou comandos e frases naturais com persistencia isolada"
        extra = {
            "tx": len(state["tx"]),
            "credit_tx": len(state["credit"]["tx"]),
            "goal_saved": state["goals"][0]["saved"],
            "debtor_amount": carlos_debtor["amount"],
            "notebook_installments": notebook_debt["installments"],
            "sample_reply": replies[-1]["reply"],
        }
        return detail, extra


def run_share_publish_pin_test() -> tuple[str, dict]:
    with tempfile.TemporaryDirectory(prefix="weedverso-publish-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        data_dir = temp_dir / "data"
        publish_file = data_dir / "publish_runtime.json"

        original_data_dir = share_publish_mod.DATA_DIR
        original_publish_file = share_publish_mod.PUBLISH_FILE
        original_notify_telegram = share_publish_mod._notify_telegram
        original_notify_discord = share_publish_mod._notify_discord
        original_env = {
            "WEEDVERSO_PUBLIC_URL": os.getenv("WEEDVERSO_PUBLIC_URL", ""),
            "WEEDVERSO_SHARE_HOST": os.getenv("WEEDVERSO_SHARE_HOST", ""),
        }
        call_log: list[dict] = []

        def fake_notify_telegram(links, previous_pin=None):
            preferred = share_publish_mod._telegram_link(links)
            next_message_id = 700 + len(call_log) + 1
            call_log.append({"link": preferred, "previous": dict(previous_pin or {})})
            return {
                "status": "sent",
                "pin": {
                    "chatId": "7121051643",
                    "messageId": next_message_id,
                    "updatedAt": "2026-04-15T03:00:00",
                    "link": preferred,
                    "status": "sent",
                },
            }

        try:
            share_publish_mod.DATA_DIR = data_dir
            share_publish_mod.PUBLISH_FILE = publish_file
            share_publish_mod._notify_telegram = fake_notify_telegram
            share_publish_mod._notify_discord = lambda message: "unconfigured"

            os.environ["WEEDVERSO_PUBLIC_URL"] = "https://weed.example.com"
            os.environ["WEEDVERSO_SHARE_HOST"] = ""

            first = share_publish_mod.publish_state(copy.deepcopy(shared_state_mod.DEFAULT_STATE), reason="manual", force=True)
            runtime_first = share_publish_mod.read_publish_runtime()
            assert_equal(first["version"], 1, "Primeiro publish deve criar versao 1")
            assert_equal(runtime_first["telegramPin"]["link"], "https://weed.example.com/login", "Link do Telegram deve ser limpo")
            assert_equal(runtime_first["telegramPin"]["messageId"], 701, "Pin inicial deve guardar o id retornado")

            os.environ["WEEDVERSO_PUBLIC_URL"] = "https://novo.weed.example.com"
            second = share_publish_mod.publish_state(copy.deepcopy(shared_state_mod.DEFAULT_STATE), reason="manual", force=False)
            runtime_second = share_publish_mod.read_publish_runtime()
            assert_equal(second["version"], 2, "Mudanca de link deve gerar nova versao mesmo sem mudar estado")
            assert_equal(runtime_second["telegramPin"]["link"], "https://novo.weed.example.com/login", "Pin deve guardar o link atualizado")
            assert_equal(call_log[-1]["previous"].get("messageId"), 701, "Segundo envio deve conhecer a mensagem anterior")
            detail = "Publicacao do Weedverso manteve um unico link limpo para o Telegram e reagiu a troca de URL"
            extra = {"first_link": runtime_first["telegramPin"]["link"], "second_link": runtime_second["telegramPin"]["link"]}
            return detail, extra
        finally:
            share_publish_mod.DATA_DIR = original_data_dir
            share_publish_mod.PUBLISH_FILE = original_publish_file
            share_publish_mod._notify_telegram = original_notify_telegram
            share_publish_mod._notify_discord = original_notify_discord
            for key, value in original_env.items():
                if value:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)


def run_api_noauth_test() -> tuple[str, dict]:
    port = free_port()
    env_map = {
        "WEEDVERSO_HOST": "127.0.0.1",
        "WEEDVERSO_PORT": str(port),
        "WEEDVERSO_SHARE_HOST": "127.0.0.1",
        "WEEDVERSO_PUBLIC_URL": "",
        "WEEDVERSO_LOGIN_USER": "",
        "WEEDVERSO_LOGIN_PASSWORD": "",
        "WEEDVERSO_LOGIN_PASSWORD_HASH": "",
        "WEEDVERSO_SESSION_DAYS": "14",
        "TELEGRAM_BOT_TOKEN": "",
        "WEEDVERSO_NOTIFY_CHAT_ID": "",
        "WEEDVERSO_MAX_JSON_BYTES": "2048",
    }

    with isolated_api_server(env_map) as (app_copy, process):
        base_url = f"http://127.0.0.1:{port}"
        status, headers, body = request("GET", f"{base_url}/")
        assert_equal(status, 200, "Pagina inicial local sem auth deve abrir")
        assert_true("Content-Security-Policy" in headers, "Cabecalho CSP deve existir")
        assert_true(b"weedverso" in body.lower(), "HTML inicial deve conter weedverso")

        status, _, body = request("GET", f"{base_url}/api/session")
        session_data = json.loads(body.decode("utf-8"))
        assert_equal(status, 200, "Sessao sem auth deve responder 200")
        assert_true(session_data.get("authenticated") is True, "Sessao sem auth deve cair em modo local")
        assert_true(session_data.get("authEnabled") is False, "Auth precisa estar desabilitada")

        new_state = copy.deepcopy(shared_state_mod.DEFAULT_STATE)
        new_state["userName"] = "Teste Local"
        new_state["balances"]["conta"]["amount"] = 321.45
        payload = json.dumps(new_state).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/state-sync",
            body=payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 200, "State sync sem auth deve salvar")
        response_data = json.loads(body.decode("utf-8"))
        assert_equal(response_data.get("appName"), "weedverso", "Resposta do sync deve trazer appName")

        status, _, body = request("GET", f"{base_url}/api/state")
        state_data = json.loads(body.decode("utf-8"))
        assert_equal(round(state_data["balances"]["conta"]["amount"], 2), 321.45, "GET state deve refletir valor salvo")

        publish_payload = json.dumps({"state": state_data, "reason": "manual", "force": True}).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/publish-sync",
            body=publish_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 200, "Publish sync sem auth deve responder 200")
        publish_data = json.loads(body.decode("utf-8"))
        assert_equal(publish_data["publish"]["version"], 1, "Primeira publicacao deve gerar versao 1")

        runtime = json.loads((app_copy / "data" / "publish_runtime.json").read_text(encoding="utf-8"))
        assert_equal(runtime["version"], 1, "Arquivo publish_runtime precisa persistir versao 1")

        status, _, body = request("GET", f"{base_url}/../api_server.py")
        assert_equal(status, 404, "Path traversal nao deve expor arquivo fonte")

        detail = "API sem auth salvou estado, publicou versao e bloqueou traversal"
        extra = {"version": runtime["version"], "conta": state_data["balances"]["conta"]["amount"]}
        return detail, extra


def run_api_auth_security_test() -> tuple[str, dict]:
    port = free_port()
    env_map = {
        "WEEDVERSO_HOST": "127.0.0.1",
        "WEEDVERSO_PORT": str(port),
        "WEEDVERSO_SHARE_HOST": "",
        "WEEDVERSO_PUBLIC_URL": "",
        "WEEDVERSO_LOGIN_USER": "tester",
        "WEEDVERSO_LOGIN_PASSWORD": "SenhaSegura123",
        "WEEDVERSO_LOGIN_PASSWORD_HASH": "",
        "WEEDVERSO_SESSION_DAYS": "14",
        "TELEGRAM_BOT_TOKEN": "",
        "WEEDVERSO_NOTIFY_CHAT_ID": "",
        "WEEDVERSO_MAX_JSON_BYTES": "1024",
        "WEEDVERSO_LOGIN_MAX_ATTEMPTS": "3",
        "WEEDVERSO_LOGIN_BLOCK_SECONDS": "2",
        "WEEDVERSO_LOGIN_WINDOW_SECONDS": "60",
    }

    with isolated_api_server(env_map) as (_, process):
        base_url = f"http://127.0.0.1:{port}"
        status, headers, _ = request("GET", f"{base_url}/", allow_redirects=False)
        assert_equal(status, 302, "Raiz autenticada deve redirecionar")
        assert_equal(headers.get("Location"), "/login", "Raiz deve redirecionar para /login")

        status, headers, body = request("GET", f"{base_url}/login")
        assert_equal(status, 200, "Login precisa abrir")
        assert_true("Content-Security-Policy" in headers, "Login precisa expor CSP")
        assert_equal(headers.get("X-Frame-Options"), "DENY", "X-Frame-Options deve ser DENY")
        assert_equal(headers.get("X-Content-Type-Options"), "nosniff", "nosniff deve estar presente")
        assert_true(b"Entrar no painel" in body, "Tela de login deve conter o formulario")

        status, _, body = request("GET", f"{base_url}/api/state")
        assert_equal(status, 401, "API protegida deve negar acesso sem cookie")
        assert_equal(json.loads(body.decode("utf-8")).get("error"), "unauthorized", "Erro esperado sem auth")

        payload = json.dumps({"username": "tester", "password": "SenhaSegura123"}).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=payload,
            headers={"Content-Type": "application/json", "Origin": "http://evil.example"},
        )
        assert_equal(status, 403, "Origem maliciosa deve ser bloqueada")
        assert_equal(json.loads(body.decode("utf-8")).get("error"), "forbidden_origin", "Erro esperado para origem invalida")

        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=b'{"username":"tester"}',
            headers={"Content-Type": "text/plain", "Origin": base_url},
        )
        assert_equal(status, 415, "Content-Type invalido deve ser rejeitado")

        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=b"{nao-json}",
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 400, "JSON invalido deve ser rejeitado")
        assert_equal(json.loads(body.decode("utf-8")).get("error"), "invalid_json", "Erro esperado para JSON invalido")

        huge_payload = json.dumps({"username": "tester", "password": "X" * 3000}).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=huge_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 413, "Payload grande demais deve ser barrado")

        wrong_payload = json.dumps({"username": "tester", "password": "errada"}).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=wrong_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 401, "Primeira credencial invalida deve retornar 401")

        status, _, body = request(
            "POST",
            f"{base_url}/api/login",
            body=wrong_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 401, "Segunda credencial invalida ainda deve retornar 401")

        status, headers, body = request(
            "POST",
            f"{base_url}/api/login",
            body=wrong_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
        )
        assert_equal(status, 429, "Terceira tentativa invalida deve ativar throttling")
        assert_true("Retry-After" in headers, "Rate limit deve expor Retry-After")

    with isolated_api_server(env_map) as (_, process):
        base_url = f"http://127.0.0.1:{port}"
        jar = CookieJar()
        login_payload = json.dumps({"username": "tester", "password": "SenhaSegura123"}).encode("utf-8")
        status, headers, body = request(
            "POST",
            f"{base_url}/api/login",
            body=login_payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
            cookie_jar=jar,
        )
        assert_equal(status, 200, "Login valido deve retornar 200")
        assert_equal(json.loads(body.decode("utf-8")).get("ok"), True, "Login valido precisa responder ok")
        cookie_header = headers.get("Set-Cookie", "")
        assert_true("HttpOnly" in cookie_header, "Cookie precisa ser HttpOnly")
        assert_true("SameSite=Lax" in cookie_header, "Cookie precisa usar SameSite=Lax")
        assert_true("Secure" not in cookie_header, "Cookie local em HTTP nao deve marcar Secure")

        status, _, body = request("GET", f"{base_url}/api/state", cookie_jar=jar)
        assert_equal(status, 200, "Sessao autenticada precisa acessar estado")
        state_data = json.loads(body.decode("utf-8"))
        assert_equal(state_data.get("appName"), "weedverso", "Estado autenticado deve abrir normalmente")

        new_state = copy.deepcopy(shared_state_mod.DEFAULT_STATE)
        new_state["userName"] = "Auth Test"
        payload = json.dumps(new_state).encode("utf-8")
        status, _, body = request(
            "POST",
            f"{base_url}/api/state-sync",
            body=payload,
            headers={"Content-Type": "application/json", "Origin": base_url},
            cookie_jar=jar,
        )
        assert_equal(status, 200, "Usuario autenticado deve conseguir salvar estado")

        status, headers, _ = request("POST", f"{base_url}/api/logout", body=b"{}", headers={"Content-Type": "application/json"}, cookie_jar=jar)
        assert_equal(status, 200, "Logout deve responder 200")
        assert_true("Max-Age=0" in headers.get("Set-Cookie", ""), "Logout precisa expirar cookie")

    detail = "Auth, cookie, CORS/origin, payload validation e throttling cobertos"
    extra = {}
    return detail, extra


def run_exposure_guard_test() -> tuple[str, dict]:
    with tempfile.TemporaryDirectory(prefix="weedverso-guard-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        app_copy = make_app_copy(temp_dir)
        env_map = {
            "WEEDVERSO_HOST": "0.0.0.0",
            "WEEDVERSO_PORT": str(free_port()),
            "WEEDVERSO_LOGIN_USER": "",
            "WEEDVERSO_LOGIN_PASSWORD": "",
            "WEEDVERSO_LOGIN_PASSWORD_HASH": "",
            "WEEDVERSO_PUBLIC_URL": "",
        }
        write_text(app_copy / ".env", "\n".join(f"{key}={value}" for key, value in env_map.items()) + "\n")
        env = os.environ.copy()
        env.update(env_map)
        proc = subprocess.run(
            [sys.executable, "-c", "import api_server; api_server.create_server()"],
            cwd=app_copy,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert_true(proc.returncode != 0, "Servidor nao deve abrir em 0.0.0.0 sem auth")
        combined = f"{proc.stdout}\n{proc.stderr}"
        assert_true("Autenticacao obrigatoria" in combined, "Mensagem de bloqueio precisa mencionar autenticacao obrigatoria")
        detail = "Guarda de exposicao impediu bind inseguro em 0.0.0.0 sem auth"
        return detail, {"returncode": proc.returncode}


def send_telegram_report(summary_text: str, lines: list[str]) -> list[dict]:
    notify_chat = (
        str(os.getenv("WEEDVERSO_NOTIFY_CHAT_ID") or "").strip()
        or str(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS") or "").split(",", 1)[0].strip()
        or str(telegram_bot_mod.latest_chat_id() or "").strip()
    )
    if not notify_chat:
        raise ValidationFailure("Nao encontrei chat do Telegram para publicar o resultado.")

    payloads = [summary_text]
    detail_text = "\n".join(lines)
    payloads.extend(chunk_text(detail_text))

    sent = []
    for text in payloads:
        result = telegram_bot_mod.call_telegram("sendMessage", {"chat_id": notify_chat, "text": text})
        sent.append({"chat_id": notify_chat, "message_id": result.get("message_id"), "text": text})
    return sent


def run_checks() -> tuple[list[CheckResult], dict]:
    checks: list[tuple[str, Callable[[], tuple[str, dict]]]] = [
        ("live_local_smoke", run_live_local_smoke),
        ("shared_state_persistence", run_shared_state_persistence_test),
        ("telegram_user_flows", run_telegram_flow_test),
        ("share_publish_pin", run_share_publish_pin_test),
        ("api_noauth_persistence", run_api_noauth_test),
        ("api_auth_security", run_api_auth_security_test),
        ("exposure_guard", run_exposure_guard_test),
    ]

    results: list[CheckResult] = []
    for name, func in checks:
        started = time.perf_counter()
        try:
            detail, extra = func()
            ok = True
        except Exception as exc:
            ok = False
            detail = f"{type(exc).__name__}: {exc}"
            extra = {"traceback": traceback.format_exc()}
        duration_ms = int((time.perf_counter() - started) * 1000)
        results.append(CheckResult(name=name, ok=ok, detail=detail, duration_ms=duration_ms, extra=extra))

    total = len(results)
    passed = sum(1 for item in results if item.ok)
    failed = total - passed
    report = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": [
            {
                "name": item.name,
                "ok": item.ok,
                "detail": item.detail,
                "durationMs": item.duration_ms,
                "extra": item.extra,
            }
            for item in results
        ],
    }
    return results, report


def main() -> int:
    stamp = now_stamp()
    report_json_path = LOGS_DIR / f"validation-report-{stamp}.json"
    report_txt_path = LOGS_DIR / f"validation-report-{stamp}.txt"

    results, report = run_checks()

    lines = []
    for item in results:
        status_label = "PASS" if item.ok else "FAIL"
        lines.append(f"[{status_label}] {item.name} ({item.duration_ms}ms) - {item.detail}")

    summary = (
        "weedverso | bateria automatizada\n"
        f"Resultado: {report['passed']}/{report['total']} aprovados\n"
        f"Falhas: {report['failed']}\n"
        f"Relatorio local: {report_txt_path}"
    )
    report_text = summary + "\n" + "\n".join(lines)

    write_json(report_json_path, report)
    write_text(report_txt_path, report_text + "\n")

    telegram_delivery = []
    try:
        telegram_delivery = send_telegram_report(summary, lines)
    except Exception as exc:
        report["telegramDeliveryError"] = str(exc)
        write_json(report_json_path, report)
        write_text(report_txt_path, report_text + f"\nTelegram: erro ao enviar -> {exc}\n")

    print(report_text)
    if telegram_delivery:
        print(f"Telegram: {len(telegram_delivery)} mensagem(ns) enviadas")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
