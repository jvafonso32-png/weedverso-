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


def _today_key():
    return datetime.now().strftime("%Y-%m-%d")


def _sorted_by_at(items, reverse=False):
    return sorted(
        list(items or []),
        key=lambda item: (
            str((item or {}).get("at") or ""),
            str((item or {}).get("id") or ""),
        ),
        reverse=reverse,
    )


def _capture_wallet_baselines(state):
    balances = (state or {}).get("balances") or {}
    baselines = {key: safe_float((item or {}).get("amount"), 0) for key, item in balances.items()}
    for item in list((state or {}).get("tx") or []):
        account = item.get("account")
        if account not in baselines:
            continue
        tx_type = str(item.get("type") or "")
        value = abs(safe_float(item.get("value"), 0))
        prev = safe_float(item.get("prev"), 0)
        if tx_type == "set":
            baselines[account] -= value - prev
        elif tx_type == "in":
            baselines[account] -= value
        elif tx_type == "out":
            baselines[account] += value
    return baselines


def _recompute_wallet_balances(state, baselines=None):
    balances = (state or {}).setdefault("balances", {})
    seed = baselines or _capture_wallet_baselines(state)
    for key, item in balances.items():
        item["amount"] = safe_float(seed.get(key), 0)
    for item in _sorted_by_at((state or {}).get("tx") or []):
        account = item.get("account")
        if account not in balances:
            continue
        tx_type = str(item.get("type") or "")
        value = abs(safe_float(item.get("value"), 0))
        if tx_type == "set":
            item["prev"] = safe_float(balances[account].get("amount"), 0)
            balances[account]["amount"] = value
        elif tx_type == "in":
            balances[account]["amount"] = safe_float(balances[account].get("amount"), 0) + value
        elif tx_type == "out":
            balances[account]["amount"] = safe_float(balances[account].get("amount"), 0) - value


def _recompute_credit_state(state):
    credit = (state or {}).setdefault("credit", {})
    credit["used"] = 0.0
    credit["reserved"] = 0.0
    credit["tx"] = list(credit.get("tx") or [])
    for item in _sorted_by_at(credit["tx"]):
        value = abs(safe_float(item.get("value"), 0))
        tx_type = str(item.get("type") or "")
        if tx_type == "expense":
            credit["used"] += value
        elif tx_type == "payment":
            credit["used"] = max(0.0, credit["used"] - value)
        elif tx_type == "reserve-in":
            credit["reserved"] += value
        elif tx_type == "reserve-out":
            credit["reserved"] = max(0.0, credit["reserved"] - value)


def _recompute_goal_saved(goal):
    if goal is None:
        return
    goal["saved"] = 0.0
    goal["tx"] = list(goal.get("tx") or [])
    for item in _sorted_by_at(goal["tx"]):
        value = abs(safe_float(item.get("value"), 0))
        if item.get("type") == "withdraw":
            goal["saved"] = max(0.0, safe_float(goal.get("saved"), 0) - value)
        else:
            goal["saved"] = safe_float(goal.get("saved"), 0) + value


def _resolve_named_entry(items, raw_name, item_label):
    target = fold_text(raw_name)
    raw_id = str(raw_name or "").strip()
    if not target and not raw_id:
        raise ValueError(f"Informe o nome do {item_label}.")

    exact = []
    for item in items:
        entry_name = fold_text(item.get("name"))
        entry_id = str(item.get("id") or "").strip()
        if raw_id and entry_id and raw_id == entry_id:
            exact.append(item)
            continue
        if target and entry_name == target:
            exact.append(item)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Existem {item_label}s duplicados com esse nome. Renomeie um deles no app.")

    partial = []
    for item in items:
        entry_name = fold_text(item.get("name"))
        if target and target in entry_name:
            partial.append(item)
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(f"Mais de um {item_label} combina com esse nome. Seja mais especifico.")
    raise ValueError(f"{titleize_words(item_label)} nao encontrado.")


