import copy
import json
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime

from weedverso_paths import persistent_data_root, resource_path

DATA_DIR = persistent_data_root()
STATE_FILE = DATA_DIR / "shared_state.json"
SEED_STATE_FILE = resource_path("data/shared_state.json")
LOCK = threading.RLock()
STATE_FILE_OVERRIDE = threading.local()


DEFAULT_STATE = {
    "appName": "weedverso",
    "userName": "",
    "xp": 0,
    "streak": 0,
    "routineDone": False,
    "lastDate": "",
    "habits": [],
    "balances": {
        "conta": {"label": "Saldo em Conta", "amount": 0},
        "vale1": {"label": "VA Mercado", "amount": 0},
        "vale2": {"label": "VA Refeicao", "amount": 0},
    },
    "tx": [],
    "credit": {
        "name": "Cartao weedverso",
        "used": 0,
        "reserved": 0,
        "tx": [],
    },
    "debtors": [],
    "myDebts": [],
    "routineLog": [],
    "skills": {"estudar": 0, "treinar": 0, "trabalhar": 0},
    "goals": [],
    "dailyStats": {},
    "focusSession": {"habitId": "", "secondsLeft": 1500, "running": False},
}


BALANCE_ALIASES = {
    "conta": "conta",
    "conta corrente": "conta",
    "conta bancaria": "conta",
    "conta principal": "conta",
    "saldo da conta": "conta",
    "saldo conta": "conta",
    "saldo conta corrente": "conta",
    "corrente": "conta",
    "principal": "conta",
    "saldo": "conta",
    "saldo em conta": "conta",
    "saldo corrente": "conta",
    "banco": "conta",
    "bancaria": "conta",
    "cc": "conta",
    "mercado": "vale1",
    "va mercado": "vale1",
    "vale mercado": "vale1",
    "alelo mercado": "vale1",
    "mercado alelo": "vale1",
    "va1": "vale1",
    "vale1": "vale1",
    "alimentacao": "vale1",
    "va": "vale1",
    "va alimentacao": "vale1",
    "vale alimentacao": "vale1",
    "vale alimentacao 1": "vale1",
    "beneficio alimentacao": "vale1",
    "alelo alimentacao": "vale1",
    "alelo va": "vale1",
    "cartao alimentacao": "vale1",
    "cartao de alimentacao": "vale1",
    "refeicao": "vale2",
    "vr": "vale2",
    "vr refeicao": "vale2",
    "vale refeicao 2": "vale2",
    "vale refeicao": "vale2",
    "beneficio refeicao": "vale2",
    "alelo refeicao": "vale2",
    "alelo vr": "vale2",
    "cartao refeicao": "vale2",
    "cartao de refeicao": "vale2",
    "va2": "vale2",
    "vale2": "vale2",
}
NORMALIZED_BALANCE_ALIASES = {}


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def make_id():
    now = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return now[-14:]


def _active_state_file():
    return getattr(STATE_FILE_OVERRIDE, "path", None) or STATE_FILE


