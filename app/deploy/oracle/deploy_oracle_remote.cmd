@echo off
setlocal

if "%~1"=="" (
  echo Uso:
  echo deploy_oracle_remote.cmd IP_PUBLICO CAMINHO_DA_CHAVE_PEM [USUARIO]
  exit /b 1
)

set HOST_NAME=%~1
set SSH_KEY=%~2
set USER_NAME=%~3

if "%USER_NAME%"=="" set USER_NAME=opc

powershell -ExecutionPolicy Bypass -File "%~dp0deploy_oracle_remote.ps1" -HostName "%HOST_NAME%" -SshKeyPath "%SSH_KEY%" -UserName "%USER_NAME%"