def _apply_balance_transaction(
    state,
    account_alias,
    direction,
    value,
    note="",
    debtor_id="",
    my_debt_id="",
    my_debt_installment=0,
    at=None,
):
    amount = abs(safe_float(value))
    note = normalize_spaces(note)[:60]
    if amount <= 0:
        raise ValueError("O valor precisa ser maior que zero.")

    account_key = resolve_balance_key(account_alias, state)
    balances = (state or {}).setdefault("balances", {})
    balance = balances[account_key]
    balance["amount"] = safe_float(balance.get("amount"), 0)
    if direction == "in":
        balance["amount"] += amount
    elif direction == "out":
        balance["amount"] -= amount
    else:
        raise ValueError("Direcao invalida.")

    entry = normalize_balance_tx(
        {
            "id": make_id(),
            "account": account_key,
            "type": direction,
            "value": amount,
            "note": note,
            "debtorId": debtor_id,
            "myDebtId": my_debt_id,
            "myDebtInstallment": my_debt_installment,
            "at": at or _now_iso(),
            **build_category(note, "Sem categoria"),
        }
    )
    state.setdefault("tx", []).insert(0, entry)
    return account_key, entry


def add_balance_transaction(account_alias, direction, value, note="", persist=True):
    def mutate(state):
        _apply_balance_transaction(state, account_alias, direction, value, note)

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


def add_debtor(name, amount, note="", pay_date="", persist=True):
    debtor_name = normalize_spaces(name)[:30]
    debtor_amount = abs(safe_float(amount))
    debtor_note = normalize_spaces(note)[:50]
    if not debtor_name:
        raise ValueError("O nome do devedor e obrigatorio.")
    if debtor_amount <= 0:
        raise ValueError("O valor do devedor precisa ser maior que zero.")

    def mutate(state):
        debtors = state.setdefault("debtors", [])
        if any(fold_text(item.get("name")) == fold_text(debtor_name) for item in debtors):
            raise ValueError("Ja existe um devedor com esse nome. Use adicionar mais valor ou renomeie no app.")
        debtors.insert(
            0,
            normalize_debt_item(
                {
                    "id": make_id(),
                    "name": debtor_name,
                    "amount": debtor_amount,
                    "note": debtor_note,
                    "payDate": str(pay_date or ""),
                    "paid": False,
                    "paidAt": "",
                    "at": _now_iso(),
                }
            ),
        )
        state["debtors"] = debtors[:100]

    return update_state(mutate, persist=persist)


def adjust_debtor_amount(debtor_name, value, mode="add", note="", persist=True):
    amount = abs(safe_float(value))
    debtor_note = normalize_spaces(note)[:50]
    if amount <= 0:
        raise ValueError("O valor precisa ser maior que zero.")
    if mode not in {"add", "remove", "set"}:
        raise ValueError("Tipo de ajuste do devedor invalido.")

    def mutate(state):
        debtor = _resolve_named_entry(state.setdefault("debtors", []), debtor_name, "devedor")
        current_amount = max(0.0, safe_float(debtor.get("amount"), 0))
        if mode == "add":
            debtor["amount"] = current_amount + amount
        elif mode == "remove":
            debtor["amount"] = max(0.0, current_amount - amount)
        else:
            debtor["amount"] = amount
        debtor["installmentValue"] = debtor["amount"]

        if debtor_note:
            debtor["note"] = debtor_note
        if debtor["amount"] > 0:
            debtor["paid"] = False
            debtor["paidAt"] = ""
        elif mode in {"remove", "set"}:
            debtor["paid"] = True
            debtor["paidAt"] = debtor.get("paidAt") or _now_iso()
            if not debtor.get("payDate"):
                debtor["payDate"] = _today_key()

    return update_state(mutate, persist=persist)