def _ensure_storage_for_file(state_file, seed_state=None):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    if not state_file.exists():
        if seed_state is not None:
            payload = normalize_state(seed_state)
            state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif SEED_STATE_FILE.exists() and SEED_STATE_FILE.resolve() != state_file.resolve():
            state_file.write_text(SEED_STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            state_file.write_text(json.dumps(DEFAULT_STATE, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_storage_for_file(_active_state_file())


@contextmanager
def using_state_file(state_file, seed_state=None):
    previous = getattr(STATE_FILE_OVERRIDE, "path", None)
    state_file = state_file.resolve()
    _ensure_storage_for_file(state_file, seed_state=seed_state)
    STATE_FILE_OVERRIDE.path = state_file
    try:
        yield state_file
    finally:
        if previous is None:
            try:
                del STATE_FILE_OVERRIDE.path
            except AttributeError:
                pass
        else:
            STATE_FILE_OVERRIDE.path = previous


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def normalize_spaces(value):
    return " ".join(str(value or "").strip().split())


def fold_text(value):
    text = normalize_spaces(value)
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    cleaned = []
    for char in normalized:
        cleaned.append(char if char.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def titleize_words(value):
    folded = fold_text(value)
    if not folded:
        return ""
    lowers = {"de", "da", "do", "das", "dos", "e", "em", "para", "pra", "pro", "no", "na", "nos", "nas"}
    words = []
    for index, word in enumerate(folded.split()):
        words.append(word if index > 0 and word in lowers else word.capitalize())
    return " ".join(words)


def build_category(raw_value, fallback="Sem categoria"):
    source = normalize_spaces(raw_value)
    label = titleize_words(source) or titleize_words(fallback) or "Sem Categoria"
    key = fold_text(source) or fold_text(fallback) or "sem categoria"
    return {"category": label[:42], "categoryKey": key[:48]}


for alias, target in BALANCE_ALIASES.items():
    NORMALIZED_BALANCE_ALIASES[fold_text(alias)] = target


def dynamic_balance_aliases(state):
    aliases = {}
    balances = (state or {}).get("balances") or {}
    removable_prefixes = ("saldo em ", "saldo ", "vale ", "cartao ", "cartão ")
    for key, item in balances.items():
        label = fold_text((item or {}).get("label"))
        if not label:
            continue
        aliases[label] = key
        for prefix in removable_prefixes:
            if label.startswith(prefix):
                trimmed = label[len(prefix):].strip()
                if trimmed:
                    aliases[trimmed] = key
    return aliases


def food_slot_from_label(label):
    folded = fold_text(label)
    if not folded:
        return ""
    if any(
        token in folded
        for token in {
            "alimentacao",
            "alelo alimentacao",
            "alelo va",
            "cartao alimentacao",
            "cartao de alimentacao",
            "va mercado",
            "mercado",
        }
    ):
        return "vale1"
    if any(
        token in folded
        for token in {
            "refeicao",
            "alelo refeicao",
            "alelo vr",
            "cartao refeicao",
            "cartao de refeicao",
            "vr refeicao",
            "vr",
        }
    ):
        return "vale2"
    return ""


def repair_food_balance_slots(state):
    balances = (state or {}).get("balances") or {}
    vale1 = dict(balances.get("vale1") or {})
    vale2 = dict(balances.get("vale2") or {})
    vale1_slot = food_slot_from_label(vale1.get("label"))
    vale2_slot = food_slot_from_label(vale2.get("label"))
    if vale1_slot == "vale2" and vale2_slot == "vale1":
        balances["vale1"], balances["vale2"] = vale2, vale1
        for item in list((state or {}).get("tx") or []):
            account = item.get("account")
            if account == "vale1":
                item["account"] = "vale2"
            elif account == "vale2":
                item["account"] = "vale1"
    return state


def balance_alias_map(state=None):
    aliases = dict(NORMALIZED_BALANCE_ALIASES)
    if state is not None:
        for label, target in dynamic_balance_aliases(state).items():
            aliases.setdefault(label, target)
    return aliases


def normalize_balance_tx(item):
    tx = dict(item or {})
    tx_type = str(tx.get("type") or "in")
    fallback = "Ajuste manual" if tx_type == "set" else "Sem categoria"
    tx = {
        "id": str(tx.get("id") or make_id()),
        "account": resolve_balance_key(tx.get("account") or "conta"),
        "type": tx_type,
        "value": abs(safe_float(tx.get("value"), 0)),
        "prev": safe_float(tx.get("prev"), 0),
        "note": normalize_spaces(tx.get("note"))[:60],
        "debtorId": str(tx.get("debtorId") or ""),
        "myDebtId": str(tx.get("myDebtId") or ""),
        "myDebtInstallment": max(0, int(safe_float(tx.get("myDebtInstallment"), 0))),
        "at": str(tx.get("at") or _now_iso()),
        "category": tx.get("category") or "",
        "categoryKey": tx.get("categoryKey") or "",
    }
    tx.update(build_category(tx["category"] or tx["note"], fallback))
    return tx


def normalize_credit_tx(item):
    tx = dict(item or {})
    tx_type = str(tx.get("type") or "expense")
    fallback = {
        "expense": "Sem categoria",
        "payment": "Pagamento cartao",
        "reserve-in": "Reserva cartao",
        "reserve-out": "Reserva cartao",
    }.get(tx_type, "Sem categoria")
    tx = {
        "id": str(tx.get("id") or make_id()),
        "type": tx_type,
        "value": abs(safe_float(tx.get("value"), 0)),
        "desc": normalize_spaces(tx.get("desc"))[:60],
        "at": str(tx.get("at") or _now_iso()),
        "category": tx.get("category") or "",
        "categoryKey": tx.get("categoryKey") or "",
    }
    tx.update(build_category(tx["category"] or tx["desc"], fallback))
    return tx


def normalize_goal_name(name):
    return normalize_spaces(name)[:36]


def normalize_debt_item(item):
    entry = dict(item or {})
    installments = max(1, min(12, int(safe_float(entry.get("installments"), 1))))
    paid = bool(entry.get("paid"))
    paid_installments = int(safe_float(entry.get("installmentsPaid"), installments if paid else 0))
    paid_installments = max(0, min(installments, paid_installments))
    raw_amount = max(0.0, safe_float(entry.get("amount"), 0))
    raw_installment_value = max(0.0, safe_float(entry.get("installmentValue"), 0))
    installment_value = raw_installment_value or (raw_amount / installments if installments > 1 and raw_amount > 0 else raw_amount)
    if paid and paid_installments < installments:
        paid_installments = installments
    paid = paid_installments >= installments
    return {
        "id": str(entry.get("id") or make_id()),
        "name": normalize_spaces(entry.get("name"))[:30],
        "amount": installment_value,
        "installmentValue": installment_value,
        "installments": installments,
        "installmentsPaid": paid_installments,
        "note": normalize_spaces(entry.get("note"))[:50],
        "payDate": str(entry.get("payDate") or ""),
        "paid": paid,
        "paidAt": str(entry.get("paidAt") or ""),
        "at": str(entry.get("at") or _now_iso()),
    }


def normalize_state(raw_state):
    raw_state = raw_state or {}
    state = copy.deepcopy(DEFAULT_STATE)
    state.update({k: v for k, v in raw_state.items() if k not in {"balances", "credit", "skills", "focusSession"}})
    state["appName"] = "weedverso"

    raw_balances = raw_state.get("balances") or {}
    for key, default_balance in DEFAULT_STATE["balances"].items():
        incoming = raw_balances.get(key) or {}
        state["balances"][key] = {
            "label": normalize_spaces(incoming.get("label") or default_balance["label"])[:26],
            "amount": safe_float(incoming.get("amount"), default_balance["amount"]),
        }

    raw_credit = raw_state.get("credit") or {}
    credit_name = normalize_spaces(raw_credit.get("name") or DEFAULT_STATE["credit"]["name"])[:30]
    if not credit_name or credit_name == "Cartao Prime":
        credit_name = DEFAULT_STATE["credit"]["name"]
    state["credit"] = {
        "name": credit_name,
        "used": max(0.0, safe_float(raw_credit.get("used"), 0)),
        "reserved": max(0.0, safe_float(raw_credit.get("reserved"), 0)),
        "tx": [normalize_credit_tx(item) for item in list(raw_credit.get("tx") or [])],
    }

    raw_skills = raw_state.get("skills") or {}
    state["skills"] = {
        "estudar": max(0, int(safe_float(raw_skills.get("estudar"), 0))),
        "treinar": max(0, int(safe_float(raw_skills.get("treinar"), 0))),
        "trabalhar": max(0, int(safe_float(raw_skills.get("trabalhar"), 0))),
    }

    focus = raw_state.get("focusSession") or {}
    state["focusSession"] = {
        "habitId": str(focus.get("habitId") or ""),
        "secondsLeft": max(0, int(safe_float(focus.get("secondsLeft"), 1500))),
        "running": bool(focus.get("running")),
    }

    state["tx"] = [normalize_balance_tx(item) for item in list(raw_state.get("tx") or [])]
    state["habits"] = list(raw_state.get("habits") or [])
    state["debtors"] = [normalize_debt_item(item) for item in list(raw_state.get("debtors") or [])]
    state["myDebts"] = [normalize_debt_item(item) for item in list(raw_state.get("myDebts") or [])]
    state["routineLog"] = list(raw_state.get("routineLog") or [])
    state["goals"] = list(raw_state.get("goals") or [])
    state["dailyStats"] = dict(raw_state.get("dailyStats") or {})
    state["lastDate"] = str(raw_state.get("lastDate") or "")
    repair_food_balance_slots(state)
    return state


def read_state():
    state_file = _active_state_file()
    _ensure_storage_for_file(state_file)
    with LOCK:
        raw = state_file.read_text(encoding="utf-8")
        return normalize_state(json.loads(raw))


def write_state(state):
    state_file = _active_state_file()
    _ensure_storage_for_file(state_file)
    normalized = normalize_state(state)
    with LOCK:
        state_file.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def update_state(mutator, persist=True):
    with LOCK:
        state = read_state()
        mutator(state)
        if persist:
            return write_state(state)
        return normalize_state(state)


def resolve_balance_key(alias, state=None):
    folded = fold_text(alias)
    dynamic_aliases = dynamic_balance_aliases(state) if state is not None else {}
    key = NORMALIZED_BALANCE_ALIASES.get(folded) or dynamic_aliases.get(folded)
    if not key and state is not None and folded:
        matches = []
        for label, target in dynamic_aliases.items():
            if folded in label or label in folded:
                matches.append(target)
        unique_matches = []
        for item in matches:
            if item not in unique_matches:
                unique_matches.append(item)
        if len(unique_matches) == 1:
            key = unique_matches[0]
    if not key:
        raise ValueError("Carteira invalida. Use conta, mercado/va1 ou refeicao/va2.")
    return key


def add_balance_transaction(account_alias, direction, value, note="", persist=True):
    amount = abs(safe_float(value))
    note = normalize_spaces(note)[:60]
    if amount <= 0:
        raise ValueError("O valor precisa ser maior que zero.")

    def mutate(state):
        account_key = resolve_balance_key(account_alias, state)
        balance = state["balances"][account_key]
        balance["amount"] = safe_float(balance.get("amount"), 0)
        if direction == "in":
            balance["amount"] += amount
        elif direction == "out":
            balance["amount"] -= amount
        else:
            raise ValueError("Direcao invalida.")
        entry = {
            "id": make_id(),
            "account": account_key,
            "type": direction,
            "value": amount,
            "note": note,
            "at": _now_iso(),
        }
        entry.update(build_category(note, "Sem categoria"))
        state["tx"].insert(0, entry)

    return update_state(mutate, persist=persist)


def add_credit_transaction(kind, value, description="", persist=True):
    amount = abs(safe_float(value))
    description = normalize_spaces(description)[:60]
    if amount <= 0:
        raise ValueError("O valor precisa ser maior que zero.")

    tx_type = {
        "expense": "expense",
        "payment": "payment",
        "reserve-in": "reserve-in",
        "reserve-out": "reserve-out",
    }.get(kind)
    if not tx_type:
        raise ValueError("Tipo de movimentacao do cartao invalido.")

    def mutate(state):
        credit = state["credit"]
        credit["used"] = max(0.0, safe_float(credit.get("used"), 0))
        credit["reserved"] = max(0.0, safe_float(credit.get("reserved"), 0))

        if tx_type == "expense":
            credit["used"] += amount
        elif tx_type == "payment":
            credit["used"] = max(0.0, credit["used"] - amount)
        elif tx_type == "reserve-in":
            credit["reserved"] += amount
        elif tx_type == "reserve-out":
            credit["reserved"] = max(0.0, credit["reserved"] - amount)

        fallback = {
            "expense": "Sem categoria",
            "payment": "Pagamento cartao",
            "reserve-in": "Reserva cartao",
            "reserve-out": "Reserva cartao",
        }[tx_type]
        entry = {
            "id": make_id(),
            "type": tx_type,
            "value": amount,
            "desc": description,
            "at": _now_iso(),
        }
        entry.update(build_category(description, fallback))
        credit["tx"].insert(0, entry)

    return update_state(mutate, persist=persist)


def resolve_goal(goals, goal_name):
    target_name = normalize_goal_name(goal_name).lower()
    if not target_name:
        raise ValueError("Informe o nome do objetivo.")

    exact = [goal for goal in goals if normalize_goal_name(goal.get("name")).lower() == target_name]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError("Existem objetivos duplicados com esse nome. Renomeie um deles no app.")

    partial = [goal for goal in goals if target_name in normalize_goal_name(goal.get("name")).lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError("Mais de um objetivo combina com esse nome. Seja mais especifico.")
    raise ValueError("Objetivo nao encontrado.")


def add_goal(name, target, persist=True):
    goal_name = normalize_goal_name(name)
    amount = abs(safe_float(target))
    if not goal_name:
        raise ValueError("O nome do objetivo e obrigatorio.")
    if amount <= 0:
        raise ValueError("A meta do objetivo precisa ser maior que zero.")

    def mutate(state):
        goals = state.setdefault("goals", [])
        if any(normalize_goal_name(goal.get("name")).lower() == goal_name.lower() for goal in goals):
            raise ValueError("Ja existe um objetivo com esse nome.")
        goals.insert(
            0,
            {
                "id": make_id(),
                "name": goal_name,
                "target": amount,
                "saved": 0,
                "tx": [],
            },
        )
        state["goals"] = goals[:80]

    return update_state(mutate, persist=persist)


def move_goal(goal_name, move_type, value, persist=True):
    amount = abs(safe_float(value))
    if amount <= 0:
        raise ValueError("O valor precisa ser maior que zero.")

    tx_type = {
        "deposit": "deposit",
        "withdraw": "withdraw",
        "yield": "yield",
    }.get(move_type)
    if not tx_type:
        raise ValueError("Tipo de movimentacao do objetivo invalido.")

    def mutate(state):
        goals = state.setdefault("goals", [])
        goal = resolve_goal(goals, goal_name)
        goal["saved"] = max(0.0, safe_float(goal.get("saved"), 0))
        if tx_type == "withdraw":
            goal["saved"] = max(0.0, goal["saved"] - amount)
        else:
            goal["saved"] += amount
        goal["tx"] = list(goal.get("tx") or [])
        goal["tx"].insert(
            0,
            {
                "id": make_id(),
                "type": tx_type,
                "value": amount,
                "at": _now_iso(),
            },
        )

    return update_state(mutate, persist=persist)


def goals_summary(state=None):
    state = state or read_state()
    goals = []
    for goal in state.get("goals", []):
        name = normalize_goal_name(goal.get("name")) or "Objetivo"
        target = max(0.0, safe_float(goal.get("target"), 0))
        saved = max(0.0, safe_float(goal.get("saved"), 0))
        left = max(0.0, target - saved)
        pct = 100 if target <= 0 and saved > 0 else (round((saved / target) * 100) if target > 0 else 0)
        pct = max(0, min(100, pct))
        goals.append({"name": name, "target": target, "saved": saved, "left": left, "pct": pct})
    goals.sort(key=lambda item: (item["pct"], item["saved"]), reverse=True)
    return goals


def money(value):
    value = safe_float(value)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def balance_summary(state=None):
    state = state or read_state()
    credit = state["credit"]
    used = max(0.0, safe_float(credit.get("used"), 0))
    reserved = max(0.0, safe_float(credit.get("reserved"), 0))
    uncovered = max(0.0, used - reserved)
    coverage = 100 if used <= 0 and reserved > 0 else (round((reserved / used) * 100) if used > 0 else 0)
    coverage = max(0, min(100, coverage))
    return {
        "conta": state["balances"]["conta"]["amount"],
        "vale1": state["balances"]["vale1"]["amount"],
        "vale2": state["balances"]["vale2"]["amount"],
        "card_used": used,
        "card_reserved": reserved,
        "card_uncovered": uncovered,
        "card_coverage": coverage,
        "card_name": credit.get("name") or DEFAULT_STATE["credit"]["name"],
    }


def combined_history(limit=10, state=None):
    state = state or read_state()
    items = []
    for item in state.get("tx", []):
        label = state["balances"].get(item.get("account"), {}).get("label", item.get("account", "Carteira"))
        if item.get("type") == "in":
            kind = "Entrada"
            sign = "+"
        elif item.get("type") == "out":
            kind = "Saida"
            sign = "-"
        else:
            kind = "Ajuste"
            sign = "~"
        items.append(
            {
                "at": item.get("at", ""),
                "text": f"{kind} {label}",
                "sign": sign,
                "value": safe_float(item.get("value"), 0),
                "note": item.get("note", ""),
            }
        )

    for item in state.get("credit", {}).get("tx", []):
        tx_type = item.get("type")
        if tx_type == "expense":
            text = "Gasto cartao"
            sign = "-"
        elif tx_type == "payment":
            text = "Pagamento cartao"
            sign = "+"
        elif tx_type == "reserve-in":
            text = "Entrada reserva cartao"
            sign = "+"
        else:
            text = "Saida reserva cartao"
            sign = "-"
        items.append(
            {
                "at": item.get("at", ""),
                "text": text,
                "sign": sign,
                "value": safe_float(item.get("value"), 0),
                "note": item.get("desc", ""),
            }
        )

    for goal in state.get("goals", []):
        goal_name = normalize_goal_name(goal.get("name")) or "Objetivo"
        for item in goal.get("tx", []):
            tx_type = item.get("type")
            if tx_type == "withdraw":
                text = f"Retirada objetivo {goal_name}"
                sign = "-"
            elif tx_type == "yield":
                text = f"Rendimento objetivo {goal_name}"
                sign = "+"
            else:
                text = f"Deposito objetivo {goal_name}"
                sign = "+"
            items.append(
                {
                    "at": item.get("at", ""),
                    "text": text,
                    "sign": sign,
                    "value": safe_float(item.get("value"), 0),
                    "note": "",
                }
            )

    items.sort(key=lambda x: x.get("at", ""), reverse=True)
    return items[:limit]
