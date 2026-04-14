import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from env_loader import load_env_file
from share_publish import current_share_info, local_base_url, public_base_url, publish_state
from shared_state import normalize_state, read_state, write_state
from weedverso_paths import resource_root


load_env_file()

BASE_DIR = resource_root()
HOST = os.getenv("WEEDVERSO_HOST", "127.0.0.1")
PORT = int(os.getenv("WEEDVERSO_PORT", "8765"))
LOGIN_USER = os.getenv("WEEDVERSO_LOGIN_USER", "").strip()
LOGIN_PASSWORD = os.getenv("WEEDVERSO_LOGIN_PASSWORD", "").strip()
LOGIN_PASSWORD_HASH = os.getenv("WEEDVERSO_LOGIN_PASSWORD_HASH", "").strip()
SYNC_TOKEN = os.getenv("WEEDVERSO_SYNC_TOKEN", "").strip()
SESSION_COOKIE = "weedverso_session"
SESSION_TTL_SECONDS = max(3600, int(os.getenv("WEEDVERSO_SESSION_DAYS", "14")) * 86400)
MAX_JSON_BYTES = max(1024, int(os.getenv("WEEDVERSO_MAX_JSON_BYTES", "524288")))
LOGIN_WINDOW_SECONDS = max(60, int(os.getenv("WEEDVERSO_LOGIN_WINDOW_SECONDS", "600")))
LOGIN_MAX_ATTEMPTS = max(3, int(os.getenv("WEEDVERSO_LOGIN_MAX_ATTEMPTS", "8")))
LOGIN_BLOCK_SECONDS = max(60, int(os.getenv("WEEDVERSO_LOGIN_BLOCK_SECONDS", "900")))

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
LOGIN_ATTEMPTS = {}
LOGIN_ATTEMPTS_LOCK = threading.Lock()


def auth_enabled():
    return bool(LOGIN_USER and (LOGIN_PASSWORD or LOGIN_PASSWORD_HASH))


def loopback_host(host):
    host = str(host or "").strip().lower()
    return host in {"127.0.0.1", "::1", "localhost"}


def verify_password(password):
    password = str(password or "")
    if LOGIN_PASSWORD_HASH:
        try:
            algorithm, iterations, salt, expected = LOGIN_PASSWORD_HASH.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(digest, expected)
        except (TypeError, ValueError):
            return False
    if LOGIN_PASSWORD:
        return hmac.compare_digest(password, LOGIN_PASSWORD)
    return False


def cleanup_sessions():
    now = time.time()
    with SESSIONS_LOCK:
        expired = [token for token, data in SESSIONS.items() if data["expires_at"] <= now]
        for token in expired:
            SESSIONS.pop(token, None)


def create_session(username):
    cleanup_sessions()
    token = secrets.token_urlsafe(32)
    with SESSIONS_LOCK:
        SESSIONS[token] = {
            "username": username,
            "expires_at": time.time() + SESSION_TTL_SECONDS,
        }
    return token


def read_session(token):
    if not token:
        return None
    cleanup_sessions()
    with SESSIONS_LOCK:
        data = SESSIONS.get(token)
        if not data:
            return None
        return dict(data)


def delete_session(token):
    if not token:
        return
    with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


