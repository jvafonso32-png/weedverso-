param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\joaov\OneDrive\Documentos\Desktop\WEEDVERSO"
$ArchiveRoot = "C:\Users\joaov\OneDrive\Documentos\WEEDVERSO-CODE-BACKUPS"
$MirrorRoot = Join-Path $env:APPDATA "Weedverso\code-mirror"
$StageRoot = Join-Path $env:TEMP "weedverso-code-stage"
$ManifestPath = Join-Path $ArchiveRoot "backup-manifest.json"

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

if (Test-Path $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
if (Test-Path $latestArchivePath) {
    Remove-Item -LiteralPath $latestArchivePath -Force
}

Compress-Archive -Path (Join-Path $StageRoot "*") -DestinationPath $archivePath -CompressionLevel Optimal
Copy-Item -LiteralPath $archivePath -Destination $latestArchivePath -Force

Invoke-RobocopyChecked -Source $StageRoot -Destination $MirrorRoot -ExtraArgs @("/MIR")

$archiveCount = (Get-ChildItem -Path $ArchiveRoot -Filter "weedverso-code-*.zip" -File | Measure-Object).Count
$manifest = [ordered]@{
    projectRoot = $ProjectRoot
    archiveRoot = $ArchiveRoot
    mirrorRoot = $MirrorRoot
    latestArchive = $latestArchivePath
    lastArchive = $archivePath
    lastRunAt = (Get-Date).ToString("s")
    archiveCount = $archiveCount
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Info "Backup do codigo concluido."
Write-Info "Zip: $archivePath"
Write-Info "Espelho: $MirrorRoot"
Write-Info "Manifesto: $ManifestPath"
