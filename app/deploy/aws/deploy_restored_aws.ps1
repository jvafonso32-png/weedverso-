param(
    [Parameter(Mandatory = $true)]
    [string]$HostIp,

    [string]$SshUser = "ec2-user",

    [string]$PemPath = "C:\Users\joaov\OneDrive\Documentos\Desktop\WEEDVERSO\weedversonovo.pem"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Comando externo falhou com codigo $LASTEXITCODE"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployDirRoot = Split-Path -Parent $ScriptDir
$AppDir = Split-Path -Parent $DeployDirRoot
$DesktopRoot = Split-Path -Parent $AppDir
$DeployDir = Join-Path $DesktopRoot "deploy-temp"
$ArchivePath = Join-Path $DeployDir "weedverso-aws-restored.tgz"
$EnvPath = Join-Path $DeployDir "weedverso-aws.env"
$RemoteArchive = "/tmp/weedverso-aws-restored.tgz"
$RemoteEnv = "/tmp/weedverso-aws.env"
$RemoteInstall = "/tmp/install_restored_weedverso.sh"
$PublicHost = "$HostIp.sslip.io"
$OriginalEnv = Join-Path $AppDir ".env.recovered-original"
$DesktopEnv = Join-Path $AppDir ".env"
$LocalInstallScript = Join-Path $ScriptDir "install_restored_weedverso.sh"

New-Item -ItemType Directory -Path $DeployDir -Force | Out-Null

if (-not (Test-Path $OriginalEnv)) {
    throw "Nao encontrei $OriginalEnv"
}

if (-not (Test-Path $LocalInstallScript)) {
    throw "Nao encontrei $LocalInstallScript"
}

$map = @{}
foreach ($line in Get-Content $OriginalEnv) {
    if ($line -match '^[\s#]') { continue }
    $parts = $line -split '=', 2
    if ($parts.Count -eq 2) {
        $map[$parts[0].Trim()] = $parts[1]
    }
}

if (Test-Path $DesktopEnv) {
    foreach ($line in Get-Content $DesktopEnv) {
        if ($line -match '^[\s#]') { continue }
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            if ($key -in @("WEEDVERSO_SYNC_TOKEN")) {
                $map[$key] = $parts[1]
            }
        }
    }
}

$map["WEEDVERSO_HOST"] = "127.0.0.1"
$map["WEEDVERSO_PORT"] = "8765"
$map["WEEDVERSO_PUBLIC_URL"] = "https://$PublicHost"
$map["WEEDVERSO_SHARE_HOST"] = ""

$ordered = @(
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_CHAT_IDS",
    "WEEDVERSO_HOST",
    "WEEDVERSO_PORT",
    "WEEDVERSO_SHARE_HOST",
    "WEEDVERSO_PUBLIC_URL",
    "WEEDVERSO_NOTIFY_CHAT_ID",
    "WEEDVERSO_LOGIN_USER",
    "WEEDVERSO_LOGIN_PASSWORD",
    "WEEDVERSO_LOGIN_PASSWORD_HASH",
    "WEEDVERSO_SYNC_TOKEN",
    "WEEDVERSO_SESSION_DAYS",
    "TELEGRAM_AUTO_DELETE_SECONDS",
    "TELEGRAM_DELETE_USER_MESSAGES",
    "DISCORD_WEBHOOK_URL"
)

$envLines = @("# Deploy restaurado automaticamente para AWS")
foreach ($key in $ordered) {
    if ($map.ContainsKey($key)) {
        $envLines += "$key=$($map[$key])"
    }
}
Set-Content -Path $EnvPath -Value $envLines -Encoding UTF8

$tarSource = @(
    ".env.example",
    ".gitignore",
    "api_server.py",
    "build_weedverso_release.py",
    "desktop_cloud_sync.py",
    "desktop_code_backup.py",
    "desktop_code_backup_status.py",
    "env_loader.py",
    "handle_weedverso_protocol.ps1",
    "index.html",
    "launch_weedverso_hidden.vbs",
    "launch_weedverso_protocol.vbs",
    "login.html",
    "register_weedverso_protocol.ps1",
    "shared_state.py",
    "share_publish.py",
    "start_weedverso.ps1",
    "telegram_bot.py",
    "telegram_chats.py",
    "telegram_runtime.py",
    "weedverso.cmd",
    "weedverso_app.py",
    "weedverso_paths.py",
    "VERSION",
    "deploy",
    "data"
)

if (Test-Path $ArchivePath) {
    Remove-Item $ArchivePath -Force
}

Invoke-Checked { tar -czf $ArchivePath -C $AppDir $tarSource }

Invoke-Checked { scp -i $PemPath $ArchivePath "${SshUser}@${HostIp}:$RemoteArchive" }
Invoke-Checked { scp -i $PemPath $EnvPath "${SshUser}@${HostIp}:$RemoteEnv" }
Invoke-Checked { scp -i $PemPath $LocalInstallScript "${SshUser}@${HostIp}:$RemoteInstall" }

Invoke-Checked { ssh -i $PemPath "${SshUser}@${HostIp}" "chmod +x $RemoteInstall && sudo bash $RemoteInstall $RemoteArchive $RemoteEnv $PublicHost" }

Write-Output "Deploy finalizado em https://$PublicHost"
