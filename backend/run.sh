#!/bin/bash

echo "===================================="
echo "启动知识库后端服务"
echo "===================================="
echo ""

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "[错误] 虚拟环境不存在，请先运行 ./setup.sh 进行配置"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 创建uploads目录
mkdir -p uploads

# 启动Flask应用
echo "正在启动Flask服务器..."
echo "服务地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务"
echo ""
python app.py
