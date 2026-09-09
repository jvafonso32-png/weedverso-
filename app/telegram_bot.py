import json
import os
import re
import threading
import time
import unicodedata
from urllib import parse, request

from env_loader import load_env_file
from share_publish import current_share_info
from shared_state import (
    BALANCE_ALIASES,
    add_debtor,
    add_balance_transaction,
    add_credit_transaction,
    add_goal,
    add_my_debt,
    adjust_debtor_amount,
    adjust_my_debt_installments,
    balance_alias_map,
    balance_summary,
    combined_history,
    delete_transaction_entry,
    debtors_summary,
    fold_text,
    goals_summary,
    money,
    move_goal,
    my_debts_summary,
    pay_my_debt_installments,
    read_state,
    receive_debtor_in_account,
    remove_debtor,
    remove_my_debt,
    resolve_balance_key,
    titleize_words,
    using_state_file,
)
from telegram_chats import latest_chat_id, read_chats, register_chat
from telegram_runtime import (
    clear_telegram_test_state,
    read_runtime,
    set_telegram_test_mode,
    telegram_test_mode_enabled,
    telegram_test_state_file,
)

try:
    from desktop_cloud_sync import trigger_background_push
except Exception:
    def trigger_background_push(reason="telegram"):
        return False


load_env_file()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
ALLOWED_CHAT_IDS = {
    item.strip()
    for item in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if item.strip()
}
TRUTHY_WORDS = {"1", "true", "on", "yes", "sim"}
FALSY_WORDS = {"0", "false", "off", "no", "nao", "não"}

VALUE_RE = r"(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)(?:\s*(?:reais|real))?"
ACCOUNT_ALIASES = sorted({fold_text(alias) for alias in BALANCE_ALIASES.keys() if fold_text(alias)}, key=len, reverse=True)
GENERIC_ACCOUNT_ALIASES = {"saldo"}
QUERY_WORDS = {
    "saldo",
    "saldos",
    "quanto",
    "quantos",
    "tenho",
    "tem",
    "mostrar",
    "mostra",
    "mostre",
    "ver",
    "ve",
    "veja",
    "consulta",
    "consultar",
    "status",
    "como",
    "qual",
    "quais",
    "me",
    "diz",
    "diga",
    "fala",
    "quero",
    "preciso",
    "acompanhar",
    "confere",
    "confira",
    "sobrou",
    "restou",
    "disponivel",
    "disponível",
    "atual",
    "atualizado",
    "fechamento",
    "resumo",
    "panorama",
}
GREETING_WORDS = {
    "oi",
    "ola",
    "e ai",
    "eai",
    "hey",
    "bom dia",
    "boa tarde",
    "boa noite",
    "fala",
    "opa",
}
HELP_WORDS = {"ajuda", "help", "socorro", "manual", "comandos", "comando", "menu"}
DEBTOR_WORDS = {"devedor", "devedores", "quem me deve", "meus devedores", "valores a receber", "a receber"}
MY_DEBT_WORDS = {"minha divida", "minhas dividas", "meus debitos", "contas a pagar", "o que eu devo"}
CARD_WORDS = {"cartao", "credito", "fatura", "amex"}
RESERVE_WORDS = {"reserva", "reservado", "reservada", "separado", "separada"}
EXTRATO_WORDS = {"extrato", "extratos", "movimentacoes", "movimentação", "movimentacao", "lancamentos", "lançamento", "lancamento", "historico", "histórico"}
BALANCE_IN_WORDS = {
    "entrada",
    "entrou",
    "recebi",
    "recebo",
    "receber",
    "ganhei",
    "ganho",
    "ganhar",
    "caiu",
    "depositei",
    "deposito",
    "depositar",
    "deposita",
    "depositaram",
    "coloquei",
    "colocaram",
    "adicionei",
    "adicionaram",
    "acrescentei",
    "acrescentaram",
    "somei",
    "somaram",
    "creditei",
    "creditaram",
    "pingou",
    "veio",
    "caiu",
    "caíram",
    "ingressou",
    "depositou",
    "depositaram",
    "entrouzinho",
}
BALANCE_OUT_WORDS = {
    "saida",
    "saiu",
    "retirei",
    "retiro",
    "retirar",
    "retiraram",
    "tirei",
    "tiro",
    "tirar",
    "tiraram",
    "debitei",
    "debito",
    "debitar",
    "debitaram",
    "descontei",
    "desconto",
    "descontar",
    "descontaram",
    "saquei",
    "saco",
    "sacar",
    "saquearam",
    "transferi",
    "transfiro",
    "transferir",
    "transferiram",
    "enviei",
    "enviaram",
    "mandei",
    "mandaram",
    "usei",
    "use",
    "girei",
    "gastei",
    "gasto",
    "paguei",
    "pago",
    "pagar",
    "quitei",
    "baixei",
    "baixaram",
    "abati",
}
GOAL_IN_COMMANDS = {
    "entrada",
    "entrar",
    "depositar",
    "deposito",
    "aportar",
    "aporte",
    "guardar",
    "guardei",
    "colocar",
    "coloquei",
}
GOAL_OUT_COMMANDS = {
    "saida",
    "sair",
    "retirar",
    "retirei",
    "tirar",
    "tirei",
    "saque",
    "saquei",
    "remover",
    "removi",
    "abater",
    "abati",
}
GOAL_YIELD_COMMANDS = {
    "rendimento",
    "rendimentos",
    "render",
    "lucro",
    "lucros",
    "juros",
}
GOAL_ADD_COMMANDS = {
    "acrescentar",
    "acrescimo",
    "acrescer",
    "somar",
    "soma",
    "mais",
    "adicionar",
    "incrementar",
    "aumentar",
}
GOAL_YIELD_HINTS = {"rendimento", "rendimentos", "lucro", "lucros", "juros", "ganho", "ganhei", "rendeu"}
CARD_EXPENSE_WORDS = {
    "gastei",
    "gasto",
    "gastar",
    "passei",
    "passaram",
    "comprei",
    "compraram",
    "debitei",
    "lancei",
    "lancar",
    "cobrou",
    "cobraram",
    "parcelei",
    "parcelei",
    "paguei",
    "consumi",
    "consumiu",
    "anotei",
    "registrei",
    "marquei",
    "lancamento",
    "lancamento",
    "comprinha",
    "compra",
}
CARD_PAYMENT_WORDS = {"paguei", "abati", "abater", "amortizei", "amortizar", "quitei", "quitar", "antecipei", "pagamento"}
RESERVE_IN_WORDS = {"reservei", "guardei", "separei", "alimentei", "reforcei", "abasteci"}
RESERVE_OUT_WORDS = {"tirei", "retirei", "usei", "saquei", "consumi", "desfalquei"}
ACCOUNT_CONTEXT_WORDS = {
    "conta",
    "corrente",
    "banco",
    "pix",
    "ted",
    "transferencia",
    "transferência",
    "boleto",
    "saque",
    "dinheiro",
    "debito",
    "débito",
    "caixa",
    "agencia",
    "agência",
}
GENERAL_BALANCE_WORDS = {"financeiro", "geral", "resumo", "panorama", "visao", "contas"}
COMMON_FILLER_WORDS = {
    "o",
    "a",
    "os",
    "as",
    "um",
    "uma",
    "uns",
    "umas",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "no",
    "na",
    "nos",
    "nas",
    "em",
    "pro",
    "pra",
    "para",
    "com",
    "meu",
    "minha",
    "meus",
    "minhas",
    "por",
    "que",
    "isso",
    "agora",
    "hoje",
    "favor",
    "porfavor",
    "foi",
    "ser",
    "esta",
    "tava",
    "ta",
    "tô",
    "to",
    "uma",
    "deu",
    "fica",
}
DEBTOR_ADD_WORDS = {"adicionar", "adiciona", "adicione", "acrescentar", "acrescenta", "somar", "soma"}
DEBTOR_REMOVE_WORDS = {"remover", "remove", "tirar", "tira", "descontar", "desconta", "abater", "abate"}
DEBT_ACTION_WORDS = DEBTOR_ADD_WORDS | DEBTOR_REMOVE_WORDS | {"receber", "recebi", "quitar", "quitaram", "apagar", "deletar"}
INSTALLMENT_WORDS = {"parcela", "parcelas"}


def env_flag(name, default=False):
    raw_value = str(os.getenv(name, "") or "").strip().lower()
    if not raw_value:
        return default
    if raw_value in TRUTHY_WORDS:
        return True
    if raw_value in FALSY_WORDS:
        return False
    return default


def env_int(name, default=0):
    raw_value = str(os.getenv(name, "") or "").strip()
    if not raw_value:
        return max(0, default)
    try:
        return max(0, int(raw_value))
    except ValueError:
        return max(0, default)


AUTO_DELETE_SECONDS = env_int("TELEGRAM_AUTO_DELETE_SECONDS", 60)
DELETE_USER_MESSAGES = env_flag("TELEGRAM_DELETE_USER_MESSAGES", True)


