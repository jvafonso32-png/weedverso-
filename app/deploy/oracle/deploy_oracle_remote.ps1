param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [Parameter(Mandatory = $false)]
    [string]$UserName = "opc",

    [Parameter(Mandatory = $true)]
    [string]$SshKeyPath,

    [Parameter(Mandatory = $false)]
    [switch]$IncludeData = $true
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$zipName = if ($IncludeData) { "weedverso-app-with-data.zip" } else { "weedverso-app.zip" }
$zipPath = Join-Path $projectRoot ("dist\\" + $zipName)
$envPath = Join-Path $projectRoot ".env"

if ($IncludeData) {
    Write-Output "Gerando pacote com dados atuais..."
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "package_oracle.ps1") -IncludeData
}
elseif (!(Test-Path $zipPath)) {
    Write-Output "Pacote nao encontrado. Gerando..."
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "package_oracle.ps1")
}

if (!(Test-Path $envPath)) {
    throw "Arquivo .env nao encontrado em $envPath"
}

if (!(Test-Path $SshKeyPath)) {
    throw "Chave SSH nao encontrada em $SshKeyPath"
}

$remote = "$UserName@$HostName"
$remoteZip = "/tmp/weedverso-app.zip"
$remoteEnv = "/tmp/weedverso.env"
$sshOptions = @(
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "BatchMode=yes"
)

Write-Output "Enviando pacote para $remote ..."
scp @sshOptions -i $SshKeyPath $zipPath "${remote}:$remoteZip"
scp @sshOptions -i $SshKeyPath $envPath "${remote}:$remoteEnv"

$remoteScript = @"
set -euo pipefail
if ! command -v unzip >/dev/null 2>&1; then
  sudo dnf install -y unzip
fi
sudo mkdir -p /opt/weedverso/app
sudo rm -rf /opt/weedverso/app/*
sudo unzip -o $remoteZip -d /opt/weedverso/app
sudo cp $remoteEnv /opt/weedverso/app/.env
sudo bash /opt/weedverso/app/deploy/oracle/install_oracle_vm.sh
sudo mkdir -p /opt/weedverso/app/data
sudo chown -R weedverso:weedverso /opt/weedverso
sudo chmod -R u+rwX,g+rX /opt/weedverso/app/data
sudo systemctl restart weedverso
sudo systemctl status weedverso --no-pager
curl -s http://127.0.0.1:8765/health
"@

Write-Output "Instalando remotamente ..."
$remoteScript | ssh @sshOptions -i $SshKeyPath $remote "bash -s"

Write-Output "Deploy finalizado."
Write-Output "Abra: http://$HostName`:8765"
