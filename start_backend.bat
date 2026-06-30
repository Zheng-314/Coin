@echo off
chcp 65001 > nul
echo ========================================
echo      检查并启动后端服务
echo ========================================
echo.

cd /d "%~dp0"
set VENV_PATH=venv_py311

echo [1/3] 检查虚拟环境...
if not exist "%VENV_PATH%\Scripts\python.exe" (
    echo 错误: 虚拟环境不存在: %VENV_PATH%
    pause
    exit /b 1
)
echo ✓ 虚拟环境存在

echo.
echo [2/3] 检查依赖...
%VENV_PATH%\Scripts\python.exe -c "import cv2" 2>nul
if errorlevel 1 (
    echo 正在安装缺失的依赖...
    %VENV_PATH%\Scripts\python.exe -m pip install opencv-python pyjwt neo4j pandas pyarrow -q
    echo ✓ 依赖安装完成
) else (
    echo ✓ 所有依赖已安装
)

echo.
echo [3/3] 启动后端服务...
echo 后端地址: http://localhost:5001
echo 按 Ctrl+C 停止服务
echo.

cd backend
%VENV_PATH%\Scripts\python.exe app_new.py

pause
