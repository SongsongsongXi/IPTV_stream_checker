@echo off
chcp 65001 >nul 2>&1
title 直播源检测工具

echo ==========================================
echo           直播源检测工具 v2.0
echo ==========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python 3.6+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 检查Python版本...
python --version

:: 检查虚拟环境是否存在
if not exist "venv" (
    echo.
    echo 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功！
)

:: 激活虚拟环境
echo.
echo 激活虚拟环境...
call venv\Scripts\activate.bat

:: 检查并安装依赖
echo.
echo 检查依赖包...
python -c "import requests" 2>nul
if errorlevel 1 (
    echo 安装requests库...
    pip install requests
    if errorlevel 1 (
        echo 错误：安装requests失败
        pause
        exit /b 1
    )
)

python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo 错误：tkinter不可用，请重新安装Python并确保包含tkinter
    pause
    exit /b 1
)

echo.
echo 启动直播源检测工具...
python stream_checker.py

:: 保持虚拟环境激活状态
echo.
echo 程序已退出，虚拟环境仍在激活状态
echo 输入 deactivate 退出虚拟环境
cmd /k
