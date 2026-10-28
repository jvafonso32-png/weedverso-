# 🎙️ Weedverso - Skill da Amazon Alexa

Integração oficial por voz da **Amazon Alexa** com o seu ecossistema **Weedverso**.
Permite consultar saldos e registrar entradas e saídas diretamente pela sua Alexa (Echo Dot, Echo Show, app Alexa no celular), funcionando **24 horas por dia com o seu computador desligado** e sincronizado em tempo real com o seu GitHub Gist e aplicativo móvel.

---

## 🚀 Como Ativar em 5 Minutos (100% Gratuito)

### Passo 1: Acessar o Console da Alexa
1. Acesse o [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Faça login com a mesma conta da Amazon que você usa no seu Echo / aplicativo da Alexa.

---

### Passo 2: Criar a Skill
1. Clique no botão **"Create Skill"**.
2. **Skill name:** Digite `Weedverso`
3. **Primary locale:** Selecione `Portuguese (BR)`
4. **Choose a model to add to your skill:** Selecione `Custom`
5. **Choose a method to host your skill's backend resources:** Selecione `Alexa-hosted (Python)`
6. Clique no botão **"Create Skill"** no canto superior direito e aguarde ~1 minuto enquanto a Amazon cria a infraestrutura.

---

### Passo 3: Configurar o Modelo de Voz (Interaction Model)
1. No menu lateral esquerdo, clique em **Interaction Model** ➜ **JSON Editor**.
2. Apague o que estiver lá e cole todo o conteúdo do arquivo [`alexa/interaction_model_pt_BR.json`](interaction_model_pt_BR.json).
3. Clique em **"Save Model"** e depois em **"Build Model"** no topo da tela (aguarde ~30 segundos até o aviso de sucesso).

---

### Passo 4: Colar o Código do Backend
1. No menu superior, clique na aba **"Code"**.
2. Abra o arquivo `lambda_function.py`, apague o conteúdo existente e cole o código de [`alexa/lambda_function.py`](lambda_function.py).
3. Abra o arquivo `requirements.txt` e garanta que tenha:
   ```text
   ask-sdk-core>=1.19.0
   ```
4. Clique em **"Save"** e depois no botão **"Deploy"** (aguarde o deploy terminar).

---

### Passo 5: Testar Imediatamente!
1. No menu superior, clique na aba **"Test"**.
2. Mude o seletor *"Skill testing is enabled in:"* de **Off** para **Development**.
3. Digite ou fale no microfone:
   - *"abra o weedverso"*
   - *"quanto eu tenho de saldo"*
   - *"gastei trinta e cinco reais no almoço"*
   - *"entraram duzentos reais na conta"*

Pronto! Automaticamente o seu aparelho Echo físico conectado à mesma conta já responderá a todos esses comandos!

---

## 🗣️ Exemplos de Comandos Suportados

### 💰 Consultar Saldos
- *"Alexa, abra o Weedverso e pergunte qual é o meu saldo"*
- *"Alexa, pergunte ao Weedverso quanto eu tenho no vale refeição"*
- *"Alexa, quanto sobrou no vale alimentação?"*
- *"Alexa, abra o Weedverso"* ➜ Alexa pergunta o que deseja ➜ *"Qual meu saldo?"*

### 📉 Registrar Gastos (Saídas)
- *"Alexa, peça ao Weedverso para registrar um gasto de 35 reais no almoço"* *(Detecta automaticamente o Vale Refeição)*
- *"Alexa, diga ao Weedverso que gastei 80 reais no mercado"* *(Detecta automaticamente o Vale Alimentação)*
- *"Alexa, lance 25 reais de gasolina na conta principal"*
- *"Alexa, saída de 50 reais de farmácia"*

### 📈 Registrar Entradas
- *"Alexa, diga ao Weedverso que entraram 200 reais na conta"*
- *"Alexa, registre uma entrada de 150 reais no vale refeição"*
- *"Alexa, adicione 100 reais no vale alimentação"*

---

### ⏪ Desfazer / Errei o Valor (Segurança Total)
- *"Alexa, desfaça o último lançamento em minhas finanças"*
- *"Alexa, errei o valor em minhas finanças"*
- *"Alexa, cancele o último gasto em minhas finanças"*
- *"Alexa, desfazer último registro"*
*(A Alexa remove a movimentação do Gist e devolve o dinheiro imediatamente para o saldo)*

### 🌙 Resumo Diário de Gastos (Balanço do Dia)
- *"Alexa, como foi meu dia em minhas finanças?"*
- *"Alexa, quanto gastei hoje em minhas finanças?"*
- *"Alexa, resumo do dia em minhas finanças"*
- *"Alexa, balanço de hoje em minhas finanças"*
*(A Alexa soma todas as saídas de Conta, Vales e Cartão feitas no dia de hoje e dá um resumo falado)*

---

## 🛡️ Sincronização em Tempo Real

Toda vez que você fala com a Alexa:
1. O backend da Amazon na AWS consulta seu **GitHub Gist**.
2. Executa a movimentação com data/hora e ID exclusivo.
3. Grava o novo saldo no Gist.
4. Seu **iPhone (PWA)** e o **Bot do Telegram** recebem as alterações automaticamente!
