param(
    [string]$RepoName = "weedverso"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GhExe = @(
    "C:\Program Files\GitHub CLI\gh.exe",
    "C:\Program Files (x86)\GitHub CLI\gh.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$GitExe = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $GhExe) {
    throw "GitHub CLI nao encontrado."
}

if (-not $GitExe) {
    throw "Git nao encontrado."
}

& $GhExe auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Voce ainda nao fez login no GitHub CLI. Rode: gh auth login"
}

$hasOrigin = $false
try {
    & $GitExe -C $RepoRoot remote get-url origin | Out-Null
    $hasOrigin = ($LASTEXITCODE -eq 0)
} catch {}

if (-not $hasOrigin) {
    & $GhExe repo create $RepoName --private --source $RepoRoot --remote origin --push
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o repositorio privado no GitHub."
    }
} else {
    & $GitExe -C $RepoRoot push -u origin main
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao enviar o codigo para o origin."
    }
}

Write-Output "Repositorio privado pronto no GitHub."