def receive_debtor_in_account(debtor_name, account_alias="conta", note="", persist=True):
    debtor_note = normalize_spaces(note)[:50]

    def mutate(state):
        debtor = _resolve_named_entry(state.setdefault("debtors", []), debtor_name, "devedor")
        amount = max(0.0, safe_float(debtor.get("amount"), 0))
        if amount <= 0:
            raise ValueError("Esse devedor nao possui saldo em aberto.")
        now_iso = _now_iso()
        debtor["paid"] = True
        debtor["paidAt"] = now_iso
        if not debtor.get("payDate"):
            debtor["payDate"] = _today_key()
        payment_note = debtor_note or f"Recebido de {debtor.get('name') or 'Devedor'}"
        _apply_balance_transaction(state, account_alias, "in", amount, payment_note, debtor_id=debtor.get("id") or "", at=now_iso)

    return update_state(mutate, persist=persist)


def remove_debtor(debtor_name, persist=True):
    def mutate(state):
        debtors = state.setdefault("debtors", [])
        debtor = _resolve_named_entry(debtors, debtor_name, "devedor")
        debtor_id = str(debtor.get("id") or "")
        state["debtors"] = [item for item in debtors if str(item.get("id") or "") != debtor_id]
        for tx in state.setdefault("tx", []):
            if str(tx.get("debtorId") or "") == debtor_id:
                tx["debtorId"] = ""

    return update_state(mutate, persist=persist)


def add_my_debt(name, installment_value, installments=1, note="", pay_date="", persist=True):
    debt_name = normalize_spaces(name)[:30]
    unit_value = abs(safe_float(installment_value))
    total_installments = max(1, min(12, int(safe_float(installments, 1))))
    debt_note = normalize_spaces(note)[:50]
    if not debt_name:
        raise ValueError("O nome da divida e obrigatorio.")
    if unit_value <= 0:
        raise ValueError("O valor da parcela precisa ser maior que zero.")

    def mutate(state):
        debts = state.setdefault("myDebts", [])
        if any(fold_text(item.get("name")) == fold_text(debt_name) for item in debts):
            raise ValueError("Ja existe uma divida com esse nome. Use adicionar parcelas ou ajuste no app.")
        debts.insert(
            0,
            normalize_debt_item(
                {
                    "id": make_id(),
                    "name": debt_name,
                    "amount": unit_value,
                    "installmentValue": unit_value,
                    "installments": total_installments,
                    "installmentsPaid": 0,
                    "note": debt_note,
                    "payDate": str(pay_date or ""),
                    "paid": False,
                    "paidAt": "",
                    "at": _now_iso(),
                }
            ),
        )
        state["myDebts"] = debts[:100]

    return update_state(mutate, persist=persist)


def adjust_my_debt_installments(debt_name, delta, installment_value=None, note="", persist=True):
    change = int(safe_float(delta, 0))
    unit_value = None if installment_value is None else abs(safe_float(installment_value))
    debt_note = normalize_spaces(note)[:50]
    if change == 0:
        raise ValueError("Informe ao menos uma parcela para ajustar.")
    if unit_value is not None and unit_value <= 0:
        raise ValueError("O valor da parcela precisa ser maior que zero.")

    def mutate(state):
        debt = _resolve_named_entry(state.setdefault("myDebts", []), debt_name, "divida")
        current_installments = max(1, min(12, int(safe_float(debt.get("installments"), 1))))
        next_installments = max(1, min(12, current_installments + change))
        if next_installments == current_installments:
            raise ValueError("Nao foi possivel ajustar mais parcelas nessa divida.")
        debt["installments"] = next_installments
        if unit_value is not None:
            debt["amount"] = unit_value
            debt["installmentValue"] = unit_value
        debt["installmentsPaid"] = max(0, min(next_installments, int(safe_float(debt.get("installmentsPaid"), 0))))
        debt["paid"] = debt["installmentsPaid"] >= next_installments
        if not debt["paid"]:
            debt["paidAt"] = ""
        elif not debt.get("paidAt"):
            debt["paidAt"] = _now_iso()
        if debt_note:
            debt["note"] = debt_note

    return update_state(mutate, persist=persist)


