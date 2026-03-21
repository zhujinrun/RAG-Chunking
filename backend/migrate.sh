#!/bin/bash

echo "===================================="
echo "数据库迁移工具"
echo "===================================="
echo ""

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "[错误] 虚拟环境不存在，请先运行 ./setup.sh 进行配置"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 执行迁移
echo "正在执行数据库迁移..."
python migrate_db.py

echo ""
echo "迁移完成！"
