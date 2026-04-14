# Weedverso na Oracle Cloud Always Free

Guia preparado para este projeto em `09/04/2026`, com base na documentação oficial da Oracle:

- Recursos Always Free: [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- Criar instância: [Creating an Instance](https://docs.oracle.com/iaas/Content/Compute/Tasks/launchinginstance.htm)
- Regras de entrada: [Adding Ingress Rules](https://docs.oracle.com/en-us/iaas/mysql-database/doc/adding-ingress-rules-compute-instance-bastion-session-or-vpn-connection.html)

## Arquitetura usada

- Uma VM Linux Always Free
- Um processo Python rodando:
  - bot do Telegram
  - API do Weedverso
  - frontend `index.html` servido pela própria API
- Dados persistidos em `data/shared_state.json`

## O que a Oracle oferece no Always Free

Segundo a documentação oficial consultada em `09/04/2026`:

- até `2` instâncias `VM.Standard.E2.1.Micro`
- ou recursos `Ampere A1` equivalentes a até `4 OCPUs` e `24 GB RAM`
- `200 GB` combinados de boot volume + block volume na home region

## Recomendação para este projeto

Use:

- `Oracle Linux`
- shape `VM.Standard.A1.Flex`
- `1 OCPU`
- `6 GB RAM`
- boot volume padrão
- IP público

Isso deixa o bot mais confortável que o micro de `1 GB`.

## Portas para abrir

Na security list ou NSG da subnet pública:

- `22/TCP` para SSH
- `8765/TCP` para abrir o Weedverso na web

## Fluxo 1: subir por Git

Na VM:

```bash
sudo dnf install -y git python3
sudo bash deploy/oracle/install_oracle_vm.sh https://SEU-REPO.git
sudo nano /opt/weedverso/app/.env
sudo systemctl restart weedverso
sudo systemctl status weedverso --no-pager
```

Depois abra:

```text
http://IP_PUBLICO:8765
```

## Fluxo 2: subir sem Git

No seu PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\oracle\package_oracle.ps1
```

Isso gera:

```text
dist\weedverso-app.zip
```

Se quiser levar seu estado real atual junto:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\oracle\package_oracle.ps1 -IncludeData
```

Isso gera:

```text
dist\weedverso-app-with-data.zip
```

## Fluxo 3: deploy remoto automatizado pelo Windows

Com a VM criada e a chave `.pem` no seu PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\oracle\deploy_oracle_remote.ps1 -HostName SEU_IP_PUBLICO -UserName opc -SshKeyPath C:\caminho\oracle.pem
```

Esse fluxo:

1. gera ou reaproveita o pacote certo
2. inclui seus dados atuais por padrao
3. envia o projeto para a VM
4. envia o `.env`
5. instala dependencias
6. registra o servico
7. sobe o Weedverso
8. faz teste de saude na propria VM

Depois:

1. envie o `.zip` para a VM por `scp` ou WinSCP
2. extraia em `/opt/weedverso/app`
3. copie `deploy/oracle/.env.oracle.example` para `.env`
4. edite o token
5. copie o service para `/etc/systemd/system`
6. habilite o serviço

Exemplo na VM:

```bash
sudo mkdir -p /opt/weedverso/app
cd /opt/weedverso/app
sudo unzip weedverso-app.zip
sudo cp deploy/oracle/.env.oracle.example .env
sudo nano .env
sudo cp deploy/oracle/weedverso.service /etc/systemd/system/weedverso.service
sudo useradd --system --create-home --home-dir /opt/weedverso --shell /sbin/nologin weedverso || true
sudo chown -R weedverso:weedverso /opt/weedverso
sudo systemctl daemon-reload
sudo systemctl enable weedverso
sudo systemctl restart weedverso
```

## Variáveis de ambiente

Arquivo `.env` na VM:

```env
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_ALLOWED_CHAT_IDS=
WEEDVERSO_HOST=0.0.0.0
WEEDVERSO_PORT=8765
```

## Verificações

Saúde da API:

```bash
curl http://127.0.0.1:8765/health
```

Logs do serviço:

```bash
sudo journalctl -u weedverso -f
```

## Backup manual

Script pronto:

```bash
sudo bash /opt/weedverso/app/deploy/oracle/backup_state.sh
```

## Observação importante

A Oracle informa que instâncias Always Free podem ser reclamadas se ficarem ociosas por um período, com critérios de CPU, rede e memória. Para projeto pessoal isso é aceitável, mas para algo crítico o ideal é:

- usar block volume com rotina de backup
- considerar plano pago no futuro

## Próximo passo recomendado

Depois do deploy básico funcionando, o ideal é evoluir para um destes:

1. colocar domínio
2. colocar HTTPS com Nginx + Caddy
3. trocar `shared_state.json` por Postgres
