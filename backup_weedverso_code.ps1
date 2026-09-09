param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ArchiveRoot = "C:\Users\joaov\OneDrive\Documentos\WEEDVERSO-CODE-BACKUPS"
$MirrorRoot = Join-Path $env:APPDATA "Weedverso\code-mirror"
$StageRoot = Join-Path $env:TEMP "weedverso-code-stage"
$ManifestPath = Join-Path $ArchiveRoot "backup-manifest.json"
$GitExeCandidates = @(
    (Get-Command git -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe"
) + (Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop\app-*\resources\app\git\cmd\git.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)

$RootFiles = @(
    "ABRIR WEEDVERSO.cmd",
    "TESTAR WEEDVERSO.cmd",
    "weedverso.cmd",
    "index.html",
    "shared_state.py",
    "shared_state_new.py"
)

$AppExcludedDirs = @(
    "data",
    "logs",
    "__pycache__",
    "deploy-temp",
    "dist"
)

$AppExcludedFiles = @(
    ".env",
    ".env.recovered-original",
    "*.pem",
    "*.pyc",
    "*.pyo"
)

function Write-Info {
    param([string]$Message)
    if (-not $Quiet) {
        Write-Output $Message
    }
}

function Invoke-RobocopyChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination,
        [string[]]$ExtraArgs = @()
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $args = @($Source, $Destination, "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
    if ($ExtraArgs) {
        $args += $ExtraArgs
    }

    & robocopy @args | Out-Null
    $exitCode = $LASTEXITCODE
    if ($exitCode -ge 8) {
        throw "Falha no robocopy de '$Source' para '$Destination' (codigo $exitCode)."
    }
}

function Get-GitExe {
    foreach ($candidate in $GitExeCandidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return ""
}

if (-not (Test-Path $ProjectRoot)) {
    throw "Projeto nao encontrado em $ProjectRoot"
}

New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
New-Item -ItemType Directory -Path $MirrorRoot -Force | Out-Null

if (Test-Path $StageRoot) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $StageRoot -Force | Out-Null

$stageApp = Join-Path $StageRoot "app"
$robocopyAppArgs = @()
if ($AppExcludedDirs.Count -gt 0) {
    $robocopyAppArgs += "/XD"
    $robocopyAppArgs += $AppExcludedDirs
}
if ($AppExcludedFiles.Count -gt 0) {
    $robocopyAppArgs += "/XF"
    $robocopyAppArgs += $AppExcludedFiles
}

Invoke-RobocopyChecked -Source (Join-Path $ProjectRoot "app") -Destination $stageApp -ExtraArgs $robocopyAppArgs

foreach ($file in $RootFiles) {
    $sourcePath = Join-Path $ProjectRoot $file
    if (Test-Path $sourcePath) {
        Copy-Item -LiteralPath $sourcePath -Destination (Join-Path $StageRoot $file) -Force
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archivePath = Join-Path $ArchiveRoot "weedverso-code-$timestamp.zip"
$latestArchivePath = Join-Path $ArchiveRoot "weedverso-code-latest.zip"
$bundlePath = Join-Path $ArchiveRoot "weedverso-history-$timestamp.bundle"
$latestBundlePath = Join-Path $ArchiveRoot "weedverso-history-latest.bundle"

if (Test-Path $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
if (Test-Path $latestArchivePath) {
    Remove-Item -LiteralPath $latestArchivePath -Force
}
if (Test-Path $bundlePath) {
    Remove-Item -LiteralPath $bundlePath -Force
}
if (Test-Path $latestBundlePath) {
    Remove-Item -LiteralPath $latestBundlePath -Force
}

Compress-Archive -Path (Join-Path $StageRoot "*") -DestinationPath $archivePath -CompressionLevel Optimal
Copy-Item -LiteralPath $archivePath -Destination $latestArchivePath -Force

$gitExe = Get-GitExe
if ($gitExe -and (Test-Path (Join-Path $ProjectRoot ".git"))) {
    & $gitExe -C $ProjectRoot bundle create $bundlePath --all | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar o bundle Git do codigo."
    }
    Copy-Item -LiteralPath $bundlePath -Destination $latestBundlePath -Force
}

Invoke-RobocopyChecked -Source $StageRoot -Destination $MirrorRoot -ExtraArgs @("/MIR")

$archiveCount = (Get-ChildItem -Path $ArchiveRoot -Filter "weedverso-code-*.zip" -File | Measure-Object).Count
$bundleCount = (Get-ChildItem -Path $ArchiveRoot -Filter "weedverso-history-*.bundle" -File | Measure-Object).Count
$manifest = [ordered]@{
    projectRoot = $ProjectRoot
    archiveRoot = $ArchiveRoot
    mirrorRoot = $MirrorRoot
    latestArchive = $latestArchivePath
    lastArchive = $archivePath
    latestBundle = $(if (Test-Path $latestBundlePath) { $latestBundlePath } else { "" })
    lastBundle = $(if (Test-Path $bundlePath) { $bundlePath } else { "" })
    lastRunAt = (Get-Date).ToString("s")
    archiveCount = $archiveCount
    bundleCount = $bundleCount
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Info "Backup do codigo concluido."
Write-Info "Zip: $archivePath"
if (Test-Path $bundlePath) {
    Write-Info "Bundle Git: $bundlePath"
}
Write-Info "Espelho: $MirrorRoot"
Write-Info "Manifesto: $ManifestPath"