def pay_my_debt_installments(debt_name, count=1, account_alias="conta", note="", persist=True):
    installments_to_pay = max(1, int(safe_float(count, 1)))
    debt_note = normalize_spaces(note)[:50]

    def mutate(state):
        debt = _resolve_named_entry(state.setdefault("myDebts", []), debt_name, "divida")
        total_installments = max(1, int(safe_float(debt.get("installments"), 1)))
        installments_paid = max(0, min(total_installments, int(safe_float(debt.get("installmentsPaid"), 0))))
        installment_value = max(0.0, safe_float(debt.get("installmentValue"), debt.get("amount")))
        if installment_value <= 0:
            raise ValueError("Essa divida nao possui valor de parcela valido.")
        remaining = max(0, total_installments - installments_paid)
        if remaining <= 0:
            raise ValueError("Essa divida ja esta quitada.")
        if installments_to_pay > remaining:
            raise ValueError(f"Restam apenas {remaining} parcela(s) em aberto.")

        now_iso = _now_iso()
        debt_name_label = debt.get("name") or "Divida"
        for _ in range(installments_to_pay):
            next_installment = installments_paid + 1
            payment_note = debt_note or f"Parcela {next_installment}/{total_installments} {debt_name_label}"
            _apply_balance_transaction(
                state,
                account_alias,
                "out",
                installment_value,
                payment_note,
                my_debt_id=debt.get("id") or "",
                my_debt_installment=next_installment,
                at=now_iso,
            )
            installments_paid = next_installment

        debt["installmentsPaid"] = installments_paid
        debt["paid"] = installments_paid >= total_installments
        debt["paidAt"] = now_iso if debt["paid"] else ""
        if debt_note:
            debt["note"] = debt_note
        if not debt.get("payDate"):
            debt["payDate"] = _today_key()

    return update_state(mutate, persist=persist)


def remove_my_debt(debt_name, persist=True):
    def mutate(state):
        debts = state.setdefault("myDebts", [])
        debt = _resolve_named_entry(debts, debt_name, "divida")
        debt_id = str(debt.get("id") or "")
        state["myDebts"] = [item for item in debts if str(item.get("id") or "") != debt_id]
        for tx in state.setdefault("tx", []):
            if str(tx.get("myDebtId") or "") == debt_id:
                tx["myDebtId"] = ""
                tx["myDebtInstallment"] = 0

    return update_state(mutate, persist=persist)


def delete_transaction_entry(source, tx_id, goal_id="", persist=True):
    source = normalize_spaces(source).lower()
    tx_id = str(tx_id or "").strip()
    goal_id = str(goal_id or "").strip()
    if not source or not tx_id:
        raise ValueError("Informe a origem e a transacao que deseja apagar.")

    def mutate(state):
        if source == "wallet":
            baselines = _capture_wallet_baselines(state)
            existing = next((item for item in state.setdefault("tx", []) if str(item.get("id") or "") == tx_id), None)
            if not existing:
                raise ValueError("Transacao nao encontrada.")
            debtor_id = str(existing.get("debtorId") or "")
            if debtor_id:
                debtor = next((item for item in state.setdefault("debtors", []) if str(item.get("id") or "") == debtor_id), None)
                if debtor:
                    debtor["paid"] = False
                    debtor["paidAt"] = ""
            my_debt_id = str(existing.get("myDebtId") or "")
            if my_debt_id:
                debt = next((item for item in state.setdefault("myDebts", []) if str(item.get("id") or "") == my_debt_id), None)
                if debt:
                    installments = max(1, int(safe_float(debt.get("installments"), 1)))
                    removed_installment = max(0, int(safe_float(existing.get("myDebtInstallment"), 0)))
                    fallback_paid = max(0, min(installments, int(safe_float(debt.get("installmentsPaid"), 0))))
                    debt["installmentsPaid"] = max(
                        0,
                        min(installments, removed_installment - 1 if removed_installment else fallback_paid - 1),
                    )
                    debt["paid"] = debt["installmentsPaid"] >= installments
                    if not debt["paid"]:
                        debt["paidAt"] = ""
            state["tx"] = [item for item in state.setdefault("tx", []) if str(item.get("id") or "") != tx_id]
            _recompute_wallet_balances(state, baselines)
            return

        if source == "credit":
            tx_list = state.setdefault("credit", {}).setdefault("tx", [])
            if not any(str(item.get("id") or "") == tx_id for item in tx_list):
                raise ValueError("Transacao nao encontrada.")
            state["credit"]["tx"] = [item for item in tx_list if str(item.get("id") or "") != tx_id]
            _recompute_credit_state(state)
            return

        if source == "goal":
            goals = state.setdefault("goals", [])
            goal = next((item for item in goals if str(item.get("id") or "") == goal_id), None)
            if goal is None:
                raise ValueError("Objetivo nao encontrado.")
            tx_list = list(goal.get("tx") or [])
            if not any(str(item.get("id") or "") == tx_id for item in tx_list):
                raise ValueError("Transacao nao encontrada.")
            goal["tx"] = [item for item in tx_list if str(item.get("id") or "") != tx_id]
            _recompute_goal_saved(goal)
            return

        raise ValueError("Origem da transacao invalida.")

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


