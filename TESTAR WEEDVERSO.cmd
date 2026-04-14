@echo off
cd /d "%~dp0app"
py -3.11 run_validation_suite.py
pause
