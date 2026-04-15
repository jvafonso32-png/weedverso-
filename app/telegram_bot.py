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
    add_balance_transaction,
    add_credit_transaction,
    add_goal,
    balance_alias_map,
    balance_summary,
    combined_history,
    debtors_summary,
    fold_text,
    goals_summary,
    money,
    move_goal,
    my_debts_summary,
    read_state,
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
CARD_PAYMENT_WORDS = {"paguei", "abati", "abater", "amortizei", "amortizar", "quitei", "quitar", "antecipei"}
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
    result = call_telegram("sendMessage", {"chat_id": chat_id, "text": text})
    schedule_delete_message(chat_id, (result or {}).get("message_id"))
    return result


def delete_message(chat_id, message_id):
    return call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


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
    return "\n".join(
        [
            f"{summary['card_name']}: {money(summary['card_used'])}",
            f"Saldo reservado: {money(summary['card_reserved'])}",
            f"Falta cobrir: {money(summary['card_uncovered'])}",
            f"Cobertura da fatura: {summary['card_coverage']}%",
        ]
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


def help_text():
    return "\n".join(
        [
            "Comandos do bot weedverso:",
            "/saldos",
            "/saldo",
            "/entrada conta 150 salario",
            "/saida mercado 42,50 compras",
            "/cartao 89,90 uber",
            "/pagarcartao 300 pagamento parcial",
            "/reservacartao entrada 200",
            "/reservacartao saida 50",
            "/objetivos",
            "/objetivo criar Viagem Dubai | 12000",
            "/objetivo depositar Viagem Dubai | 400",
            "/objetivo retirar Viagem Dubai | 100",
            "/objetivo rendimento Viagem Dubai | 35",
            "/extrato",
            "/meuid",
            "/modoteste on",
            "/modoteste off",
            "/modoteste status",
            "",
            "Frases naturais que funcionam:",
            "conta entrada 150 salario",
            "conta saida 40 uber",
            "mercado entrada 100 recarga",
            "refeicao saida 35 almoco",
            "gastei 38 no uber",
            "passei 62 no cartao no ifood",
            "lancei 35 de farmacia no cartao",
            "paguei a fatura do cartao 300",
            "recebi 1200 na conta salario",
            "caiu 850 salario",
            "pingou 90 cashback",
            "depositei 200 no vale alimentacao mercado",
            "coloquei 50 no vr almoco",
            "retirei 45 da conta uber",
            "mandei 120 por pix do aluguel",
            "reservei 300 pro cartao",
            "tirei 50 da reserva do cartao",
            "quanto tenho na conta",
            "qual meu saldo no vr",
            "me mostra meus saldos",
            "como esta a fatura do cartao",
            "quanto tenho reservado no cartao",
            "quanto falta pra cobrir a fatura",
            "criar objetivo notebook | 5000",
            "depositei 200 no objetivo notebook",
            "rendeu 30 no objetivo notebook",
            "devedores",
            "minhas dividas",
            "link weedverso",
            "",
            "Durante o modo teste, tudo acima vira simulacao e nada e salvo.",
            "",
            "Categorias agora sao agrupadas sem diferenca entre maiusculas, minusculas e acentos.",
            f"Limpeza automatica do chat: respostas do bot sao apagadas apos {AUTO_DELETE_SECONDS} segundos.",
        ]
    )


def format_saldos():
    state = read_state()
    summary = balance_summary(state)
    return "\n".join(
        [
            "weedverso | visao financeira",
            f"{state['balances']['conta']['label']}: {money(summary['conta'])}",
            f"{state['balances']['vale1']['label']}: {money(summary['vale1'])}",
            f"{state['balances']['vale2']['label']}: {money(summary['vale2'])}",
            f"{summary['card_name']}: {money(summary['card_used'])}",
            f"Saldo reservado cartao: {money(summary['card_reserved'])}",
            f"Falta cobrir: {money(summary['card_uncovered'])}",
            f"Cobertura da fatura: {summary['card_coverage']}%",
        ]
    )


def format_extrato():
    items = combined_history(limit=12)
    if not items:
        return "Sem movimentacoes recentes."
    lines = ["Ultimas movimentacoes:"]
    for item in items:
        note = f" | {item['note']}" if item.get("note") else ""
        lines.append(f"{item['sign']} {money(item['value'])} | {item['text']}{note}")
    return "\n".join(lines)


def format_goals():
    items = goals_summary()
    if not items:
        return "Nenhum objetivo cadastrado."
    lines = ["Objetivos ativos:"]
    for item in items[:8]:
        lines.append(
            f"{item['name']} | {money(item['saved'])} de {money(item['target'])} | {item['pct']}% | faltam {money(item['left'])}"
        )
    return "\n".join(lines)


def format_debtors():
    items = debtors_summary()
    if not items:
        return "Nenhum devedor cadastrado."
    open_items = [item for item in items if not item.get("paid")]
    if not open_items:
        return "Nenhum devedor em aberto."
    total_open = sum(float(item.get("amount") or 0) for item in open_items)
    lines = [f"Devedores | em aberto: {len(open_items)} | total a receber: {money(total_open)}"]
    for item in open_items[:8]:
        parts = [f"{item['name']}: {money(item['amount'])}"]
        if item.get("payDate"):
            parts.append(f"vence {format_short_date(item['payDate'])}")
        if item.get("note"):
            parts.append(item["note"])
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def format_my_debts():
    items = my_debts_summary()
    if not items:
        return "Nenhuma divida propria cadastrada."
    open_items = [item for item in items if not item.get("paid")]
    if not open_items:
        return "Nenhuma divida em aberto."
    total_open = sum(float(item.get("remainingValue") or 0) for item in open_items)
    lines = [f"Minhas dividas | em aberto: {len(open_items)} | total restante: {money(total_open)}"]
    for item in open_items[:8]:
        parts = [
            f"{item['name']}: {money(item['remainingValue'])}",
            f"{item['installmentsPaid']}/{item['installments']} parcelas",
            f"parcela {money(item['installmentValue'])}",
        ]
        if item.get("payDate"):
            parts.append(f"vence {format_short_date(item['payDate'])}")
        if item.get("note"):
            parts.append(item["note"])
        lines.append(" | ".join(parts))
    return "\n".join(lines)


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
    if action in {"depositar", "deposito", "aportar", "guardar"}:
        name, value = split_pipe_payload(payload)
        state = move_goal(name, "deposit", value, persist=persist)
        goal = find_goal_summary(name, state)
        return f"Deposito registrado em {goal['name']}.\nGuardado: {money(goal['saved'])}"
    if action in {"retirar", "saque", "tirar"}:
        name, value = split_pipe_payload(payload)
        state = move_goal(name, "withdraw", value, persist=persist)
        goal = find_goal_summary(name, state)
        return f"Retirada registrada em {goal['name']}.\nGuardado: {money(goal['saved'])}"
    if action in {"rendimento", "render", "lucro"}:
        name, value = split_pipe_payload(payload)
        state = move_goal(name, "yield", value, persist=persist)
        goal = find_goal_summary(name, state)
        return f"Rendimento registrado em {goal['name']}.\nGuardado: {money(goal['saved'])}"

    raise ValueError("Use /objetivo criar|depositar|retirar|rendimento Nome | valor")


def format_query_goal(text):
    goal_name = normalize_text(re.sub(r"^(?:como esta|quanto tem|quanto tenho|mostrar|mostra|ver|status do|status da)\s+", "", text, flags=re.IGNORECASE))
    goal_name = re.sub(r"^(?:objetivo|meta)\s+", "", goal_name, flags=re.IGNORECASE).strip()
    if not goal_name:
        return format_goals()
    goal = find_goal_summary(goal_name)
    return f"{goal['name']} | {money(goal['saved'])} de {money(goal['target'])} | {goal['pct']}% | faltam {money(goal['left'])}"


def try_parse_natural_goal(text, persist=True):
    raw_text = normalize_text(text)
    normalized = fold_text(text)
    normalized_amounts = fold_text_keep_amounts(text)

    match = re.match(rf"^(?:criar|crie|adicionar|adicione|novo|nova)(?:\s+(?:objetivo|meta))?\s+(.+?)\s*\|\s*{VALUE_RE}$", raw_text, flags=re.IGNORECASE)
    if match:
        name = titleize_words(match.group(1))
        value = parse_amount(match.group(2))
        add_goal(name, value, persist=persist)
        return f"Objetivo criado: {name}.\nMeta inicial: {money(value)}"

    match = re.match(rf"^(?:depositei|deposita|deposita|guardei|coloquei|apliquei|aportei)\s+{VALUE_RE}\s+(?:no|na|em)\s+(?:objetivo|meta)\s+(.+)$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        state = move_goal(goal_name, "deposit", value, persist=persist)
        goal = find_goal_summary(goal_name, state)
        return f"Deposito registrado em {goal['name']}.\nGuardado: {money(goal['saved'])}"

    match = re.match(rf"^(?:retirei|tirei|saquei)\s+{VALUE_RE}\s+(?:do|da|de)\s+(?:objetivo|meta)\s+(.+)$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        state = move_goal(goal_name, "withdraw", value, persist=persist)
        goal = find_goal_summary(goal_name, state)
        return f"Retirada registrada em {goal['name']}.\nGuardado: {money(goal['saved'])}"

    match = re.match(rf"^(?:rendeu|teve rendimento de|rendimento de|lucrou)\s+{VALUE_RE}\s+(?:no|na|em)\s+(?:objetivo|meta)\s+(.+)$", normalized_amounts)
    if match:
        value = parse_amount(match.group(1))
        goal_name = titleize_words(match.group(2))
        state = move_goal(goal_name, "yield", value, persist=persist)
        goal = find_goal_summary(goal_name, state)
        return f"Rendimento registrado em {goal['name']}.\nGuardado: {money(goal['saved'])}"

    if ("objetivo" in normalized or "meta" in normalized) and any(word in normalized.split() for word in QUERY_WORDS):
        return format_query_goal(text)

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
        patterns = [
            rf"^(entrada|saida)\s+{re.escape(alias)}\s+{VALUE_RE}(?:\s+(.+))?$",
            rf"^{re.escape(alias)}\s+(entrada|saida)\s+{VALUE_RE}(?:\s+(.+))?$",
        ]
        for pattern in patterns:
            match = re.match(pattern, normalized)
            if not match:
                continue
            direction = "in" if match.group(1) == "entrada" else "out"
            amount = parse_amount(match.group(2))
            note = normalize_desc(match.group(3) or "", "Entrada" if direction == "in" else "Saida")
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
    if normalized in {"objetivos", "metas", "meus objetivos", "minhas metas"}:
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

    read_reply = try_parse_read_query(text)
    if read_reply:
        return read_reply

    structured_balance_reply = try_parse_structured_balance_phrase(text, persist=persist)
    if structured_balance_reply:
        return structured_balance_reply

    if amount and "reserva" in normalized and ("cartao" in normalized or "amex" in normalized):
        if tokens & RESERVE_IN_WORDS:
            state = add_credit_transaction("reserve-in", amount, "Reserva cartao", persist=persist)
            return f"Reserva do cartao reforcada.\nSaldo reservado: {money(state['credit']['reserved'])}"
        if tokens & RESERVE_OUT_WORDS:
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
    if command == "/objetivo":
        return chat_id, maybe_decorate_test_reply(handle_goal_command(args, persist=persist_changes))
    if command in {"/extrato", "/extratos"}:
        return chat_id, maybe_decorate_test_reply(format_extrato())
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

    if telegram_test_mode_enabled():
        seed_state = read_state()
        with using_state_file(telegram_test_state_file(chat_id), seed_state=seed_state):
            return _route_message_impl(message)

    return _route_message_impl(message)


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
