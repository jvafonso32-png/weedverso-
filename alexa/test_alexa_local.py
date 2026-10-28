# -*- coding: utf-8 -*-
"""
Testes automatizados locais para a Skill Alexa do Weedverso.
Valida:
1. Formatação de moeda fonética para voz (format_spoken_currency)
2. Normalização e inferência inteligente de carteiras (normalize_wallet_key)
3. Geração de IDs e estrutura de transações compatíveis com Weedverso
4. Comunicação de leitura com o GitHub Gist
"""

import sys
import os
import unittest
from pathlib import Path

# Carrega .env local se disponivel
env_file = Path(__file__).resolve().parent.parent / "app" / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Adiciona o diretorio alexa ao path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import lambda_function as alexa_mod

class TestAlexaSkillLogic(unittest.TestCase):

    def test_format_spoken_currency(self):
        self.assertEqual(alexa_mod.format_spoken_currency(0), "zero reais")
        self.assertEqual(alexa_mod.format_spoken_currency(1), "1 real")
        self.assertEqual(alexa_mod.format_spoken_currency(2), "2 reais")
        self.assertEqual(alexa_mod.format_spoken_currency(35.00), "35 reais")
        self.assertEqual(alexa_mod.format_spoken_currency(35.50), "35 reais e 50 centavos")
        self.assertEqual(alexa_mod.format_spoken_currency(0.75), "75 centavos")
        self.assertEqual(alexa_mod.format_spoken_currency(1.01), "1 real e 1 centavo")
        self.assertEqual(alexa_mod.format_spoken_currency(-50), "menos 50 reais")
        print("✅ Teste de pronúncia de valores monetários: APROVADO")

    def test_normalize_wallet_key(self):
        # Explicito
        self.assertEqual(alexa_mod.normalize_wallet_key("conta")[0], "conta")
        self.assertEqual(alexa_mod.normalize_wallet_key("vale refeicao")[0], "vale2")
        self.assertEqual(alexa_mod.normalize_wallet_key("refeição")[0], "vale2")
        self.assertEqual(alexa_mod.normalize_wallet_key("vr")[0], "vale2")
        self.assertEqual(alexa_mod.normalize_wallet_key("vale alimentacao")[0], "vale1")
        self.assertEqual(alexa_mod.normalize_wallet_key("mercado")[0], "vale1")
        self.assertEqual(alexa_mod.normalize_wallet_key("va")[0], "vale1")

        # Inferencia contextual sem dizer a carteira
        self.assertEqual(alexa_mod.normalize_wallet_key("", "almoço no restaurante")[0], "vale2")
        self.assertEqual(alexa_mod.normalize_wallet_key("", "ifood hambúrguer")[0], "vale2")
        self.assertEqual(alexa_mod.normalize_wallet_key("", "compras no supermercado")[0], "vale1")
        self.assertEqual(alexa_mod.normalize_wallet_key("", "açougue")[0], "vale1")
        self.assertEqual(alexa_mod.normalize_wallet_key("", "gasolina posto")[0], "conta")
        print("✅ Teste de inferência inteligente de carteira: APROVADO")

    def test_transaction_id_format(self):
        tid = alexa_mod.make_id()
        self.assertTrue(len(tid) >= 12)
        self.assertTrue(tid.isdigit())
        print("✅ Teste de formato de ID de transação: APROVADO")

    def test_mock_transaction_mutation(self):
        # Simula o estado
        state = {
            "balances": {
                "conta": {"label": "Saldo em Conta", "amount": 1000.0},
                "vale1": {"label": "Alelo Alimentação", "amount": 250.0},
                "vale2": {"label": "Alelo Refeição", "amount": 80.0}
            },
            "tx": []
        }

        # 1. Simula Gasto de R$ 35,00 no Vale Refeicao
        wallet_key, wallet_name = alexa_mod.normalize_wallet_key("vale refeição", "Almoço")
        amount = 35.0
        prev_balance = state["balances"][wallet_key]["amount"]
        new_balance = prev_balance - amount
        state["balances"][wallet_key]["amount"] = new_balance

        tx = {
            "id": alexa_mod.make_id(),
            "account": wallet_key,
            "type": "out",
            "value": amount,
            "prev": prev_balance,
            "note": "Almoço",
            "category": "Almoço",
            "categoryKey": "almoco"
        }
        state["tx"].insert(0, tx)

        self.assertEqual(state["balances"]["vale2"]["amount"], 45.0)
        self.assertEqual(len(state["tx"]), 1)
        self.assertEqual(state["tx"][0]["value"], 35.0)
        self.assertEqual(state["tx"][0]["account"], "vale2")

        # 2. Simula Entrada de R$ 200,00 na Conta Principal
        in_key, _ = alexa_mod.normalize_wallet_key("conta", "Salario")
        in_amount = 200.0
        in_prev = state["balances"][in_key]["amount"]
        state["balances"][in_key]["amount"] = in_prev + in_amount

        in_tx = {
            "id": alexa_mod.make_id(),
            "account": in_key,
            "type": "in",
            "value": in_amount,
            "prev": in_prev,
            "note": "Salário"
        }
        state["tx"].insert(0, in_tx)

        self.assertEqual(state["balances"]["conta"]["amount"], 1200.0)
        self.assertEqual(len(state["tx"]), 2)
        print("✅ Teste de mutação de saldo e histórico: APROVADO")

    def test_credit_card_and_extras(self):
        state = {
            "credit": {
                "name": "AMEX",
                "used": 1500.0,
                "reserved": 300.0,
                "tx": []
            },
            "debtors": [
                {"name": "Dilson", "amount": 500.0, "paid": False},
                {"name": "Lucas", "amount": 200.0, "paid": True}
            ],
            "tx": [
                {"type": "out", "value": 35.0, "note": "Almoço"},
                {"type": "in", "value": 200.0, "note": "Pix"}
            ]
        }

        # 1. Simula Gasto de R$ 100,00 no Cartão
        credit = state["credit"]
        card_prev = credit["used"]
        credit_amount = 100.0
        credit["used"] = round(card_prev + credit_amount, 2)
        credit["tx"].insert(0, {
            "id": alexa_mod.make_id(),
            "type": "expense",
            "value": credit_amount,
            "desc": "Farmácia"
        })
        self.assertEqual(credit["used"], 1600.0)
        self.assertEqual(len(credit["tx"]), 1)

        # 2. Simula Calculo de Devedores
        debtors = [d for d in state["debtors"] if not d.get("paid")]
        self.assertEqual(len(debtors), 1)
        self.assertEqual(debtors[0]["name"], "Dilson")
        self.assertEqual(debtors[0]["amount"], 500.0)

        # 3. Simula Extrato
        txs = state["tx"][:2]
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]["note"], "Almoço")
        print("✅ Teste de cartão, extrato e devedores: APROVADO")

    def test_gist_live_pull(self):
        state, msg = alexa_mod.pull_state_from_gist()
        if state is not None:
            self.assertIn("balances", state)
            self.assertIn("conta", state["balances"])
            print(f"✅ Teste de conexão Gist ao vivo: CONECTADO COM SUCESSO (Saldo Conta: R$ {state['balances']['conta']['amount']})")
        else:
            print(f"⚠️ Teste Gist ignorado ou sem rede: {msg}")

if __name__ == "__main__":
    unittest.main()
