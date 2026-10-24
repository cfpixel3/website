@echo off
title Bazaar Production Server
cd /d "%~dp0"
echo Starting Bazaar on http://127.0.0.1:5000 ...
python run_production.py
pause