def call_telegram(method, payload=None):
    if not TOKEN:
        raise RuntimeError("Defina TELEGRAM_BOT_TOKEN antes de iniciar o bot.")
    payload = payload or {}
    data = parse.urlencode(payload).encode("utf-8")
    req = request.Request(API_URL + method, data=data)
    with request.urlopen(req, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Falha na API do Telegram: {body}")
    return body["result"]


def send_message(chat_id, text):
    chunks = split_telegram_text(text)
    first_result = None
    for index, chunk in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": chunk}
        if index > 0:
            payload["disable_notification"] = "true"
        if is_plain_link_message(chunk):
            payload["disable_web_page_preview"] = "true"
        result = call_telegram("sendMessage", payload)
        schedule_delete_message(chat_id, (result or {}).get("message_id"))
        if first_result is None:
            first_result = result
    return first_result


def delete_message(chat_id, message_id):
    return call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def is_plain_link_message(text):
    return bool(re.match(r"^https?://\S+$", normalize_text(text)))


def split_telegram_text(text, max_len=900):
    normalized = str(text or "").strip()
    if not normalized:
        return [""]
    if len(normalized) <= max_len:
        return [normalized]

    chunks = []
    current = ""

    def push(value):
        value = str(value or "").strip()
        if value:
            chunks.append(value)

    for paragraph in re.split(r"\n{2,}", normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            push(current)
            current = ""

        if len(paragraph) <= max_len:
            current = paragraph
            continue

        block = ""
        for line in paragraph.splitlines():
            line = line.rstrip()
            candidate = line if not block else block + "\n" + line
            if len(candidate) <= max_len:
                block = candidate
                continue
            if block:
                push(block)
                block = ""
            if len(line) <= max_len:
                block = line
                continue
            for start in range(0, len(line), max_len):
                push(line[start : start + max_len])
        if block:
            current = block

    if current:
        push(current)
    return chunks or [normalized]


def current_state_snapshot():
    try:
        return json.dumps(read_state(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return ""


def _delete_message_after_delay(chat_id, message_id, delay_seconds):
    time.sleep(max(0, delay_seconds))
    return delete_message(chat_id, message_id)


def schedule_delete_message(chat_id, message_id, delay_seconds=None):
    delete_after = AUTO_DELETE_SECONDS if delay_seconds is None else max(0, int(delay_seconds))
    if delete_after <= 0 or not chat_id or not message_id:
        return False

    def worker():
        try:
            _delete_message_after_delay(chat_id, message_id, delete_after)
        except Exception as exc:
            print(f"Falha ao apagar mensagem {message_id} do chat {chat_id}: {exc}")

    thread = threading.Thread(
        target=worker,
        daemon=True,
        name=f"weedverso-telegram-delete-{chat_id}-{message_id}",
    )
    thread.start()
    return True


def schedule_user_message_cleanup(chat_id, message_id, delay_seconds=None):
    if not DELETE_USER_MESSAGES:
        return False
    return schedule_delete_message(chat_id, message_id, delay_seconds=delay_seconds)


def allowed_chat_ids():
    if ALLOWED_CHAT_IDS:
        return set(ALLOWED_CHAT_IDS)
    fallback = {
        str(os.getenv("WEEDVERSO_NOTIFY_CHAT_ID") or "").strip(),
        str(latest_chat_id() or "").strip(),
    }
    fallback.update(str(item.get("id") or "").strip() for item in read_chats())
    return {item for item in fallback if item}


def is_allowed(chat_id):
    allowed = allowed_chat_ids()
    if not allowed:
        return False
    return str(chat_id) in allowed


def parse_amount(raw_value):
    try:
        return float(str(raw_value).replace(",", "."))
    except ValueError:
        raise ValueError("Valor invalido. Exemplo: 150 ou 89,90.")


def normalize_text(text):
    return " ".join(str(text or "").strip().split())


def fold_text_keep_amounts(text):
    normalized = normalize_text(text)
    if not normalized:
        return ""
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    cleaned = []
    for char in normalized:
        cleaned.append(char if char.isalnum() or char in {",", ".", "$", "|"} else " ")
    return " ".join("".join(cleaned).split())


def normalize_desc(text, fallback="Sem categoria", drop_words=None):
    drop_words = set(drop_words or ())
    words = [word for word in fold_text(text).split() if word not in drop_words]
    label = titleize_words(" ".join(words)) or titleize_words(fallback) or fallback
    return label[:42]


def detect_account_alias(text):
    state = None
    try:
        state = read_state()
    except Exception:
        state = None
    aliases = sorted(
        {alias for alias in balance_alias_map(state).keys() if alias},
        key=len,
        reverse=True,
    )
    folded = f" {fold_text(text)} "
    matches = []
    for alias in aliases:
        if f" {alias} " in folded:
            matches.append(alias)
    if not matches:
        return ""
    for alias in matches:
        if alias not in GENERIC_ACCOUNT_ALIASES:
            return alias
    return matches[0]


def text_tokens(text):
    return set(fold_text(text).split())


def has_token(text, words):
    return bool(text_tokens(text) & set(words))


def has_phrase(text, phrases):
    folded = fold_text(text)
    return any(phrase in folded for phrase in phrases)


def is_query_like(text):
    folded = fold_text(text)
    tokens = set(folded.split())
    return bool(tokens & QUERY_WORDS) or has_phrase(
        folded,
        {
            "me mostra",
            "me mostre",
            "me diz",
            "me diga",
            "quero ver",
            "como ta",
            "como esta",
            "como anda",
            "como ficou",
            "quanto esta",
            "quanto ficou",
            "quanto sobrou",
            "quanto restou",
            "qual e o saldo",
            "qual o saldo",
            "me passa",
            "consulta pra mim",
        },
    )


def is_simple_account_balance_lookup(normalized):
    alias = detect_account_alias(normalized)
    if not alias:
        return False
    folded = fold_text(normalized)
    return folded == alias or folded in {f"saldo {alias}", f"saldo do {alias}", f"saldo da {alias}"}


def extract_amount(text):
    match = re.search(VALUE_RE, fold_text_keep_amounts(text), flags=re.IGNORECASE)
    if not match:
        return None
    return parse_amount(match.group(1))


def looks_like_write_intent(text):
    normalized = fold_text(text)
    if not normalized:
        return False
    if extract_amount(text) is None:
        return False
    tokens = text_tokens(normalized)
    write_words = (
        BALANCE_IN_WORDS
        | BALANCE_OUT_WORDS
        | CARD_EXPENSE_WORDS
        | CARD_PAYMENT_WORDS
        | RESERVE_IN_WORDS
        | RESERVE_OUT_WORDS
        | {"entrada", "saida", "deposito", "retirada", "pagamento", "ajuste", "ajustar"}
    )
    if tokens & write_words:
        return True
    return has_phrase(
        normalized,
        {
            "entrada de",
            "saida de",
            "gasto de",
            "pagamento de",
            "quanto entrou",
            "quanto saiu",
            "ajuste de saldo",
            "ajuste de saldos",
        },
    )


def remove_known_aliases(text):
    cleaned = fold_text(text)
    for alias in ACCOUNT_ALIASES:
        cleaned = re.sub(rf"\b{re.escape(alias)}\b", " ", cleaned)
    return " ".join(cleaned.split())


def compact_label(text, fallback="Sem categoria", extra_drop=None):
    cleaned = re.sub(VALUE_RE, " ", fold_text_keep_amounts(text), flags=re.IGNORECASE)
    cleaned = remove_known_aliases(cleaned)
    drop_words = COMMON_FILLER_WORDS | set(extra_drop or ())
    words = [word for word in cleaned.split() if word not in drop_words and word not in HELP_WORDS]
    return normalize_desc(" ".join(words), fallback, drop_words=drop_words)


def account_note_from_text(text, account_alias, fallback):
    extra_drop = {
        account_alias,
        "entrada",
        "saida",
        "deposito",
        "depositar",
        "depositei",
        "retirada",
        "retirar",
        "retirei",
        "saldo",
    }
    extra_drop |= BALANCE_IN_WORDS | BALANCE_OUT_WORDS | ACCOUNT_CONTEXT_WORDS
    return compact_label(text, fallback, extra_drop)


def card_note_from_text(text, fallback):
    extra_drop = CARD_WORDS | CARD_EXPENSE_WORDS | CARD_PAYMENT_WORDS | RESERVE_WORDS | RESERVE_IN_WORDS | RESERVE_OUT_WORDS
    return compact_label(text, fallback, extra_drop)


def find_goal_summary(goal_name, state=None):
    target = fold_text(goal_name)
    items = goals_summary(state)
    exact = [item for item in items if fold_text(item["name"]) == target]
    if exact:
        return exact[0]
    partial = [item for item in items if target and target in fold_text(item["name"])]
    if len(partial) == 1:
        return partial[0]
    raise ValueError("Objetivo nao encontrado ou ambiguo.")


def find_named_summary(goal_name, items, item_label):
    target = fold_text(goal_name)
    if not target:
        raise ValueError(f"Informe o nome do {item_label}.")
    exact = [item for item in items if fold_text(item.get("name")) == target or str(item.get("id") or "").strip() == str(goal_name).strip()]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Existem {item_label}s duplicados com esse nome.")
    partial = [item for item in items if target in fold_text(item.get("name"))]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(f"Mais de um {item_label} combina com esse nome.")
    raise ValueError(f"{titleize_words(item_label)} nao encontrado.")


def find_debtor_summary(debtor_name, state=None):
    return find_named_summary(debtor_name, debtors_summary(state), "devedor")


def find_my_debt_summary(debt_name, state=None):
    return find_named_summary(debt_name, my_debts_summary(state), "divida")


def split_pipe_sections(text):
    return [normalize_text(part) for part in str(text or "").split("|") if normalize_text(part)]


def parse_count(raw_value, label="quantidade"):
    raw_text = normalize_text(raw_value)
    if not raw_text:
        raise ValueError(f"Informe a {label}.")
    try:
        value = int(float(raw_text.replace(",", ".")))
    except ValueError:
        raise ValueError(f"{titleize_words(label)} invalida.")
    if value <= 0:
        raise ValueError(f"A {label} precisa ser maior que zero.")
    return value


def history_item_by_index(index, state=None):
    state = state or read_state()
    items = combined_history(limit=None, state=state)
    if index < 1 or index > len(items):
        raise ValueError("Nao encontrei essa transacao no extrato.")
    return items[index - 1]


def latest_history_item(state=None):
    return history_item_by_index(1, state=state)


def test_mode_prefix():
    return "MODO TESTE TELEGRAM ATIVO | nada foi salvo"


def decorate_test_reply(text):
    return "\n".join([test_mode_prefix(), text])


def format_test_mode_status():
    runtime = read_runtime()
    status = "ATIVO" if runtime["testMode"] else "INATIVO"
    updated_at = runtime.get("updatedAt") or "sem registro"
    return "\n".join(
        [
            f"Modo teste Telegram: {status}",
            f"Ultima mudanca: {updated_at}",
            "Quando estiver ativo, entradas, saidas, cartao e objetivos viram simulacao sem gravar nada.",
        ]
    )


def handle_test_mode_command(args):
    if not args:
        return format_test_mode_status()

    action = fold_text(args[0])
    if action in {"status", "estado", "como", "ver"}:
        return format_test_mode_status()
    if action in {"on", "ligar", "ativa", "ativar", "enable", "sim"}:
        clear_telegram_test_state()
        set_telegram_test_mode(True)
        return "\n".join(
            [
                "Modo teste Telegram ativado.",
                "A partir de agora, o bot responde normalmente em sandbox e nao salva alteracoes financeiras reais.",
            ]
        )
    if action in {"off", "desligar", "desativa", "desativar", "disable", "nao"}:
        set_telegram_test_mode(False)
        clear_telegram_test_state()
        return "\n".join(
            [
                "Modo teste Telegram desativado.",
                "O bot voltou a salvar alteracoes financeiras.",
            ]
        )
    raise ValueError("Use /modoteste on, /modoteste off ou /modoteste status.")


def format_account_balance(account_alias):
    state = read_state()
    key = resolve_balance_key(account_alias, state)
    item = state["balances"][key]
    return f"{item['label']}: {money(item['amount'])}"


def format_card_status():
    summary = balance_summary(read_state())
    return build_block(
        summary["card_name"],
        [
            f"Fatura atual: {money(summary['card_used'])}",
            f"Reservado: {money(summary['card_reserved'])}",
            f"Falta cobrir: {money(summary['card_uncovered'])}",
            f"Cobertura: {summary['card_coverage']}%",
        ],
    )


def format_short_date(value):
    raw = normalize_text(value)
    if not raw:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return f"{raw[8:10]}/{raw[5:7]}"
    if re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
        return f"{raw[8:10]}/{raw[5:7]}"
    return raw[:10]


def join_blocks(blocks):
    return "\n\n".join(str(block).strip() for block in blocks if str(block or "").strip())


def build_block(title, lines=None):
    rows = [str(title or "").strip()] if str(title or "").strip() else []
    for line in lines or []:
        line = str(line or "").strip()
        if line:
            rows.append(line)
    return "\n".join(rows)


def build_item_block(title, lines=None, prefix=""):
    header = f"{prefix}{title}".strip()
    rows = [header] if header else []
    for line in lines or []:
        line = str(line or "").strip()
        if line:
            rows.append(f"  {line}")
    return "\n".join(rows)


def help_text():
    return join_blocks(
        [
            build_block(
                "WEEDVERSO | GUIA RAPIDO",
                [
                    "Consultas e lancamentos em um formato mais direto para o Telegram.",
                    f"Limpeza automatica do chat: respostas do bot somem apos {AUTO_DELETE_SECONDS} segundos.",
                ],
            ),
            build_block(
                "CONSULTAS",
                [
                    "/saldos",
                    "/saldo",
                    "/extrato",
                    "/objetivos",
                    "/devedores",
                    "/dividas",
                    "/link",
                ],
            ),
            build_block(
                "LANCAMENTOS",
                [
                    "/entrada conta 150 salario",
                    "/saida mercado 42,50 compras",
                    "25 entrada conta",
                    "/cartao 89,90 uber",
                    "/pagarcartao 300 pagamento parcial",
                    "/reservacartao entrada 200",
                    "/reservacartao saida 50",
                    "/apagartransacao 1",
                    "remover ultima transacao",
                ],
            ),
            build_block(
                "DEVEDORES",
                [
                    "/devedor adicionar Lucas | 50 | pix atrasado | 2026-04-20",
                    "/devedor somar Lucas | 25",
                    "/devedor abater Lucas | 10",
                    "/devedor receber Lucas | conta",
                    "/devedor remover Lucas",
                ],
            ),
            build_block(
                "DIVIDAS",
                [
                    "/divida adicionar Notebook | 250 | 5 | parcelado | 2026-04-25",
                    "/divida parcelas Notebook | 2",
                    "/divida pagar Notebook | 1 | conta",
                    "/divida remover Notebook",
                ],
            ),
            build_block(
                "OBJETIVOS",
                [
                    "/objetivo criar Viagem Dubai | 12000",
                    "/objetivo entrada Viagem Dubai | 400",
                    "/objetivo saida Viagem Dubai | 100",
                    "/objetivo acrescentar Viagem Dubai | 35 | rendimento",
                    "/objetivo rendimento Viagem Dubai | 35",
                    "12,55 rendimento ganho em objetivo",
                ],
            ),
            build_block(
                "FRASES NATURAIS",
                [
                    "conta entrada 150 salario",
                    "conta saida 40 uber",
                    "gastei 38 no uber",
                    "passei 62 no cartao no ifood",
                    "recebi 1200 na conta salario",
                    "reservei 300 pro cartao",
                    "entrada 200 no objetivo viagem",
                    "saida 50 do objetivo viagem",
                    "acrescentar 25 de rendimento no objetivo viagem",
                    "quanto tenho na conta",
                    "como esta a fatura do cartao",
                    "adicionar mais 50 na categoria devedor para Lucas",
                    "adicionar divida notebook 250 em 5 parcelas",
                    "acrescentar 2 parcelas na divida notebook",
                    "pagar parcela da divida notebook",
                    "apagar transacao 1",
                    "devedores",
                    "minhas dividas",
                    "link weedverso",
                ],
            ),
            build_block(
                "MODO TESTE",
                [
                    "/modoteste on",
                    "/modoteste off",
                    "/modoteste status",
                    "Quando o modo teste esta ativo, nada financeiro e salvo de verdade.",
                ],
            ),
            build_block(
                "OBS",
                [
                    "Categorias sao agrupadas sem diferenca entre maiusculas, minusculas e acentos.",
                    "/meuid mostra o identificador do chat atual.",
                ],
            ),
        ]
    )


def format_saldos():
    state = read_state()
    summary = balance_summary(state)
    return join_blocks(
        [
            build_block(
                "WEEDVERSO | VISAO FINANCEIRA",
                [
                    f"{state['balances']['conta']['label']}: {money(summary['conta'])}",
                    f"{state['balances']['vale1']['label']}: {money(summary['vale1'])}",
                    f"{state['balances']['vale2']['label']}: {money(summary['vale2'])}",
                ],
            ),
            build_block(
                summary["card_name"],
                [
                    f"Fatura atual: {money(summary['card_used'])}",
                    f"Reservado: {money(summary['card_reserved'])}",
                    f"Falta cobrir: {money(summary['card_uncovered'])}",
                    f"Cobertura: {summary['card_coverage']}%",
                ],
            ),
        ]
    )


def format_extrato():
    items = combined_history(limit=12)
    if not items:
        return "Sem movimentacoes recentes."
    blocks = [build_block("ULTIMAS MOVIMENTACOES", ["As 12 mais recentes.", "Para apagar: /apagartransacao numero"])]
    for index, item in enumerate(items, start=1):
        detail_lines = [
            f"{item['sign']} {money(item['value'])}",
        ]
        if item.get("note"):
            detail_lines.append(f"Obs: {item['note']}")
        if item.get("at"):
            detail_lines.append(f"Data: {format_short_date(item['at'])}")
        blocks.append(build_item_block(f"{index}. {item['text']}", detail_lines))
    return join_blocks(blocks)


def format_goals():
    items = goals_summary()
    if not items:
        return "Nenhum objetivo cadastrado."
    blocks = [build_block("OBJETIVOS ATIVOS", [f"Total visivel: {min(len(items), 8)} de {len(items)}"])]
    for index, item in enumerate(items[:8], start=1):
        blocks.append(
            build_item_block(
                f"{index}. {item['name']}",
                [
                    f"Guardado: {money(item['saved'])} de {money(item['target'])}",
                    f"Progresso: {item['pct']}%",
                    f"Falta: {money(item['left'])}",
                ],
            )
        )
    return join_blocks(blocks)


def format_debtors():
    items = debtors_summary()
    if not items:
        return "Nenhum devedor cadastrado."
    open_items = [item for item in items if not item.get("paid")]
    if not open_items:
        return "Nenhum devedor em aberto."
    total_open = sum(float(item.get("amount") or 0) for item in open_items)
    blocks = [
        build_block(
            "DEVEDORES",
            [
                f"Em aberto: {len(open_items)}",
                f"Total a receber: {money(total_open)}",
            ],
        )
    ]
    for index, item in enumerate(open_items[:8], start=1):
        detail_lines = [f"Valor: {money(item['amount'])}"]
        if item.get("payDate"):
            detail_lines.append(f"Vence: {format_short_date(item['payDate'])}")
        if item.get("note"):
            detail_lines.append(f"Obs: {item['note']}")
        blocks.append(build_item_block(f"{index}. {item['name']}", detail_lines))
    return join_blocks(blocks)


def format_my_debts():
    items = my_debts_summary()
    if not items:
        return "Nenhuma divida propria cadastrada."
    open_items = [item for item in items if not item.get("paid")]
    if not open_items:
        return "Nenhuma divida em aberto."
    total_open = sum(float(item.get("remainingValue") or 0) for item in open_items)
    blocks = [
        build_block(
            "MINHAS DIVIDAS",
            [
                f"Em aberto: {len(open_items)}",
                f"Total restante: {money(total_open)}",
            ],
        )
    ]
    for index, item in enumerate(open_items[:8], start=1):
        detail_lines = [
            f"Restante: {money(item['remainingValue'])}",
            f"Parcelas: {item['installmentsPaid']}/{item['installments']}",
            f"Valor da parcela: {money(item['installmentValue'])}",
        ]
        if item.get("payDate"):
            detail_lines.append(f"Vence: {format_short_date(item['payDate'])}")
        if item.get("note"):
            detail_lines.append(f"Obs: {item['note']}")
        blocks.append(build_item_block(f"{index}. {item['name']}", detail_lines))
    return join_blocks(blocks)


def format_share_link():
    info = current_share_info()
    preferred = str(((info or {}).get("links") or {}).get("preferred") or "").strip()
    if not preferred:
        return "Link do Weedverso ainda nao foi publicado."
    return preferred.split("?", 1)[0].rstrip("/")


def format_connection(chat_id):
    whitelist = "restrita"
    token_status = "ok" if TOKEN else "faltando"
    return "\n".join(
        [
            "weedverso | conexao telegram",
            f"Chat ID: {chat_id}",
            f"Token: {token_status}",
            f"Whitelist: {whitelist}",
            "Defina TELEGRAM_ALLOWED_CHAT_IDS no .env para travar explicitamente os chats autorizados.",
        ]
    )


def send_test_snapshot(chat_id):
    if not chat_id:
        chat_id = latest_chat_id()
    if not chat_id:
        raise ValueError("Nenhum chat registrado ainda.")
    message = "\n".join(["Teste inicial do weedverso", format_saldos()])
    send_message(chat_id, message)
    return "Teste enviado no Telegram."


def parse_balance_command_args(args):
    if len(args) < 2:
        raise ValueError("Use: /entrada conta 150 descricao ou /saida mercado 20 lanche")
    state = read_state()
    first, second = args[0], args[1]
    try:
        account = resolve_balance_key(first, state)
        value = parse_amount(second)
        note = " ".join(args[2:]).strip()
        return account, value, note
    except Exception:
        value = parse_amount(first)
        account = resolve_balance_key(second, state)
        note = " ".join(args[2:]).strip()
        return account, value, note


def handle_balance_command(direction, args, persist=True):
    account_key, value, note = parse_balance_command_args(args)
    state = add_balance_transaction(account_key, "in" if direction == "entrada" else "out", value, note, persist=persist)
    label = state["balances"][account_key]["label"]
    return f"{'Entrada' if direction == 'entrada' else 'Saida'} registrada em {label}.\nSaldo atual: {money(state['balances'][account_key]['amount'])}"


def handle_cartao_command(kind, args, persist=True):
    if not args:
        raise ValueError("Informe o valor. Exemplo: /cartao 89,90 uber")
    value = parse_amount(args[0])
    desc = normalize_text(" ".join(args[1:]).strip())
    tx_kind = "expense" if kind == "gasto" else "payment"
    state = add_credit_transaction(tx_kind, value, desc, persist=persist)
    return f"{'Gasto' if tx_kind == 'expense' else 'Pagamento'} registrado no cartao.\nFatura atual: {money(state['credit']['used'])}"


def handle_reserva_command(args, persist=True):
    if len(args) < 2:
        raise ValueError("Use: /reservacartao entrada 200 ou /reservacartao saida 50")
    direction = fold_text(args[0])
    value = parse_amount(args[1])
    if direction not in {"entrada", "saida"}:
        raise ValueError("Use entrada ou saida.")
    state = add_credit_transaction("reserve-in" if direction == "entrada" else "reserve-out", value, "Reserva cartao", persist=persist)
    return f"Reserva do cartao atualizada.\nSaldo reservado: {money(state['credit']['reserved'])}"


def split_pipe_payload(text):
    if "|" not in text:
        raise ValueError("Use o formato Nome do objetivo | valor")
    left, right = text.rsplit("|", 1)
    name = normalize_text(left)
    value = parse_amount(right.strip())
    return name, value


def split_goal_move_payload(text):
    parts = split_pipe_sections(text)
    if len(parts) < 2:
        raise ValueError("Use o formato Nome do objetivo | valor | tipo(opcional)")
    return titleize_words(parts[0]), parse_amount(parts[1]), parts[2] if len(parts) > 2 else ""


def infer_goal_target_name(goal_hint, state=None):
    state = state or read_state()
    raw_name = normalize_text(goal_hint)
    raw_name = re.sub(r"^(?:o|a|um|uma|meu|minha|meus|minhas)\s+", "", raw_name, flags=re.IGNORECASE).strip()
    raw_name = re.sub(r"^(?:objetivo|objetivos|meta|metas)\s*", "", raw_name, flags=re.IGNORECASE).strip()
    raw_name = re.sub(r"\s+(?:objetivo|objetivos|meta|metas)\s*$", "", raw_name, flags=re.IGNORECASE).strip()
    if raw_name and fold_text(raw_name) not in {"objetivo", "objetivos", "meta", "metas"}:
        return titleize_words(raw_name), None

    goals = goals_summary(state)
    if not goals:
        return None, "Nenhum objetivo ativo encontrado."
    if len(goals) == 1:
        return goals[0]["name"], None
    return None, "Informe qual objetivo voce quer movimentar."


def detect_goal_move_type(text):
    normalized = fold_text(text)
    tokens = set(normalized.split())
    if tokens & (GOAL_YIELD_COMMANDS | GOAL_YIELD_HINTS):
        return "yield"
    if tokens & GOAL_OUT_COMMANDS:
        return "withdraw"
    if tokens & GOAL_IN_COMMANDS:
        return "deposit"
    if tokens & GOAL_ADD_COMMANDS:
        if tokens & GOAL_YIELD_HINTS:
            return "yield"
        return "deposit"
    return None


def compact_goal_target_hint(text):
    raw_text = normalize_text(text)
    raw_text = re.sub(r"\b(?:no|na|em|do|da|de)\s+(?:objetivo|objetivos|meta|metas)\b", " ", raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r"\b(?:objetivo|objetivos|meta|metas)\b", " ", raw_text, flags=re.IGNORECASE)
    keep_words = []
    for word in raw_text.split():
        folded_word = fold_text(word)
        if folded_word in COMMON_FILLER_WORDS:
            continue
        if folded_word in GOAL_IN_COMMANDS | GOAL_OUT_COMMANDS | GOAL_YIELD_COMMANDS | GOAL_ADD_COMMANDS | GOAL_YIELD_HINTS:
            continue
        keep_words.append(word)
    return normalize_text(" ".join(keep_words))


def goal_move_type_from_action(action, hint=""):
    folded_action = fold_text(action)
    folded_hint = fold_text(hint)
    hint_tokens = set(folded_hint.split())

    if folded_action in GOAL_OUT_COMMANDS:
        return "withdraw"
    if folded_action in GOAL_YIELD_COMMANDS:
        return "yield"
    if folded_action in GOAL_IN_COMMANDS:
        return "deposit"
    if folded_action in GOAL_ADD_COMMANDS:
        if folded_hint in GOAL_YIELD_HINTS or bool(hint_tokens & GOAL_YIELD_HINTS):
            return "yield"
        return "deposit"
    raise ValueError("Use criar, entrada, saida, acrescentar ou rendimento.")


def goal_move_reply(goal_name, move_type, value, persist=True):
    state = move_goal(goal_name, move_type, value, persist=persist)
    goal = find_goal_summary(goal_name, state)
    prefix = {
        "deposit": "Entrada registrada",
        "withdraw": "Saida registrada",
        "yield": "Rendimento registrado",
    }[move_type]
    return f"{prefix} em {goal['name']}.\nGuardado: {money(goal['saved'])}"


def handle_goal_command(args, persist=True):
    if not args:
        return format_goals()

    action = fold_text(args[0])
    payload = normalize_text(" ".join(args[1:]))

    if action in {"listar", "lista", "status"}:
        return format_goals()
    if action in {"criar", "novo", "adicionar"}:
        name, value = split_pipe_payload(payload)
        state = add_goal(name, value, persist=persist)
        goal = find_goal_summary(name, state)
        return f"Objetivo criado: {goal['name']}.\nMeta inicial: {money(goal['target'])}"
    if action in GOAL_IN_COMMANDS | GOAL_OUT_COMMANDS | GOAL_YIELD_COMMANDS | GOAL_ADD_COMMANDS:
        name, value, hint = split_goal_move_payload(payload)
        move_type = goal_move_type_from_action(action, hint=hint)
        return goal_move_reply(name, move_type, value, persist=persist)

    raise ValueError("Use /objetivo criar|entrada|saida|acrescentar|rendimento Nome | valor")


def handle_debtor_command(args, persist=True):
    if not args:
        return format_debtors()

    action = fold_text(args[0])
    payload = normalize_text(" ".join(args[1:]))
    parts = split_pipe_sections(payload)

    if action in {"listar", "lista", "status"}:
        return format_debtors()
    if action in {"criar", "novo", "nova", "adicionar"}:
        if len(parts) < 2:
            raise ValueError("Use /devedor adicionar Nome | valor | observacao | 2026-04-20")
        name = titleize_words(parts[0])
        value = parse_amount(parts[1])
        note = parts[2] if len(parts) > 2 else ""
        pay_date = parts[3] if len(parts) > 3 else ""
        state = add_debtor(name, value, note, pay_date, persist=persist)
        item = find_debtor_summary(name, state)
        return f"Devedor cadastrado: {item['name']}.\nTotal em aberto: {money(item['amount'])}"
    if action in {"somar", "mais", "acrescentar"}:
        if len(parts) < 2:
            raise ValueError("Use /devedor somar Nome | valor | observacao")
        name = titleize_words(parts[0])
        value = parse_amount(parts[1])
        note = parts[2] if len(parts) > 2 else ""
        state = adjust_debtor_amount(name, value, mode="add", note=note, persist=persist)
        item = find_debtor_summary(name, state)
        return f"Saldo devedor atualizado para {item['name']}.\nNovo total: {money(item['amount'])}"
    if action in {"abater", "tirar", "descontar"}:
        if len(parts) < 2:
            raise ValueError("Use /devedor abater Nome | valor")
        name = titleize_words(parts[0])
        value = parse_amount(parts[1])
        note = parts[2] if len(parts) > 2 else ""
        state = adjust_debtor_amount(name, value, mode="remove", note=note, persist=persist)
        item = find_debtor_summary(name, state)
        return f"Valor abatido para {item['name']}.\nNovo total: {money(item['amount'])}"
    if action in {"receber", "quitar"}:
        if not parts:
            raise ValueError("Use /devedor receber Nome | conta | observacao")
        name = titleize_words(parts[0])
        account_alias = parts[1] if len(parts) > 1 else "conta"
        note = parts[2] if len(parts) > 2 else ""
        state = receive_debtor_in_account(name, account_alias=account_alias, note=note, persist=persist)
        item = find_debtor_summary(name, state)
        account_key = resolve_balance_key(account_alias, state)
        return (
            f"Recebimento de {item['name']} lançado em {state['balances'][account_key]['label']}.\n"
            f"Saldo atual: {money(state['balances'][account_key]['amount'])}"
        )
    if action in {"remover", "apagar", "deletar"}:
        name = titleize_words(parts[0] if parts else payload)
        item = find_debtor_summary(name)
        remove_debtor(name, persist=persist)
        return f"Devedor removido: {item['name']}."

    raise ValueError("Use /devedor adicionar|somar|abater|receber|remover Nome | ...")


def handle_my_debt_command(args, persist=True):
    if not args:
        return format_my_debts()

    action = fold_text(args[0])
    payload = normalize_text(" ".join(args[1:]))
    parts = split_pipe_sections(payload)

    if action in {"listar", "lista", "status"}:
        return format_my_debts()
    if action in {"criar", "nova", "novo", "adicionar"}:
        if len(parts) < 2:
            raise ValueError("Use /divida adicionar Nome | valor da parcela | parcelas | observacao | 2026-04-20")
        name = titleize_words(parts[0])
        installment_value = parse_amount(parts[1])
        installments = parse_count(parts[2], "quantidade de parcelas") if len(parts) > 2 else 1
        note = parts[3] if len(parts) > 3 else ""
        pay_date = parts[4] if len(parts) > 4 else ""
        state = add_my_debt(name, installment_value, installments, note, pay_date, persist=persist)
        item = find_my_debt_summary(name, state)
        return (
            f"Divida cadastrada: {item['name']}.\n"
            f"Parcelas: {item['installments']}x de {money(item['installmentValue'])}"
        )
    if action in {"parcelas", "acrescentar", "somar"}:
        if len(parts) < 2:
            raise ValueError("Use /divida parcelas Nome | quantidade")
        name = titleize_words(parts[0])
        change = parse_count(parts[1], "quantidade de parcelas")
        installment_value = parse_amount(parts[2]) if len(parts) > 2 and parts[2] else None
        note = parts[3] if len(parts) > 3 else ""
        state = adjust_my_debt_installments(name, change, installment_value=installment_value, note=note, persist=persist)
        item = find_my_debt_summary(name, state)
        return (
            f"Parcelas ajustadas em {item['name']}.\n"
            f"Agora sao {item['installments']}x de {money(item['installmentValue'])}"
        )
    if action in {"pagar", "parcela", "quitaparcela"}:
        if not parts:
            raise ValueError("Use /divida pagar Nome | quantidade | conta | observacao")
        name = titleize_words(parts[0])
        count = parse_count(parts[1], "quantidade de parcelas") if len(parts) > 1 else 1
        account_alias = parts[2] if len(parts) > 2 else "conta"
        note = parts[3] if len(parts) > 3 else ""
        state = pay_my_debt_installments(name, count=count, account_alias=account_alias, note=note, persist=persist)
        item = find_my_debt_summary(name, state)
        account_key = resolve_balance_key(account_alias, state)
        return (
            f"Pagamento registrado para {item['name']} em {state['balances'][account_key]['label']}.\n"
            f"Parcelas pagas: {item['installmentsPaid']}/{item['installments']} | Restante: {money(item['remainingValue'])}"
        )
    if action in {"remover", "apagar", "deletar"}:
        name = titleize_words(parts[0] if parts else payload)
        item = find_my_debt_summary(name)
        remove_my_debt(name, persist=persist)
        return f"Divida removida: {item['name']}."

    raise ValueError("Use /divida adicionar|parcelas|pagar|remover Nome | ...")


def handle_delete_transaction_command(args, persist=True):
    if not args:
        raise ValueError("Use /apagartransacao numero-do-extrato")
    index = parse_count(args[0], "posicao do extrato")
    item = history_item_by_index(index)
    delete_transaction_entry(item.get("source"), item.get("txId"), item.get("goalId") or "", persist=persist)
    note = f"\nObs: {item['note']}" if item.get("note") else ""
    return f"Transacao {index} apagada: {item['text']} {item['sign']} {money(item['value'])}{note}"


def handle_delete_last_transaction_command(persist=True):
    item = latest_history_item()
    delete_transaction_entry(item.get("source"), item.get("txId"), item.get("goalId") or "", persist=persist)
    note = f"\nObs: {item['note']}" if item.get("note") else ""
    return f"Ultima transacao apagada: {item['text']} {item['sign']} {money(item['value'])}{note}"


def format_query_goal(text):
    goal_name = normalize_text(
        re.sub(
            r"^(?:como esta|quanto tem|quanto tenho|mostrar|mostra|ver|status do|status da|saldo do|saldo da|saldo de|saldo)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
    )
    goal_name = re.sub(r"^(?:meu|minha|meus|minhas)\s+", "", goal_name, flags=re.IGNORECASE).strip()
    goal_name = re.sub(r"^(?:objetivos|objetivo|metas|meta)\s*", "", goal_name, flags=re.IGNORECASE).strip()
    if not goal_name or fold_text(goal_name) in {"objetivo", "objetivos", "meta", "metas", "saldo"}:
        return format_goals()
    goal = find_goal_summary(goal_name)
    return f"{goal['name']} | {money(goal['saved'])} de {money(goal['target'])} | {goal['pct']}% | faltam {money(goal['left'])}"


def try_parse_natural_goal(text, persist=True):
    raw_text = normalize_text(text)
    normalized = fold_text(text)
    normalized_amounts = fold_text_keep_amounts(text)
    amount = extract_amount(text)

    match = re.match(rf"^(?:criar|crie|adicionar|adicione|novo|nova)(?:\s+(?:objetivo|meta))?\s+(.+?)\s*\|\s*{VALUE_RE}$", raw_text, flags=re.IGNORECASE)
    if match:
        name = titleize_words(match.group(1))
        value = parse_amount(match.group(2))
        add_goal(name, value, persist=persist)
        return f"Objetivo criado: {name}.\nMeta inicial: {money(value)}"

    match = re.match(
        rf"^(?:entrada|entrar|deposito|depositar|depositei|guardar|guardei|colocar|coloquei|aporte|aportar|aportei)\s+{VALUE_RE}\s+(?:no|na|em)\s+(?:objetivo|meta)\s+(.+)$",
        normalized_amounts,
    )
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        return goal_move_reply(goal_name, "deposit", value, persist=persist)

    match = re.match(
        rf"^(?:saida|sair|retirar|retirei|tirar|tirei|saquei|remover|removi|abater|abati)\s+{VALUE_RE}\s+(?:do|da|de)\s+(?:objetivo|meta)\s+(.+)$",
        normalized_amounts,
    )
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        return goal_move_reply(goal_name, "withdraw", value, persist=persist)

    match = re.match(
        rf"^(?:rendimento|rendimentos|juros|lucro|lucros|rendeu|teve rendimento de|rendimento de|lucrou)\s+{VALUE_RE}\s+(?:no|na|em)\s+(?:objetivo|meta)\s+(.+)$",
        normalized_amounts,
    )
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        return goal_move_reply(goal_name, "yield", value, persist=persist)

    match = re.match(
        rf"^(?:adicionar|adicione|acrescentar|acrescente|somar|some|mais|incrementar|aumentar)\s+{VALUE_RE}(?:\s+de\s+((?:rendimento|rendimentos|juros|lucro|lucros)))?\s+(?:no|na|em)\s+(?:objetivo|meta)\s+(.+)$",
        normalized_amounts,
    )
    if match:
        value = parse_amount(match.group(1))
        hint = match.group(2) or ""
        goal_name = titleize_words(match.group(3))
        move_type = "yield" if fold_text(hint) in GOAL_YIELD_HINTS else "deposit"
        return goal_move_reply(goal_name, move_type, value, persist=persist)

    if amount is not None and ("objetivo" in normalized or "meta" in normalized):
        move_type = detect_goal_move_type(normalized_amounts)
        if move_type:
            state = read_state()
            amountless_text = normalize_text(re.sub(VALUE_RE, " ", normalized_amounts, count=1))
            goal_hint = compact_goal_target_hint(amountless_text)
            goal_name, error_reply = infer_goal_target_name(goal_hint, state)
            if error_reply:
                return error_reply
            return goal_move_reply(goal_name, move_type, amount, persist=persist)

    if ("objetivo" in normalized or "meta" in normalized) and any(word in normalized.split() for word in QUERY_WORDS):
        try:
            return format_query_goal(text)
        except Exception:
            return format_goals()

    return None


def try_parse_natural_transaction_delete(text, persist=True):
    normalized = fold_text(text)
    if re.match(
        r"^(?:apagar|apaga|deletar|delete|remover|remove|desfazer|desfaz)\s+(?:a\s+)?(?:ultima|ultimo)\s+(?:transacao|lancamento|movimentacao|movimento|registro)?$",
        normalized,
    ):
        return handle_delete_last_transaction_command(persist=persist)
    match = re.match(r"^(?:apagar|apaga|deletar|delete|remover|remove)\s+(?:a\s+)?transacao\s+(\d+)$", normalized)
    if not match:
        return None
    return handle_delete_transaction_command([match.group(1)], persist=persist)


def try_parse_natural_debtor_flow(text, persist=True):
    normalized_amounts = fold_text_keep_amounts(text)

    match = re.match(
        rf"^(?:adicionar|adicionar|acrescentar|somar)(?:\s+mais)?\s+{VALUE_RE}\s+(?:na|no)\s+(?:categoria\s+)?devedor(?:\s+para)?\s+(.+)$",
        normalized_amounts,
    )
    if match:
        value = parse_amount(match.group(1))
        name = titleize_words(match.group(2))
        try:
            state = adjust_debtor_amount(name, value, mode="add", persist=persist)
        except ValueError as exc:
            if "nao encontrado" not in fold_text(str(exc)):
                raise
            state = add_debtor(name, value, persist=persist)
        item = find_debtor_summary(name, state)
        return f"Saldo devedor atualizado para {item['name']}.\nNovo total: {money(item['amount'])}"

    match = re.match(rf"^(?:criar|cadastrar|adicionar|novo|nova)\s+(?:um\s+|uma\s+)?devedor(?:\s+para)?\s+(.+?)\s+{VALUE_RE}(?:\s+(.+))?$", normalized_amounts)
    if match:
        name = titleize_words(match.group(1))
        value = parse_amount(match.group(2))
        note = normalize_desc(match.group(3) or "", "Sem observacao")
        note_value = note if note != "Sem Observacao" else ""
        try:
            state = add_debtor(name, value, note=note_value, persist=persist)
            item = find_debtor_summary(name, state)
            return f"Devedor cadastrado: {item['name']}.\nTotal em aberto: {money(item['amount'])}"
        except ValueError as exc:
            if "ja existe um devedor" not in fold_text(str(exc)):
                raise
            state = adjust_debtor_amount(name, value, mode="add", note=note_value, persist=persist)
        item = find_debtor_summary(name, state)
        return f"Saldo devedor atualizado para {item['name']}.\nNovo total: {money(item['amount'])}"

    match = re.match(rf"^(?:remover|tirar|descontar|abater)\s+{VALUE_RE}\s+(?:do|da)\s+(?:categoria\s+)?devedor(?:\s+para)?\s+(.+)$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        name = titleize_words(match.group(2))
        state = adjust_debtor_amount(name, value, mode="remove", persist=persist)
        item = find_debtor_summary(name, state)
        return f"Valor abatido para {item['name']}.\nNovo total: {money(item['amount'])}"

    match = re.match(r"^(?:receber|quitar|quitei)\s+(?:o\s+)?devedor\s+(.+?)(?:\s+(?:na|no)\s+(.+))?$", normalized_amounts)
    if match:
        name = titleize_words(match.group(1))
        account_alias = normalize_text(match.group(2) or "conta")
        state = receive_debtor_in_account(name, account_alias=account_alias, persist=persist)
        account_key = resolve_balance_key(account_alias, state)
        return (
            f"Recebimento de {name} lançado em {state['balances'][account_key]['label']}.\n"
            f"Saldo atual: {money(state['balances'][account_key]['amount'])}"
        )

    match = re.match(r"^(?:remover|apagar|deletar)\s+(?:o\s+)?devedor\s+(.+)$", normalized_amounts)
    if match:
        name = titleize_words(match.group(1))
        item = find_debtor_summary(name)
        remove_debtor(name, persist=persist)
        return f"Devedor removido: {item['name']}."

    return None


def try_parse_natural_my_debt_flow(text, persist=True):
    normalized_amounts = fold_text_keep_amounts(text)

    match = re.match(
        rf"^(?:adicionar|criar|cadastrar|novo|nova)\s+(?:uma\s+)?(?:divida|debito)\s+(?:de\s+)?(.+?)\s+{VALUE_RE}(?:\s+(?:em|de)\s+(\d+)\s+parcelas?)?(?:\s+(.+))?$",
        normalized_amounts,
    )
    if match:
        name = titleize_words(match.group(1))
        installment_value = parse_amount(match.group(2))
        installments = parse_count(match.group(3), "quantidade de parcelas") if match.group(3) else 1
        note = normalize_desc(match.group(4) or "", "Sem observacao")
        state = add_my_debt(name, installment_value, installments, note=note if note != "Sem Observacao" else "", persist=persist)
        item = find_my_debt_summary(name, state)
        return f"Divida cadastrada: {item['name']}.\nParcelas: {item['installments']}x de {money(item['installmentValue'])}"

    match = re.match(
        r"^(?:acrescentar|adicionar|somar)\s+(\d+)\s+parcelas?\s+(?:na|da|de|para)\s+(?:divida|debito)\s+(.+)$",
        normalized_amounts,
    )
    if match:
        installments = parse_count(match.group(1), "quantidade de parcelas")
        name = titleize_words(match.group(2))
        state = adjust_my_debt_installments(name, installments, persist=persist)
        item = find_my_debt_summary(name, state)
        return f"Parcelas ajustadas em {item['name']}.\nAgora sao {item['installments']}x de {money(item['installmentValue'])}"

    match = re.match(
        r"^(?:pagar|paguei|quitar|quitei)\s+(?:(\d+)\s+)?parcelas?\s+(?:da|de)\s+(?:divida|debito)\s+(.+?)(?:\s+(?:na|no)\s+(.+))?$",
        normalized_amounts,
    )
    if match:
        count = parse_count(match.group(1), "quantidade de parcelas") if match.group(1) else 1
        name = titleize_words(match.group(2))
        account_alias = normalize_text(match.group(3) or "conta")
        state = pay_my_debt_installments(name, count=count, account_alias=account_alias, persist=persist)
        item = find_my_debt_summary(name, state)
        account_key = resolve_balance_key(account_alias, state)
        return (
            f"Pagamento registrado para {item['name']} em {state['balances'][account_key]['label']}.\n"
            f"Parcelas pagas: {item['installmentsPaid']}/{item['installments']} | Restante: {money(item['remainingValue'])}"
        )

    match = re.match(r"^(?:pagar|paguei|quitar|quitei)\s+(?:uma\s+)?parcela\s+(?:da|de)\s+(?:divida|debito)\s+(.+?)(?:\s+(?:na|no)\s+(.+))?$", normalized_amounts)
    if match:
        name = titleize_words(match.group(1))
        account_alias = normalize_text(match.group(2) or "conta")
        state = pay_my_debt_installments(name, count=1, account_alias=account_alias, persist=persist)
        item = find_my_debt_summary(name, state)
        account_key = resolve_balance_key(account_alias, state)
        return (
            f"Pagamento registrado para {item['name']} em {state['balances'][account_key]['label']}.\n"
            f"Parcelas pagas: {item['installmentsPaid']}/{item['installments']} | Restante: {money(item['remainingValue'])}"
        )

    match = re.match(r"^(?:remover|apagar|deletar)\s+(?:a\s+)?(?:divida|debito)\s+(.+)$", normalized_amounts)
    if match:
        name = titleize_words(match.group(1))
        item = find_my_debt_summary(name)
        remove_my_debt(name, persist=persist)
        return f"Divida removida: {item['name']}."

    return None


def try_parse_structured_balance_phrase(text, persist=True):
    normalized = fold_text_keep_amounts(text)
    state = read_state()
    aliases = sorted(
        {alias for alias in balance_alias_map(state).keys() if alias and alias not in GENERIC_ACCOUNT_ALIASES},
        key=len,
        reverse=True,
    )

    for alias in aliases:
        variants = [
            ("action-first", re.match(rf"^(entrada|saida)\s+{re.escape(alias)}\s+{VALUE_RE}(?:\s+(.+))?$", normalized)),
            ("alias-first", re.match(rf"^{re.escape(alias)}\s+(entrada|saida)\s+{VALUE_RE}(?:\s+(.+))?$", normalized)),
            ("amount-first-action", re.match(rf"^{VALUE_RE}\s+(entrada|saida)\s+{re.escape(alias)}(?:\s+(.+))?$", normalized)),
            ("amount-first-alias", re.match(rf"^{VALUE_RE}\s+{re.escape(alias)}\s+(entrada|saida)(?:\s+(.+))?$", normalized)),
        ]
        for variant, match in variants:
            if not match:
                continue
            if variant in {"action-first", "alias-first"}:
                action_word = match.group(1)
                amount = parse_amount(match.group(2))
                note_text = match.group(3) or ""
            else:
                amount = parse_amount(match.group(1))
                action_word = match.group(2)
                note_text = match.group(3) or ""
            direction = "in" if action_word == "entrada" else "out"
            note = normalize_desc(note_text, "Entrada" if direction == "in" else "Saida")
            updated_state = add_balance_transaction(alias, direction, amount, note, persist=persist)
            key = resolve_balance_key(alias, updated_state)
            action = "Entrada" if direction == "in" else "Saida"
            return f"{action} registrada em {updated_state['balances'][key]['label']}.\nSaldo atual: {money(updated_state['balances'][key]['amount'])}"

    return None


def try_parse_read_query(text):
    normalized = fold_text(text)
    if not normalized:
        return None
    if looks_like_write_intent(text):
        return None

    if normalized in HELP_WORDS or has_phrase(normalized, {"como usa", "como funciona", "quais comandos", "me ajuda"}):
        return help_text()

    if normalized in GREETING_WORDS or any(normalized.startswith(greeting + " ") for greeting in GREETING_WORDS):
        return "\n".join(["Bot weedverso online.", format_saldos(), "Se quiser ver tudo que ele faz, use /help."])

    if normalized in {"saldo", "saldos", "status", "visao financeira", "visao do dia", "panorama", "resumo financeiro"}:
        return format_saldos()
    if normalized in {"extrato", "movimentacoes", "ultimas movimentacoes", "ultimos lancamentos", "ultimas compras", "ultimos gastos"}:
        return format_extrato()
    if normalized in {"objetivo", "objetivos", "meta", "metas", "meus objetivos", "minhas metas"}:
        return format_goals()
    if normalized in DEBTOR_WORDS:
        return format_debtors()
    if normalized in MY_DEBT_WORDS:
        return format_my_debts()
    if normalized in {"link", "link weedverso", "abrir weedverso", "painel weedverso", "painel"}:
        return format_share_link()
    if is_query_like(normalized) and text_tokens(normalized) & EXTRATO_WORDS:
        return format_extrato()
    if is_query_like(normalized) and text_tokens(normalized) & {"objetivo", "objetivos", "meta", "metas"}:
        try:
            return format_query_goal(text)
        except Exception:
            return format_goals()
    if is_query_like(normalized) and (text_tokens(normalized) & {"devedor", "devedores"} or has_phrase(normalized, {"quem me deve", "o que tenho a receber"})):
        return format_debtors()
    if is_query_like(normalized) and (
        has_phrase(normalized, {"minhas dividas", "meus debitos", "contas a pagar", "o que eu devo"})
        or ("dividas" in text_tokens(normalized) and {"minha", "minhas", "meu", "meus", "eu"} & text_tokens(normalized))
    ):
        return format_my_debts()
    if is_query_like(normalized) and has_phrase(normalized, {"link do weedverso", "me manda o link", "qual o link", "abre o painel"}):
        return format_share_link()

    if is_query_like(normalized) and (text_tokens(normalized) & GENERAL_BALANCE_WORDS):
        return format_saldos()
    if is_query_like(normalized) and {"saldo", "saldos"} & text_tokens(normalized) and not detect_account_alias(normalized):
        return format_saldos()

    if has_phrase(normalized, {"me mostra os saldos", "me mostra meu saldo", "quero ver meus saldos", "quero ver meu saldo"}):
        return format_saldos()

    if normalized in {"fatura", "cartao", "cartao de credito", "credito", "amex"}:
        return format_card_status()
    if normalized in {"reserva do cartao", "reserva cartao", "reservado cartao"}:
        summary = balance_summary(read_state())
        return f"Saldo reservado cartao: {money(summary['card_reserved'])}\nFalta cobrir: {money(summary['card_uncovered'])}"
    if is_simple_account_balance_lookup(normalized):
        return format_account_balance(detect_account_alias(normalized))

    if ("reserva" in normalized and ("cartao" in normalized or "amex" in normalized)) and (
        is_query_like(normalized) or has_phrase(normalized, {"quanto tem reservado", "quanto esta reservado", "quanto ficou reservado"})
    ):
        summary = balance_summary(read_state())
        return f"Saldo reservado cartao: {money(summary['card_reserved'])}\nFalta cobrir: {money(summary['card_uncovered'])}"

    if ("cartao" in normalized or "fatura" in normalized or "amex" in normalized or "credito" in normalized) and (
        is_query_like(normalized)
        or has_phrase(normalized, {"quanto devo", "quanto gastei", "quanto falta", "como ta a fatura", "como esta a fatura"})
    ):
        return format_card_status()

    alias = detect_account_alias(normalized)
    if alias and (
        is_query_like(normalized)
        or has_phrase(normalized, {"saldo do", "saldo da", "quanto tem no", "quanto tem na", "quanto sobrou no", "quanto sobrou na"})
    ):
        return format_account_balance(alias)

    return None


def try_parse_natural_finance(text, persist=True):
    normalized = fold_text(text)
    tokens = text_tokens(normalized)
    normalized_amounts = fold_text_keep_amounts(text)
    amount = extract_amount(text)
    reserve_in_hints = RESERVE_IN_WORDS | {"entrada", "deposito", "depositar", "adicionar", "acrescentar", "somar"}
    reserve_out_hints = RESERVE_OUT_WORDS | {"saida", "retirada", "retirar", "tirar", "abater", "descontar"}

    read_reply = try_parse_read_query(text)
    if read_reply:
        return read_reply

    delete_reply = try_parse_natural_transaction_delete(text, persist=persist)
    if delete_reply:
        return delete_reply

    debtor_reply = try_parse_natural_debtor_flow(text, persist=persist)
    if debtor_reply:
        return debtor_reply

    my_debt_reply = try_parse_natural_my_debt_flow(text, persist=persist)
    if my_debt_reply:
        return my_debt_reply

    structured_balance_reply = try_parse_structured_balance_phrase(text, persist=persist)
    if structured_balance_reply:
        return structured_balance_reply

    if amount and "reserva" in normalized and ("cartao" in normalized or "amex" in normalized):
        if tokens & reserve_in_hints:
            state = add_credit_transaction("reserve-in", amount, "Reserva cartao", persist=persist)
            return f"Reserva do cartao reforcada.\nSaldo reservado: {money(state['credit']['reserved'])}"
        if tokens & reserve_out_hints:
            state = add_credit_transaction("reserve-out", amount, "Reserva cartao", persist=persist)
            return f"Saida da reserva registrada.\nSaldo reservado: {money(state['credit']['reserved'])}"

    match = re.match(rf"^(?:reservei|guardei|separei|coloquei|adicionei|reforcei|abasteci)\s+{VALUE_RE}\s+(?:pro|para o|para|na|na reserva do)\s+cartao$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        state = add_credit_transaction("reserve-in", value, "Reserva cartao", persist=persist)
        return f"Reserva do cartao reforcada.\nSaldo reservado: {money(state['credit']['reserved'])}"

    match = re.match(rf"^(?:tirei|retirei|usei|saquei|consumi)\s+{VALUE_RE}\s+(?:da|do|de)\s+reserva(?: do)?\s+cartao$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        state = add_credit_transaction("reserve-out", value, "Reserva cartao", persist=persist)
        return f"Saida da reserva registrada.\nSaldo reservado: {money(state['credit']['reserved'])}"

    if amount and ("cartao" in normalized or "fatura" in normalized or "amex" in normalized):
        if tokens & CARD_PAYMENT_WORDS:
            desc = card_note_from_text(text, "Pagamento cartao")
            state = add_credit_transaction("payment", amount, desc, persist=persist)
            return f"Pagamento registrado no cartao.\nFatura atual: {money(state['credit']['used'])}"
        if tokens & (CARD_EXPENSE_WORDS | {"compra", "compras", "lancamento", "gasto"}):
            desc = card_note_from_text(text, "Gasto rapido")
            state = add_credit_transaction("expense", amount, desc, persist=persist)
            return f"Gasto registrado no cartao.\nCategoria: {desc}\nFatura atual: {money(state['credit']['used'])}"
        desc = card_note_from_text(text, "Gasto rapido")
        state = add_credit_transaction("expense", amount, desc, persist=persist)
        return f"Gasto registrado no cartao.\nCategoria: {desc}\nFatura atual: {money(state['credit']['used'])}"

    if amount:
        account_alias = detect_account_alias(normalized)
        account_context = bool(account_alias or tokens & ACCOUNT_CONTEXT_WORDS or has_phrase(normalized, {"conta corrente", "saldo em conta", "por pix", "via pix", "no debito", "no débito"}))
        account_key = None

        if (tokens & BALANCE_IN_WORDS) or has_phrase(normalized, {"entrou", "caiu", "pingou", "ganhei", "recebi"}):
            account_alias = account_alias or "conta"
            note = account_note_from_text(text, account_alias, "Entrada")
            state = add_balance_transaction(account_alias, "in", amount, note, persist=persist)
            key = resolve_balance_key(account_alias, state)
            return f"Entrada registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

        if (tokens & BALANCE_OUT_WORDS or has_phrase(normalized, {"mandei por pix", "enviei por pix", "transferi", "saquei", "paguei no debito", "paguei no débito"})) and account_context:
            account_alias = account_alias or "conta"
            note = account_note_from_text(text, account_alias, "Saida")
            state = add_balance_transaction(account_alias, "out", amount, note, persist=persist)
            key = resolve_balance_key(account_alias, state)
            return f"Saida registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

        if has_phrase(normalized, {"entrada de", "deposito de", "depósito de"}) and not account_alias:
            note = account_note_from_text(text, "conta", "Entrada")
            state = add_balance_transaction("conta", "in", amount, note, persist=persist)
            return f"Entrada registrada em {state['balances']['conta']['label']}.\nSaldo atual: {money(state['balances']['conta']['amount'])}"

        if has_phrase(normalized, {"saida de", "saída de", "despesa de"}) and account_context:
            account_alias = account_alias or "conta"
            note = account_note_from_text(text, account_alias, "Saida")
            state = add_balance_transaction(account_alias, "out", amount, note, persist=persist)
            key = resolve_balance_key(account_alias, state)
            return f"Saida registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

        if tokens & CARD_EXPENSE_WORDS or has_phrase(normalized, {"fiz um gasto", "fiz gasto", "lancei", "passei", "compra de", "gasto de"}):
            if account_alias:
                note = account_note_from_text(text, account_alias, "Saida")
                state = add_balance_transaction(account_alias, "out", amount, note, persist=persist)
                key = resolve_balance_key(account_alias, state)
                return f"Saida registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"
            desc = card_note_from_text(text, "Gasto rapido")
            state = add_credit_transaction("expense", amount, desc, persist=persist)
            return f"Gasto registrado no cartao.\nCategoria: {desc}\nFatura atual: {money(state['credit']['used'])}"

        if account_alias and has_phrase(normalized, {"coloquei", "adicionei", "acrescentei", "credita", "soma"}):
            note = account_note_from_text(text, account_alias, "Entrada")
            state = add_balance_transaction(account_alias, "in", amount, note, persist=persist)
            key = resolve_balance_key(account_alias, state)
            return f"Entrada registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

        if account_alias and has_phrase(normalized, {"retira", "retirei", "tira", "saquei", "desconta", "debita"}):
            note = account_note_from_text(text, account_alias, "Saida")
            state = add_balance_transaction(account_alias, "out", amount, note, persist=persist)
            key = resolve_balance_key(account_alias, state)
            return f"Saida registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

        generic_goal_context = "objetivo" in normalized or "meta" in normalized
        generic_card_context = "cartao" in normalized or "fatura" in normalized or "amex" in normalized or "credito" in normalized
        if not generic_goal_context and not generic_card_context and "reserva" not in normalized:
            if "entrada" in tokens:
                account_alias = account_alias or "conta"
                note = account_note_from_text(text, account_alias, "Entrada")
                state = add_balance_transaction(account_alias, "in", amount, note, persist=persist)
                key = resolve_balance_key(account_alias, state)
                return f"Entrada registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

            if "saida" in tokens:
                account_alias = account_alias or "conta"
                note = account_note_from_text(text, account_alias, "Saida")
                state = add_balance_transaction(account_alias, "out", amount, note, persist=persist)
                key = resolve_balance_key(account_alias, state)
                return f"Saida registrada em {state['balances'][key]['label']}.\nSaldo atual: {money(state['balances'][key]['amount'])}"

    return None


def maybe_decorate_test_reply(reply):
    if telegram_test_mode_enabled():
        return decorate_test_reply(reply)
    return reply


def _route_message_impl(message):
    chat_id = message["chat"]["id"]
    text = normalize_text(message.get("text") or "")
    if not text:
        return chat_id, "Envie um comando. Use /help para ver os exemplos."

    persist_changes = True

    if not text.startswith("/"):
        goal_reply = try_parse_natural_goal(text, persist=persist_changes)
        if goal_reply:
            return chat_id, maybe_decorate_test_reply(goal_reply)
        finance_reply = try_parse_natural_finance(text, persist=persist_changes)
        if finance_reply:
            return chat_id, maybe_decorate_test_reply(finance_reply)
        return chat_id, "Desculpe meu senhor, programe melhor."

    parts = text.split()
    command = parts[0].split("@")[0].lower()
    args = parts[1:]

    if command in {"/modoteste", "/modo_teste", "/testemode"}:
        return chat_id, handle_test_mode_command(args)
    if command in {"/start", "/help", "/ajuda"}:
        return chat_id, maybe_decorate_test_reply(help_text())
    if command in {"/saldos", "/saldo", "/status"}:
        return chat_id, maybe_decorate_test_reply(format_saldos())
    if command == "/entrada":
        return chat_id, maybe_decorate_test_reply(handle_balance_command("entrada", args, persist=persist_changes))
    if command == "/saida":
        return chat_id, maybe_decorate_test_reply(handle_balance_command("saida", args, persist=persist_changes))
    if command == "/cartao":
        return chat_id, maybe_decorate_test_reply(handle_cartao_command("gasto", args, persist=persist_changes))
    if command == "/pagarcartao":
        return chat_id, maybe_decorate_test_reply(handle_cartao_command("pagamento", args, persist=persist_changes))
    if command == "/reservacartao":
        return chat_id, maybe_decorate_test_reply(handle_reserva_command(args, persist=persist_changes))
    if command in {"/objetivos", "/metas"}:
        return chat_id, maybe_decorate_test_reply(format_goals())
    if command in {"/devedores", "/receber"}:
        return chat_id, maybe_decorate_test_reply(format_debtors())
    if command in {"/dividas", "/minhasdividas", "/debitos"}:
        return chat_id, maybe_decorate_test_reply(format_my_debts())
    if command in {"/devedor", "/devedorcfg"}:
        return chat_id, maybe_decorate_test_reply(handle_debtor_command(args, persist=persist_changes))
    if command in {"/divida", "/debitocfg"}:
        return chat_id, maybe_decorate_test_reply(handle_my_debt_command(args, persist=persist_changes))
    if command == "/objetivo":
        return chat_id, maybe_decorate_test_reply(handle_goal_command(args, persist=persist_changes))
    if command in {"/extrato", "/extratos"}:
        return chat_id, maybe_decorate_test_reply(format_extrato())
    if command in {"/apagartransacao", "/apagartx"}:
        return chat_id, maybe_decorate_test_reply(handle_delete_transaction_command(args, persist=persist_changes))
    if command in {"/apagarultima", "/ultimatransacao", "/desfazerultima"}:
        return chat_id, maybe_decorate_test_reply(handle_delete_last_transaction_command(persist=persist_changes))
    if command in {"/link", "/painel", "/weedverso"}:
        return chat_id, maybe_decorate_test_reply(format_share_link())
    if command in {"/meuid", "/chatid", "/conexao"}:
        return chat_id, maybe_decorate_test_reply(format_connection(chat_id))
    if command in {"/teste", "/testetelegram"}:
        return chat_id, maybe_decorate_test_reply(send_test_snapshot(chat_id))

    return chat_id, "Comando nao reconhecido. Use /help."


def route_message(message):
    chat_id = message["chat"]["id"]
    text = normalize_text(message.get("text") or "")
    if not text:
        return chat_id, "Envie um comando. Use /help para ver os exemplos."

    if text.startswith("/"):
        command = text.split()[0].split("@")[0].lower()
        if command in {"/modoteste", "/modo_teste", "/testemode"}:
            return _route_message_impl(message)

    before_snapshot = ""
    should_trigger_sync = not telegram_test_mode_enabled()
    if should_trigger_sync:
        before_snapshot = current_state_snapshot()

    if telegram_test_mode_enabled():
        seed_state = read_state()
        with using_state_file(telegram_test_state_file(chat_id), seed_state=seed_state):
            return _route_message_impl(message)

    result = _route_message_impl(message)
    if should_trigger_sync:
        after_snapshot = current_state_snapshot()
        if after_snapshot and after_snapshot != before_snapshot:
            try:
                trigger_background_push("telegram")
            except Exception:
                pass
    return result


def run_bot():
    if not TOKEN:
        raise RuntimeError("Defina TELEGRAM_BOT_TOKEN antes de iniciar o bot.")

    print("Bot do Telegram iniciado.")
    if AUTO_DELETE_SECONDS > 0:
        user_cleanup = "ativada" if DELETE_USER_MESSAGES else "desativada"
        print(f"Auto limpeza do Telegram: {AUTO_DELETE_SECONDS}s | apagar mensagens do usuario: {user_cleanup}")
    offset = None
    while True:
        try:
            result = call_telegram(
                "getUpdates",
                {
                    "timeout": 25,
                    "offset": offset or "",
                    "allowed_updates": json.dumps(["message"]),
                },
            )
            for update in result:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                if not chat_id:
                    continue
                if not is_allowed(chat_id):
                    send_message(chat_id, "Este chat nao esta autorizado para o bot weedverso.")
                    schedule_user_message_cleanup(chat_id, message.get("message_id"))
                    continue
                register_chat(chat)
                try:
                    target_chat_id, reply = route_message(message)
                except Exception as exc:
                    print(f"Falha ao processar mensagem do chat {chat_id}: {exc}")
                    target_chat_id, reply = chat_id, "Nao consegui processar sua mensagem agora. Tente novamente."
                send_message(target_chat_id, reply)
                schedule_user_message_cleanup(chat_id, message.get("message_id"))
        except Exception as exc:
            print(f"Falha no polling do Telegram: {exc}")
            time.sleep(4)


if __name__ == "__main__":
    run_bot()
