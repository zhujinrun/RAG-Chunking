@echo off
echo ====================================
echo 数据库迁移工具
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

REM 执行迁移
echo 正在执行数据库迁移...
python migrate_db.py

echo.
echo 迁移完成！
pause
