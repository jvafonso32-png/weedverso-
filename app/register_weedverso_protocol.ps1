$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProtocolRoot = "HKCU:\Software\Classes\weedverso"
$CommandPath = Join-Path $ProtocolRoot "shell\open\command"
$IconPath = Join-Path $ProtocolRoot "DefaultIcon"
$Launcher = Join-Path $AppDir "launch_weedverso_protocol.vbs"
$IconFile = Join-Path $AppDir "assets\weedverso-icon.ico"

New-Item -Path $ProtocolRoot -Force | Out-Null
Set-Item -Path $ProtocolRoot -Value "URL:Weedverso Protocol"
New-ItemProperty -Path $ProtocolRoot -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null

New-Item -Path $CommandPath -Force | Out-Null
Set-Item -Path $CommandPath -Value ('wscript.exe "' + $Launcher + '" "%1"')

if (Test-Path $IconFile) {
    New-Item -Path $IconPath -Force | Out-Null
    Set-Item -Path $IconPath -Value $IconFile
}
