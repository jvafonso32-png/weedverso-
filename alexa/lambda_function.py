# -*- coding: utf-8 -*-
"""
Weedverso - Alexa Voice Skill (AWS Lambda / Alexa-Hosted Python)
Permite consultar saldos e registrar entradas e saídas por voz via Alexa,
sincronizando 100% em tempo real com o GitHub Gist do Weedverso.
"""

import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Alexa Skills Kit SDK (com suporte a fallback local para testes sem instalacao previa)
try:
    from ask_sdk_core.skill_builder import SkillBuilder
    from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
    from ask_sdk_core.utils import is_request_type, is_intent_name
    from ask_sdk_core.handler_input import HandlerInput
    from ask_sdk_model import Response
except ImportError:
    class AbstractRequestHandler:
        pass
    class AbstractExceptionHandler:
        pass
    def is_request_type(name):
        return lambda x: False
    def is_intent_name(name):
        return lambda x: False
    class SkillBuilder:
        def add_request_handler(self, handler): pass
        def add_exception_handler(self, handler): pass
        def lambda_handler(self): return lambda event, context: None
    HandlerInput = object
    Response = object

# Configuracoes de Sincronizacao (Configuradas nas Variaveis de Ambiente da Skill)
EXPECTED_SKILL_ID = os.getenv("ALEXA_SKILL_ID", "").strip()

def get_env_config():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_SYNC_TOKEN") or ""
    gist_id = os.getenv("GITHUB_GIST_ID", "")
    return token.strip(), gist_id.strip()

# ==============================================================================
# Funcoes Auxiliares de Formatacao e Deteccao
# ==============================================================================

def make_id():
    """Gera um ID único alfanumérico no padrão do Weedverso."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return now[-14:]

def format_spoken_currency(value):
    """Converte valor monetário para texto fonético natural para a Alexa."""
    val = float(value or 0.0)
    is_neg = val < 0
    val = abs(val)
    reais = int(val)
    centavos = int(round((val - reais) * 100))

    if reais == 0 and centavos == 0:
        return "zero reais"

    parts = []
    if reais > 0:
        if reais == 1:
            parts.append("1 real")
        else:
            parts.append(f"{reais} reais")

    if centavos > 0:
        if centavos == 1:
            parts.append("1 centavo")
        else:
            parts.append(f"{centavos} centavos")

    spoken = " e ".join(parts) if parts else "zero reais"
    return f"menos {spoken}" if is_neg else spoken

def parse_spoken_amount(raw_val):
    """Extrai o valor numérico com tolerância máxima a variações de fala da Alexa."""
    if not raw_val:
        return 0.0
    text = str(raw_val).lower().replace("r$", "").replace("reais", "").replace("real", "").strip()
    # Troca vírgula decimal por ponto
    text = text.replace(",", ".")
    try:
        return abs(float(text))
    except (ValueError, TypeError):
        pass
    # Tenta extrair números por regex caso venha com texto adicional
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        try:
            return abs(float(match.group(1)))
        except (ValueError, TypeError):
            pass
    return 0.0

def calculate_amount(raw_val, raw_cents=""):
    """Calcula o valor total somando reais e centavos (ex: 29 reais e 24 centavos = 29.24)."""
    base = parse_spoken_amount(raw_val)
    cents = parse_spoken_amount(raw_cents)
    if round(base, 2) != int(base):
        return round(base, 2)
    if cents > 0:
        return round(base + (cents / 100.0), 2)
    return round(base, 2)

def normalize_wallet_key(raw_slot, description=""):
    """
    Identifica a carteira de destino:
    'conta' (Conta Principal), 'vale1' (Alimentacao/Mercado), 'vale2' (Refeicao/VR).
    Se o usuario nao disse a carteira, analisa a descricao (ex: 'almoco' -> refeicao).
    """
    text = (raw_slot or "").lower().strip()
    desc = (description or "").lower().strip()

    # Mapeamento explicito
    if any(k in text for k in ["refeicao", "refeição", "vr", "vale 2", "vale2", "almoco", "almoço", "jantar", "restaurante", "lanche"]):
        return "vale2", "Vale Refeição"
    if any(k in text for k in ["alimentacao", "alimentação", "va", "mercado", "supermercado", "vale 1", "vale1"]):
        return "vale1", "Vale Alimentação"
    if any(k in text for k in ["conta", "corrente", "principal", "banco", "nubank", "inter", "itau"]):
        return "conta", "Conta Principal"

    # Inferencia inteligente pelo contexto da descricao
    if any(k in desc for k in ["almoco", "almoço", "jantar", "refeicao", "refeição", "restaurante", "mcdonalds", "burger", "lanche", "ifood", "cafe", "café"]):
        return "vale2", "Vale Refeição"
    if any(k in desc for k in ["mercado", "supermercado", "feira", "acougue", "açougue", "hortifruti", "sacolao", "padaria"]):
        return "vale1", "Vale Alimentação"

    # Padrao geral: Conta Principal
    return "conta", "Conta Principal"

def get_slot_value(handler_input, slot_name):
    """Extrai com seguranca o valor de um slot da solicitacao da Alexa."""
    try:
        slots = handler_input.request_envelope.request.intent.slots
        if slot_name in slots and slots[slot_name].value:
            return slots[slot_name].value.strip()
    except Exception:
        pass
    return ""

# ==============================================================================
# Comunicacao com o GitHub Gist (Banco de Dados em Nuvem)
# ==============================================================================

def pull_state_from_gist():
    token, gist_id = get_env_config()
    if not token or not gist_id:
        return None, "Token ou Gist ID não configurados."

    url = f"https://api.github.com/gists/{gist_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "WeedversoAlexaSkill"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = data.get("files", {})
            file_entry = files.get("weedverso_state.json")
            if not file_entry or not file_entry.get("content"):
                return None, "Arquivo weedverso_state.json não encontrado no Gist."
            return json.loads(file_entry["content"]), "ok"
    except Exception as exc:
        return None, f"Erro ao acessar Gist: {exc}"

def push_state_to_gist(state):
    token, gist_id = get_env_config()
    if not token or not gist_id:
        return False, "Token ou Gist ID não configurados."

    # Atualiza timestamp
    state["lastUpdatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    url = f"https://api.github.com/gists/{gist_id}"
    payload = {
        "files": {
            "weedverso_state.json": {
                "content": json.dumps(state, indent=2, ensure_ascii=False)
            }
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "WeedversoAlexaSkill"
        },
        method="PATCH"
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, "ok"
    except Exception as exc:
        return False, f"Erro ao salvar no Gist: {exc}"

# ==============================================================================
# Handlers da Alexa Skill
# ==============================================================================

class LaunchRequestHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Alexa, abra o Weedverso'."""
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Olá! Bem-vindo ao Weedverso. "
            "Você pode me pedir para consultar seu saldo, "
            "registrar um gasto ou lançar uma entrada. O que deseja fazer?"
        )
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("Deseja consultar o saldo ou registrar uma movimentação?")
            .response
        )

class ConsultarSaldoIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Quanto eu tenho de saldo?', 'Qual meu saldo no vale refeição?'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarSaldoIntent")(handler_input)

    def handle(self, handler_input):
        raw_carteira = get_slot_value(handler_input, "carteira")

        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui conectar ao seu banco de dados na nuvem no momento."
            ).response

        balances = state.get("balances", {})
        c_conta = balances.get("conta", {}).get("amount", 0.0)
        c_vale1 = balances.get("vale1", {}).get("amount", 0.0)
        c_vale2 = balances.get("vale2", {}).get("amount", 0.0)

        if raw_carteira:
            key, name = normalize_wallet_key(raw_carteira)
            amount = balances.get(key, {}).get("amount", 0.0)
            speech = f"Seu saldo na {name} é de {format_spoken_currency(amount)}."
        else:
            speech = (
                f"Seu saldo na Conta Principal é de {format_spoken_currency(c_conta)}, "
                f"no Vale Alimentação é de {format_spoken_currency(c_vale1)}, "
                f"e no Vale Refeição é de {format_spoken_currency(c_vale2)}."
            )

        return handler_input.response_builder.speak(speech).response

class RegistrarGastoIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Gastei 35 reais no almoço', 'Lance 50 reais no mercado'."""
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarGastoIntent")(handler_input)

    def handle(self, handler_input):
        raw_val = get_slot_value(handler_input, "valor")
        raw_cents = get_slot_value(handler_input, "centavos")
        raw_carteira = get_slot_value(handler_input, "carteira")
        raw_desc = get_slot_value(handler_input, "categoria") or get_slot_value(handler_input, "descricao")

        amount = calculate_amount(raw_val, raw_cents)

        if amount <= 0:
            return (
                handler_input.response_builder
                .speak("Qual foi o valor do gasto?")
                .ask("Por favor, diga o valor que deseja registrar.")
                .response
            )

        wallet_key, wallet_name = normalize_wallet_key(raw_carteira, raw_desc)
        note = raw_desc.capitalize() if raw_desc else "Gasto via Alexa"

        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui acessar o Weedverso na nuvem para registrar o gasto."
            ).response

        balances = state.setdefault("balances", {})
        wallet = balances.setdefault(wallet_key, {"label": wallet_name, "amount": 0.0})
        prev_balance = float(wallet.get("amount", 0.0))
        new_balance = prev_balance - amount
        wallet["amount"] = round(new_balance, 2)

        # Adiciona no historico de transacoes
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        tx_entry = {
            "id": make_id(),
            "account": wallet_key,
            "type": "out",
            "value": round(amount, 2),
            "prev": round(prev_balance, 2),
            "note": note[:60],
            "debtorId": "",
            "myDebtId": "",
            "myDebtInstallment": 0,
            "at": now_iso,
            "category": note[:40],
            "categoryKey": note.lower()[:48]
        }
        state.setdefault("tx", []).insert(0, tx_entry)

        ok, push_err = push_state_to_gist(state)
        if not ok:
            return handler_input.response_builder.speak(
                "O gasto foi calculado, mas houve um erro ao sincronizar com o Gist."
            ).response

        speech = (
            f"Registrado! Saída de {format_spoken_currency(amount)} "
            f"em {note} na {wallet_name}. Seu novo saldo é de {format_spoken_currency(new_balance)}."
        )
        return handler_input.response_builder.speak(speech).response

class RegistrarEntradaIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Entraram 200 reais na conta', 'Recebi 150 reais'."""
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarEntradaIntent")(handler_input)

    def handle(self, handler_input):
        raw_val = get_slot_value(handler_input, "valor")
        raw_cents = get_slot_value(handler_input, "centavos")
        raw_carteira = get_slot_value(handler_input, "carteira")
        raw_desc = get_slot_value(handler_input, "origem") or get_slot_value(handler_input, "descricao")

        amount = calculate_amount(raw_val, raw_cents)

        if amount <= 0:
            return (
                handler_input.response_builder
                .speak("Qual o valor da entrada que você deseja registrar?")
                .ask("Por favor, diga o valor.")
                .response
            )

        wallet_key, wallet_name = normalize_wallet_key(raw_carteira, raw_desc)
        note = raw_desc.capitalize() if raw_desc else "Entrada via Alexa"

        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui conectar ao Weedverso na nuvem."
            ).response

        balances = state.setdefault("balances", {})
        wallet = balances.setdefault(wallet_key, {"label": wallet_name, "amount": 0.0})
        prev_balance = float(wallet.get("amount", 0.0))
        new_balance = prev_balance + amount
        wallet["amount"] = round(new_balance, 2)

        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        tx_entry = {
            "id": make_id(),
            "account": wallet_key,
            "type": "in",
            "value": round(amount, 2),
            "prev": round(prev_balance, 2),
            "note": note[:60],
            "debtorId": "",
            "myDebtId": "",
            "myDebtInstallment": 0,
            "at": now_iso,
            "category": note[:40],
            "categoryKey": note.lower()[:48]
        }
        state.setdefault("tx", []).insert(0, tx_entry)

        ok, push_err = push_state_to_gist(state)
        if not ok:
            return handler_input.response_builder.speak(
                "A entrada foi calculada, mas houve um erro ao sincronizar com a nuvem."
            ).response

        speech = (
            f"Registrado! Entrada de {format_spoken_currency(amount)} "
            f"na {wallet_name}. Seu novo saldo é de {format_spoken_currency(new_balance)}."
        )
        return handler_input.response_builder.speak(speech).response

class RegistrarGastoCartaoIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Gastei 100 reais no cartão', 'Lance 50 reais no crédito de farmácia'."""
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarGastoCartaoIntent")(handler_input)

    def handle(self, handler_input):
        raw_val = get_slot_value(handler_input, "valor")
        raw_cents = get_slot_value(handler_input, "centavos")
        raw_desc = get_slot_value(handler_input, "categoria") or get_slot_value(handler_input, "descricao")

        amount = calculate_amount(raw_val, raw_cents)

        if amount <= 0:
            return (
                handler_input.response_builder
                .speak("Qual foi o valor do gasto no cartão?")
                .ask("Por favor, diga o valor.")
                .response
            )

        note = raw_desc.capitalize() if raw_desc else "Gasto no Cartão"

        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui conectar ao seu banco de dados na nuvem."
            ).response

        credit = state.setdefault("credit", {"name": "Cartão", "used": 0.0, "reserved": 0.0, "tx": []})
        card_name = credit.get("name") or "Cartão"
        prev_used = float(credit.get("used", 0.0))
        new_used = round(prev_used + amount, 2)
        credit["used"] = new_used

        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry = {
            "id": make_id(),
            "type": "expense",
            "value": round(amount, 2),
            "desc": note[:60],
            "at": now_iso
        }
        credit.setdefault("tx", []).insert(0, entry)

        ok, push_err = push_state_to_gist(state)
        if not ok:
            return handler_input.response_builder.speak(
                "O gasto no cartão foi calculado, mas houve um erro ao sincronizar com a nuvem."
            ).response

        speech = (
            f"Registrado! Gasto de {format_spoken_currency(amount)} em {note} "
            f"no cartão {card_name}. Sua fatura atual é de {format_spoken_currency(new_used)}."
        )
        return handler_input.response_builder.speak(speech).response

class ConsultarFaturaIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Qual a fatura do cartão?', 'Quanto devo no cartão?'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarFaturaIntent")(handler_input)

    def handle(self, handler_input):
        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui consultar sua fatura no momento."
            ).response

        credit = state.get("credit", {})
        used = float(credit.get("used", 0.0))
        reserved = float(credit.get("reserved", 0.0))
        card_name = credit.get("name") or "Cartão"

        speech = (
            f"Sua fatura atual do cartão {card_name} é de {format_spoken_currency(used)}. "
            f"Você possui {format_spoken_currency(reserved)} em reserva para o pagamento."
        )
        return handler_input.response_builder.speak(speech).response

class ConsultarExtratoIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Quais foram minhas últimas movimentações?', 'Extrato'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarExtratoIntent")(handler_input)

    def handle(self, handler_input):
        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui acessar seu extrato no momento."
            ).response

        txs = state.get("tx", [])[:3]
        if not txs:
            return handler_input.response_builder.speak(
                "Você ainda não possui movimentações recentes registradas."
            ).response

        items = []
        for t in txs:
            direction = "Saída" if t.get("type") == "out" else "Entrada"
            val = format_spoken_currency(t.get("value", 0.0))
            note = t.get("note") or t.get("category") or "Geral"
            items.append(f"{direction} de {val} em {note}")

        speech = f"Suas últimas movimentações foram: {', '.join(items)}."
        return handler_input.response_builder.speak(speech).response

class ConsultarDevedoresIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Quem me deve?', 'Quanto tenho para receber?'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarDevedoresIntent")(handler_input)

    def handle(self, handler_input):
        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui consultar os devedores no momento."
            ).response

        debtors = [d for d in state.get("debtors", []) if not d.get("paid")]
        if not debtors:
            return handler_input.response_builder.speak(
                "Boas notícias! Você não tem nenhum valor pendente para receber."
            ).response

        total = sum(float(d.get("amount", 0.0)) for d in debtors)
        details = [f"{d.get('name', 'Alguém')}, com {format_spoken_currency(d.get('amount', 0.0))}" for d in debtors[:3]]

        speech = (
            f"Você tem {format_spoken_currency(total)} para receber no total. "
            f"Devedores em aberto: {', '.join(details)}."
        )
        return handler_input.response_builder.speak(speech).response

class ConsultarObjetivosIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Meus objetivos', 'Como estão minhas metas?'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarObjetivosIntent")(handler_input)

    def handle(self, handler_input):
        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui consultar seus objetivos no momento."
            ).response

        goals = state.get("goals", [])
        if not goals:
            return handler_input.response_builder.speak(
                "Você ainda não cadastrou nenhum objetivo no Weedverso."
            ).response

        details = []
        for g in goals[:3]:
            name = g.get("name") or "Objetivo"
            cur = format_spoken_currency(g.get("current", 0.0))
            tgt = format_spoken_currency(g.get("target", 0.0))
            details.append(f"{name}, com {cur} guardados de uma meta de {tgt}")

        speech = f"Seus objetivos atuais são: {', '.join(details)}."
        return handler_input.response_builder.speak(speech).response

class ConsultarInvestimentosIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Quanto eu tenho investido?', 'Saldo de investimentos'."""
    def can_handle(self, handler_input):
        return is_intent_name("ConsultarInvestimentosIntent")(handler_input)

    def handle(self, handler_input):
        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui consultar seus investimentos no momento."
            ).response

        invest = state.get("investments", {})
        total = float(invest.get("total", 0.0))

        speech = f"Seu saldo total investido atualmente é de {format_spoken_currency(total)}."
        return handler_input.response_builder.speak(speech).response

class RegistrarAporteIntentHandler(AbstractRequestHandler):
    """Chamado ao dizer: 'Aporte de 500 reais nos investimentos', 'Investi 200 reais'."""
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarAporteIntent")(handler_input)

    def handle(self, handler_input):
        raw_val = get_slot_value(handler_input, "valor")
        raw_cents = get_slot_value(handler_input, "centavos")

        amount = calculate_amount(raw_val, raw_cents)

        if amount <= 0:
            return (
                handler_input.response_builder
                .speak("Qual foi o valor do aporte para os investimentos?")
                .ask("Por favor, diga o valor.")
                .response
            )

        state, err = pull_state_from_gist()
        if not state:
            return handler_input.response_builder.speak(
                "Desculpe, não consegui conectar ao seu banco de dados na nuvem."
            ).response

        invest = state.setdefault("investments", {"total": 0.0, "history": []})
        old_total = float(invest.get("total", 0.0))
        new_total = round(old_total + amount, 2)
        invest["total"] = new_total

        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        invest.setdefault("history", []).insert(0, {
            "type": "add",
            "value": round(amount, 2),
            "balanceAfter": new_total,
            "note": "Aporte via Alexa",
            "at": now_iso
        })

        ok, push_err = push_state_to_gist(state)
        if not ok:
            return handler_input.response_builder.speak(
                "O aporte foi calculado, mas houve um erro ao sincronizar com a nuvem."
            ).response

        speech = (
            f"Registrado! Aporte de {format_spoken_currency(amount)} nos investimentos. "
            f"Seu novo saldo total investido é de {format_spoken_currency(new_total)}."
        )
        return handler_input.response_builder.speak(speech).response

class HelpIntentHandler(AbstractRequestHandler):
    """Ajuda ao usuário."""
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Com o Weedverso, você pode perguntar: "
            "'Qual é o meu saldo?', "
            "'Qual a fatura do cartão?', "
            "'Gastei trinta e cinco reais no almoço', "
            "'Lance cinquenta reais no cartão', "
            "'Quais foram minhas últimas movimentações?', ou "
            "'Quem me deve?'. O que você gostaria de fazer?"
        )
        return handler_input.response_builder.speak(speech).ask("Como posso ajudar?").response

class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Encerra a interação."""
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Até mais!").response

class FallbackIntentHandler(AbstractRequestHandler):
    """Caso a Alexa não entenda com clareza."""
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Não entendi esse comando no Weedverso. "
            "Você pode tentar dizer: 'Qual é o meu saldo' ou 'Gastei vinte reais'."
        )
        return handler_input.response_builder.speak(speech).ask("Deseja tentar novamente?").response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Fim de sessão."""
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Captura exceções globais com mensagem amigável."""
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        print(f"Erro capturado na Skill Alexa: {exception}")
        return handler_input.response_builder.speak(
            "Ocorreu um erro ao processar seu pedido no Weedverso. Por favor, tente novamente."
        ).response

# ==============================================================================
# Configuração do SkillBuilder
# ==============================================================================

sb = SkillBuilder()
if EXPECTED_SKILL_ID and hasattr(sb, "skill_id"):
    sb.skill_id = EXPECTED_SKILL_ID

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(ConsultarSaldoIntentHandler())
sb.add_request_handler(RegistrarGastoIntentHandler())
sb.add_request_handler(RegistrarEntradaIntentHandler())
sb.add_request_handler(RegistrarGastoCartaoIntentHandler())
sb.add_request_handler(ConsultarFaturaIntentHandler())
sb.add_request_handler(ConsultarExtratoIntentHandler())
sb.add_request_handler(ConsultarDevedoresIntentHandler())
sb.add_request_handler(ConsultarObjetivosIntentHandler())
sb.add_request_handler(ConsultarInvestimentosIntentHandler())
sb.add_request_handler(RegistrarAporteIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
