param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $AppDir "logs"
$HealthUrl = "http://127.0.0.1:8765/health"

function Read-WeedversoEnv {
    $envPath = Join-Path $AppDir ".env"
    $map = @{}
    if (-not (Test-Path $envPath)) {
        return $map
    }

    foreach ($rawLine in Get-Content $envPath) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }
        $parts = $line -split "=", 2
        $map[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }

    return $map
}

function Test-WeedversoHealth {
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2
        return $response.status -eq "ok"
    }
    catch {
        return $false
    }
}

function Get-PythonExe {
    $candidates = @()

    try {
        $resolved = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($resolved) {
            $candidates += $resolved.Trim()
        }
    }
    catch {}

    try {
        $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($resolved) {
            $candidates += $resolved.Trim()
        }
    }
    catch {}

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source) {
        $candidates += $pythonCommand.Source
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    throw "Python 3 nao encontrado para iniciar o Weedverso."
}

function Get-CloudLoginUrl {
    param(
        [hashtable]$EnvMap
    )

    $base = [string]($EnvMap["WEEDVERSO_CLOUD_URL"])
    if (-not $base) {
        return ""
    }
    $base = $base.Trim().TrimEnd("/")
    if (-not $base) {
        return ""
    }
    if ($base -match "/login$") {
        return $base
    }
    return "$base/login"
}

function Get-BrowserAppExe {
    $candidates = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Users\joaov\AppData\Local\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "C:\Users\joaov\AppData\Local\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return ""
}

function Open-WeedversoWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    $browserExe = Get-BrowserAppExe
    if ($browserExe) {
        Start-Process `
            -FilePath $browserExe `
            -ArgumentList "--app=$Url", "--start-maximized", "--disable-session-crashed-bubble", "--no-first-run"
        return
    }

    Start-Process $Url
}

function Get-ExistingCloudSyncProcess {
    try {
        return Get-CimInstance Win32_Process |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -like "*desktop_cloud_sync.py*" -and
                $_.CommandLine -like "*$AppDir*"
            } |
            Select-Object -First 1
    }
    catch {
        return $null
    }
}

function Ensure-CloudMirror {
    $existing = Get-ExistingCloudSyncProcess
    if ($existing) {
        return
    }

    $pythonExe = Get-PythonExe
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
    $stdoutLog = Join-Path $LogsDir "cloud-sync.stdout.log"
    $stderrLog = Join-Path $LogsDir "cloud-sync.stderr.log"

    Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "-u", "desktop_cloud_sync.py", "run" `
        -WorkingDirectory $AppDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog
}

function Start-LocalWeedverso {
    if (-not (Test-WeedversoHealth)) {
        $pythonExe = Get-PythonExe
        New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
        $stdoutLog = Join-Path $LogsDir "weedverso.stdout.log"
        $stderrLog = Join-Path $LogsDir "weedverso.stderr.log"

        Start-Process `
            -FilePath $pythonExe `
            -ArgumentList "-u", "weedverso_app.py" `
            -WorkingDirectory $AppDir `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog

        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 500
            if (Test-WeedversoHealth) {
                break
            }
        }
    }

    if (-not (Test-WeedversoHealth)) {
        throw "Weedverso nao respondeu em http://127.0.0.1:8765"
    }
}

$envMap = Read-WeedversoEnv
$cloudLoginUrl = Get-CloudLoginUrl -EnvMap $envMap

if ($cloudLoginUrl) {
    Ensure-CloudMirror
    if ($OpenBrowser) {
        Open-WeedversoWindow -Url $cloudLoginUrl
    }
    exit 0
}

Start-LocalWeedverso

if ($OpenBrowser) {
    Open-WeedversoWindow -Url "http://127.0.0.1:8765/"
}