def debtors_summary(state=None):
    state = state or read_state()
    debtors = []
    for item in state.get("debtors", []):
        entry = normalize_debt_item(item)
        debtors.append(
            {
                "id": str(entry.get("id") or ""),
                "name": entry["name"] or "Devedor",
                "amount": max(0.0, safe_float(entry.get("amount"), 0)),
                "note": normalize_spaces(entry.get("note")),
                "payDate": str(entry.get("payDate") or ""),
                "paid": bool(entry.get("paid")),
                "paidAt": str(entry.get("paidAt") or ""),
                "at": str(entry.get("at") or ""),
            }
        )
    debtors.sort(key=lambda item: (item["paid"], item["payDate"] or "9999-99-99", item["name"].lower()))
    return debtors


def my_debts_summary(state=None):
    state = state or read_state()
    debts = []
    for item in state.get("myDebts", []):
        entry = normalize_debt_item(item)
        installments = max(1, int(entry.get("installments") or 1))
        installments_paid = max(0, min(installments, int(entry.get("installmentsPaid") or 0)))
        installment_value = max(0.0, safe_float(entry.get("installmentValue"), entry.get("amount")))
        remaining_installments = max(0, installments - installments_paid)
        remaining_value = installment_value * remaining_installments
        debts.append(
            {
                "id": str(entry.get("id") or ""),
                "name": entry["name"] or "Divida",
                "installmentValue": installment_value,
                "installments": installments,
                "installmentsPaid": installments_paid,
                "remainingInstallments": remaining_installments,
                "remainingValue": remaining_value,
                "note": normalize_spaces(entry.get("note")),
                "payDate": str(entry.get("payDate") or ""),
                "paid": bool(entry.get("paid")),
                "paidAt": str(entry.get("paidAt") or ""),
                "at": str(entry.get("at") or ""),
            }
        )
    debts.sort(key=lambda item: (item["paid"], item["payDate"] or "9999-99-99", item["name"].lower()))
    return debts


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
                "source": "wallet",
                "txId": str(item.get("id") or ""),
                "goalId": "",
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
                "source": "credit",
                "txId": str(item.get("id") or ""),
                "goalId": "",
            }
        )

    for goal in state.get("goals", []):
        goal_name = normalize_goal_name(goal.get("name")) or "Objetivo"
        for item in goal.get("tx", []):
            tx_type = item.get("type")
            if tx_type == "withdraw":
                text = f"Saida objetivo {goal_name}"
                sign = "-"
            elif tx_type == "yield":
                text = f"Rendimento objetivo {goal_name}"
                sign = "+"
            else:
                text = f"Entrada objetivo {goal_name}"
                sign = "+"
            items.append(
                {
                    "at": item.get("at", ""),
                    "text": text,
                    "sign": sign,
                    "value": safe_float(item.get("value"), 0),
                    "note": "",
                    "source": "goal",
                    "txId": str(item.get("id") or ""),
                    "goalId": str(goal.get("id") or ""),
                }
            )

    items.sort(key=lambda x: (str(x.get("at") or ""), str(x.get("txId") or "")), reverse=True)
    if limit is None:
        return items
    return items[:limit]
