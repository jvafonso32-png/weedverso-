# Melhorias de toque e lançamentos

- Controles maiores no celular; navegação e textos com mais espaço.
- Botão `+` oferece ações da aba atual: cartão, aportes/resgates e contas a pagar/receber.
- Favoritos guardam descrição, conta, tipo e valor opcional **neste navegador**. Selecionar ou salvar um favorito nunca registra um lançamento.
- A descrição do lançamento fica em uma seção opcional; a conta escolhida é indicada antes da confirmação.
- O extrato abre detalhes completos e permite acessar o editor existente.
- Lançamentos, ajustes de saldo e investimentos podem ser desfeitos por 15 segundos. O desfazer é recusado se o lançamento ou saldo tiver sido alterado depois.
- Modais fecham com Escape, mantêm o foco dentro deles e acompanham a altura disponível quando o teclado aparece.
- Próxima parcela, vencimento e total restante ficam separados nas dívidas.
- Salvamentos consecutivos são enfileirados; respostas antigas de sincronização não substituem operações locais recentes.

## Verificação

```powershell
node --test tests/touch-ui-safety.test.cjs
python -m unittest discover -s tests -p test_ui_installer.py -v
python tests/serve-touch-preview.py
```

A prévia fica em `http://127.0.0.1:8951` e usa somente registros fictícios em memória. Ela bloqueia conexões com serviços externos. Fechar o servidor descarta esses registros.

## Atualizar o mesmo servidor

```powershell
python tools/update_frontend.py --host SEU_HOST --key CAMINHO_DA_CHAVE
```

O atualizador descobre a pasta pelo serviço ativo e envia **somente** `index.html`, `assets/touch-ui.css` e `assets/touch-ui.js`. Faz backup dos arquivos anteriores e uma cópia dos dados no próprio servidor, fora da pasta pública. Instala os recursos primeiro e substitui o HTML de forma atômica no final. Não reinicia o serviço, muda o endereço, substitui `.env`, atualiza o backend ou restaura dados de uma cópia local.

Se o servidor não responder, nenhum arquivo remoto é alterado. O script conserva a verificação da chave SSH do servidor.
