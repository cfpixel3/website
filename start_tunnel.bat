@echo off
title Cloudflare Tunnel for fernhill.site
set CLOUDFLARED="C:\Program Files (x86)\cloudflared\cloudflared.exe"

echo ===================================================
echo   Cloudflare Tunnel Connector for fernhill.site
echo ===================================================
echo.

if not exist %CLOUDFLARED% (
    echo Error: cloudflared was not found at %CLOUDFLARED%
    pause
    exit /b 1
)

set /p TOKEN="Paste your Cloudflare Tunnel Token: "
if "%TOKEN%"=="" (
    echo No token provided. Exiting.
    pause
    exit /b 1
)

echo.
echo Connecting tunnel to Cloudflare...
%CLOUDFLARED% tunnel run --token %TOKEN%
pause
