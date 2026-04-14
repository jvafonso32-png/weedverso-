param(
    [string]$Uri = ""
)

$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $AppDir "logs"

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

    throw "Python 3 nao encontrado para executar o backup do codigo."
}

if (-not $Uri -or ($Uri -notmatch "github-backup")) {
    exit 0
}

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$pythonExe = Get-PythonExe
$stdoutLog = Join-Path $LogsDir "desktop-code-backup.stdout.log"
$stderrLog = Join-Path $LogsDir "desktop-code-backup.stderr.log"

Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-u", "desktop_code_backup.py", "run", "--trigger", "desktop-protocol", "--uri", $Uri `
    -WorkingDirectory $AppDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog
