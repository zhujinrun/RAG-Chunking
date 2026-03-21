#!/bin/bash

echo "===================================="
echo "知识库后端环境配置脚本"
echo "===================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.8+"
    exit 1
fi

echo "[1/4] 检测到Python版本："
python3 --version
echo ""

# 创建虚拟环境
echo "[2/4] 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
    echo "虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境并安装依赖
echo "[3/4] 激活虚拟环境并安装依赖..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[错误] 激活虚拟环境失败"
    exit 1
fi

echo "正在安装依赖包..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[错误] 安装依赖失败"
    exit 1
fi
echo ""

# 初始化数据库
echo "[4/4] 初始化数据库..."
python -c "from database import init_db; init_db(); print('数据库初始化成功')"
if [ $? -ne 0 ]; then
    echo "[错误] 数据库初始化失败"
    exit 1
fi

# 执行数据库迁移
echo "执行数据库迁移..."
python migrate_db.py
if [ $? -ne 0 ]; then
    echo "[警告] 数据库迁移失败，但可以继续"
fi
echo ""

echo "===================================="
echo "环境配置完成！"
echo "===================================="
echo ""
echo "使用以下命令启动后端服务："
echo "  cd backend"
echo "  ./run.sh"
echo ""
