@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%venv_py311\Scripts\python.exe"
set "CLOUDFLARED=%ROOT%tools\cloudflared.exe"
set "PORT=7890"

if not exist "%PY%" (
  echo [错误] 找不到 Python 虚拟环境：%PY%
  pause
  exit /b 1
)
if not exist "%CLOUDFLARED%" (
  echo [错误] 找不到 cloudflared：%CLOUDFLARED%
  pause
  exit /b 1
)

rem 停止旧服务，避免端口/隧道冲突
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% .*LISTENING"') do taskkill /PID %%p /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
del "%ROOT%public_backend.log" "%ROOT%public_backend.err.log" "%ROOT%cloudflared.log" "%ROOT%cloudflared.err.log" >nul 2>&1

rem 后端同时提供 Web 页面和 API；输出写入日志，不弹出额外窗口
powershell -NoProfile -Command "$env:PORT='%PORT%'; Start-Process -FilePath '%PY%' -ArgumentList 'server.py' -WorkingDirectory '%ROOT%backend' -RedirectStandardOutput '%ROOT%public_backend.log' -RedirectStandardError '%ROOT%public_backend.err.log' -WindowStyle Hidden"

echo 正在加载 YOLO 和 ONNX 模型（约 40 秒）...
timeout /t 40 /nobreak >nul

rem Cloudflare 免费 Quick Tunnel，公网地址会写入 cloudflared.log
powershell -NoProfile -Command "Start-Process -FilePath '%CLOUDFLARED%' -ArgumentList 'tunnel','--url','http://127.0.0.1:%PORT%' -RedirectStandardOutput '%ROOT%cloudflared.log' -RedirectStandardError '%ROOT%cloudflared.err.log' -WindowStyle Hidden"

timeout /t 8 /nobreak >nul
echo.
echo ========================================
echo 鉴泉识珍公网服务已启动
echo ========================================
echo 新公网地址已写入：%ROOT%cloudflared.err.log
echo 在日志中找 https://xxxxx.trycloudflare.com
echo 手机 App：我的 ^> 服务器地址 ^> 填入该地址
echo 电脑关机、网络断开或停止进程后，公网服务会失效。
echo ========================================
pause
