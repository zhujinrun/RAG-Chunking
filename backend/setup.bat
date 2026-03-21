@echo off
echo ====================================
echo 知识库后端环境配置脚本
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 检测到Python版本：
python --version
echo.

REM 创建虚拟环境
echo [2/4] 创建虚拟环境...
if exist venv (
    echo 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功
)
echo.

REM 激活虚拟环境并安装依赖
echo [3/4] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

echo 正在安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)
echo.

REM 初始化数据库
echo [4/4] 初始化数据库...
python -c "from database import init_db; init_db(); print('数据库初始化成功')"
if errorlevel 1 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)

REM 执行数据库迁移
echo 执行数据库迁移...
python migrate_db.py
if errorlevel 1 (
    echo [警告] 数据库迁移失败，但可以继续
)
echo.

echo ====================================
echo 环境配置完成！
echo ====================================
echo.
echo 使用以下命令启动后端服务：
echo   cd backend
echo   run.bat
echo.
pause
