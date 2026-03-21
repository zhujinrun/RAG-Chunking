@echo off
echo ====================================
echo 启动知识库后端服务
echo ====================================
echo.

REM 检查虚拟环境是否存在
if not exist venv (
    echo [错误] 虚拟环境不存在，请先运行 setup.bat 进行配置
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 创建uploads目录
if not exist uploads mkdir uploads

REM 启动Flask应用
echo 正在启动Flask服务器...
echo 服务地址: http://localhost:5000
echo 按 Ctrl+C 停止服务
echo.
python app.py