def normalize_origin(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def cleanup_login_attempts(now=None):
    now = now or time.time()
    with LOGIN_ATTEMPTS_LOCK:
        expired = []
        for key, entry in LOGIN_ATTEMPTS.items():
            blocked_until = float(entry.get("blocked_until") or 0)
            if blocked_until and blocked_until > now:
                continue
            attempts = [stamp for stamp in list(entry.get("attempts") or []) if now - stamp <= LOGIN_WINDOW_SECONDS]
            if attempts:
                entry["attempts"] = attempts
                entry["blocked_until"] = 0
            else:
                expired.append(key)
        for key in expired:
            LOGIN_ATTEMPTS.pop(key, None)


class WeedversoHandler(BaseHTTPRequestHandler):
    server_version = "WeedversoAPI"
    sys_version = ""

    def version_string(self):
        return self.server_version

    def _request_scheme(self):
        forwarded = str(self.headers.get("X-Forwarded-Proto", "")).split(",", 1)[0].strip().lower()
        if forwarded in {"http", "https"}:
            return forwarded
        return "http"

    def _request_origin(self):
        host = str(self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "").split(",", 1)[0].strip()
        if not host:
            return ""
        return normalize_origin(f"{self._request_scheme()}://{host}")

    def _allowed_origins(self):
        origins = {
            normalize_origin(public_base_url()),
            normalize_origin(local_base_url()),
            self._request_origin(),
        }
        return {origin for origin in origins if origin}

    def _cors_origin(self):
        origin = normalize_origin(self.headers.get("Origin", ""))
        if origin and origin in self._allowed_origins():
            return origin
        return ""

    def _request_context_origin(self):
        origin = normalize_origin(self.headers.get("Origin", ""))
        if origin:
            return origin
        return normalize_origin(self.headers.get("Referer", ""))

    def _enforce_request_origin(self):
        context_origin = self._request_context_origin()
        if not context_origin:
            return True
        if context_origin in self._allowed_origins():
            return True
        self._send_json({"error": "forbidden_origin"}, status=403)
        return False

    def _client_ip(self):
        forwarded = str(self.headers.get("X-Forwarded-For", "")).split(",", 1)[0].strip()
        if forwarded:
            return forwarded
        return str(self.client_address[0] if self.client_address else "").strip() or "unknown"

    def _login_block_seconds(self):
        cleanup_login_attempts()
        key = self._client_ip()
        with LOGIN_ATTEMPTS_LOCK:
            entry = LOGIN_ATTEMPTS.get(key) or {}
            remaining = max(0, int((float(entry.get("blocked_until") or 0) - time.time()) + 0.999))
        return remaining

    def _record_failed_login(self):
        now = time.time()
        key = self._client_ip()
        cleanup_login_attempts(now)
        with LOGIN_ATTEMPTS_LOCK:
            entry = LOGIN_ATTEMPTS.setdefault(key, {"attempts": [], "blocked_until": 0})
            attempts = [stamp for stamp in list(entry.get("attempts") or []) if now - stamp <= LOGIN_WINDOW_SECONDS]
            attempts.append(now)
            blocked_until = 0
            if len(attempts) >= LOGIN_MAX_ATTEMPTS:
                blocked_until = now + LOGIN_BLOCK_SECONDS
                attempts = []
            entry["attempts"] = attempts
            entry["blocked_until"] = blocked_until
            return max(0, int((blocked_until - now) + 0.999))

    def _clear_failed_logins(self):
        key = self._client_ip()
        with LOGIN_ATTEMPTS_LOCK:
            LOGIN_ATTEMPTS.pop(key, None)

    def _request_is_secure(self):
        return self._request_scheme() == "https"

    def _response_headers(self, extra_headers=None):
        origin = self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; "
            "img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'",
        )
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        if self._request_is_secure():
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if extra_headers:
            for key, value in extra_headers:
                self.send_header(key, value)

    def _send_json(self, payload, status=200, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        all_headers = [("Cache-Control", "no-store"), ("Pragma", "no-cache")]
        if headers:
            all_headers.extend(headers)
        self._response_headers(all_headers)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_file(self, file_path, status=200, headers=None):
        mime_type, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        cache_value = "no-store" if file_path.name in {"index.html", "login.html"} else "public, max-age=3600"
        self.send_header("Cache-Control", cache_value)
        if file_path.name in {"index.html", "login.html"}:
            self.send_header("Pragma", "no-cache")
        self._response_headers(headers)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self._response_headers()
        self.end_headers()

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "invalid_content_length"}, status=400)
            return None
        if length < 0:
            self._send_json({"error": "invalid_content_length"}, status=400)
            return None
        content_type = str(self.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if length and content_type != "application/json":
            self._send_json({"error": "unsupported_media_type"}, status=415)
            return None
        if length > MAX_JSON_BYTES:
            self._send_json({"error": "payload_too_large"}, status=413)
            return None
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, status=400)
            return None
        if not isinstance(payload, dict):
            self._send_json({"error": "invalid_payload"}, status=400)
            return None
        return payload

    def _cookie_value(self, key):
        raw_cookie = self.headers.get("Cookie", "")
        if not raw_cookie:
            return ""
        jar = cookies.SimpleCookie()
        jar.load(raw_cookie)
        morsel = jar.get(key)
        return morsel.value if morsel else ""

    def _sync_token_value(self):
        direct = str(self.headers.get("X-Weedverso-Sync-Token", "") or "").strip()
        if direct:
            return direct
        auth_header = str(self.headers.get("Authorization", "") or "").strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return ""

    def _has_sync_access(self):
        if not SYNC_TOKEN:
            return False
        candidate = self._sync_token_value()
        if not candidate:
            return False
        return hmac.compare_digest(candidate, SYNC_TOKEN)

    def _session_cookie_header(self, token=None, expire=False):
        jar = cookies.SimpleCookie()
        jar[SESSION_COOKIE] = "" if expire else token
        morsel = jar[SESSION_COOKIE]
        morsel["httponly"] = True
        morsel["path"] = "/"
        morsel["samesite"] = "Lax"
        if self._request_is_secure():
            morsel["secure"] = True
        if expire:
            morsel["max-age"] = 0
            morsel["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        else:
            morsel["max-age"] = str(SESSION_TTL_SECONDS)
        return morsel.OutputString()

    def _current_session(self):
        if not auth_enabled():
            return {"username": "modo-local", "expires_at": time.time() + SESSION_TTL_SECONDS}
        return read_session(self._cookie_value(SESSION_COOKIE))

    def _is_authenticated(self):
        return self._current_session() is not None

    def _ensure_auth_json(self):
        if self._is_authenticated() or self._has_sync_access():
            return True
        self._send_json({"error": "unauthorized"}, status=401)
        return False

    def _serve_static(self, path):
        cleaned = path.lstrip("/")
        target = (BASE_DIR / cleaned).resolve()
        try:
            target.relative_to(BASE_DIR.resolve())
        except ValueError:
            return False

        if target.is_file():
            self._send_file(target)
            return True
        return False

    def do_OPTIONS(self):
        if self.headers.get("Origin") and not self._cors_origin():
            self._send_json({"error": "forbidden_origin"}, status=403)
            return
        self.send_response(204)
        self._response_headers()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json({"status": "ok"})
            return

        if path == "/api/session":
            session = self._current_session()
            sync_authenticated = self._has_sync_access()
            self._send_json(
                {
                    "authenticated": session is not None or sync_authenticated,
                    "user": session["username"] if session else ("sync-bridge" if sync_authenticated else None),
                    "authEnabled": auth_enabled(),
                    "syncAuthenticated": sync_authenticated,
                }
            )
            return

        if path in {"/login", "/login.html"}:
            if self._is_authenticated():
                self._redirect("/")
                return
            login_path = BASE_DIR / "login.html"
            if login_path.exists():
                self._send_file(login_path)
                return
            self._send_json({"error": "login_page_missing"}, status=500)
            return

        if path == "/api/state":
            if not self._ensure_auth_json():
                return
            self._send_json(read_state())
            return

        if path == "/api/share-info":
            if not self._ensure_auth_json():
                return
            self._send_json(current_share_info())
            return

        if path in {"", "/", "/index.html"} and not self._is_authenticated():
            self._redirect("/login")
            return

        if not self._is_authenticated():
            self._redirect("/login")
            return

        normalized_path = "/" if path in {"", "/"} else path
        if normalized_path == "/":
            normalized_path = "/index.html"

        if self._serve_static(normalized_path):
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self._enforce_request_origin():
            return

        if path == "/api/login":
            if not auth_enabled():
                self._send_json({"error": "auth_not_configured"}, status=503)
                return
            blocked_for = self._login_block_seconds()
            if blocked_for > 0:
                self._send_json(
                    {"error": "too_many_attempts", "retryAfter": blocked_for},
                    status=429,
                    headers=[("Retry-After", str(blocked_for))],
                )
                return
            payload = self._read_json_body()
            if payload is None:
                return
            username = str(payload.get("username", "")).strip()
            password = payload.get("password", "")
            if not username or not password:
                self._send_json({"error": "missing_credentials"}, status=400)
                return
            if not hmac.compare_digest(username, LOGIN_USER) or not verify_password(password):
                blocked_for = self._record_failed_login()
                if blocked_for > 0:
                    self._send_json(
                        {"error": "too_many_attempts", "retryAfter": blocked_for},
                        status=429,
                        headers=[("Retry-After", str(blocked_for))],
                    )
                    return
                self._send_json({"error": "invalid_credentials"}, status=401)
                return
            self._clear_failed_logins()
            token = create_session(username)
            self._send_json(
                {"ok": True, "user": username},
                headers=[("Set-Cookie", self._session_cookie_header(token=token))],
            )
            return

        if path == "/api/logout":
            delete_session(self._cookie_value(SESSION_COOKIE))
            self._send_json(
                {"ok": True},
                headers=[("Set-Cookie", self._session_cookie_header(expire=True))],
            )
            return

        if path == "/api/state-sync":
            if not self._ensure_auth_json():
                return
            payload = self._read_json_body()
            if payload is None:
                return
            state = write_state(normalize_state(payload))
            self._send_json({"ok": True, "updatedAt": time.time(), "appName": state.get("appName", "weedverso")})
            return

        if path == "/api/publish":
            if not self._ensure_auth_json():
                return
            payload = self._read_json_body()
            if payload is None:
                return
            state_payload = payload.get("state")
            if state_payload is not None:
                state = write_state(normalize_state(state_payload))
            else:
                state = read_state()
            publish = publish_state(
                state,
                reason=str(payload.get("reason") or "manual"),
                force=bool(payload.get("force")),
            )
            self._send_json({"ok": True, "stateUpdatedAt": time.time(), "publish": publish})
            return

        if path == "/api/publish-sync":
            if not self._ensure_auth_json():
                return
            payload = self._read_json_body()
            if payload is None:
                return
            state_payload = payload.get("state")
            if state_payload is not None:
                state = write_state(normalize_state(state_payload))
            else:
                state = read_state()
            publish = publish_state(
                state,
                reason=str(payload.get("reason") or "close"),
                force=bool(payload.get("force")),
            )
            self._send_json({"ok": True, "publish": publish})
            return

        self._send_json({"error": "not_found"}, status=404)

    def do_PUT(self):
        path = urlparse(self.path).path
        if path != "/api/state":
            self._send_json({"error": "not_found"}, status=404)
            return
        if not self._enforce_request_origin():
            return
        if not self._ensure_auth_json():
            return

        payload = self._read_json_body()
        if payload is None:
            return

        state = write_state(normalize_state(payload))
        self._send_json(state)

    def log_message(self, format_text, *args):
        return


def create_server():
    if not auth_enabled() and not loopback_host(HOST) and str(os.getenv("WEEDVERSO_ALLOW_INSECURE_NOAUTH", "")).strip().lower() not in {"1", "true", "on", "yes", "sim"}:
        raise RuntimeError(
            "Autenticacao obrigatoria para expor o Weedverso fora do loopback. "
            "Defina usuario/senha ou use WEEDVERSO_ALLOW_INSECURE_NOAUTH=1 conscientemente."
        )
    return ThreadingHTTPServer((HOST, PORT), WeedversoHandler)


def run_server():
    server = create_server()
    print(f"Weedverso API ativa em http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
