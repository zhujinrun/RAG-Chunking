"""
数据库迁移脚本
用于更新现有数据库结构，添加新字段
"""
import sqlite3
import os

DATABASE = 'knowledge_base.db'

def migrate():
    """执行数据库迁移"""
    if not os.path.exists(DATABASE):
        print("数据库文件不存在，无需迁移")
        return
    
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    print("开始数据库迁移...")
    
    # 检查并添加 documents 表的 file_format 字段
    try:
        cursor.execute("SELECT file_format FROM documents LIMIT 1")
        print("✓ documents.file_format 字段已存在")
    except sqlite3.OperationalError:
        print("→ 添加 documents.file_format 字段...")
        cursor.execute("ALTER TABLE documents ADD COLUMN file_format TEXT DEFAULT 'txt'")
        db.commit()
        print("✓ documents.file_format 字段添加成功")
    
    # 检查并添加 documents 表的 chunk_progress 字段
    try:
        cursor.execute("SELECT chunk_progress FROM documents LIMIT 1")
        print("✓ documents.chunk_progress 字段已存在")
    except sqlite3.OperationalError:
        print("→ 添加 documents.chunk_progress 字段...")
        cursor.execute("ALTER TABLE documents ADD COLUMN chunk_progress INTEGER DEFAULT 0")
        db.commit()
        print("✓ documents.chunk_progress 字段添加成功")
    
    # 检查并添加 documents 表的 chunk_count 字段
    try:
        cursor.execute("SELECT chunk_count FROM documents LIMIT 1")
        print("✓ documents.chunk_count 字段已存在")
    except sqlite3.OperationalError:
        print("→ 添加 documents.chunk_count 字段...")
        cursor.execute("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0")
        db.commit()
        print("✓ documents.chunk_count 字段添加成功")
    
    # 检查并添加 chunks 表的 keywords 字段
    try:
        cursor.execute("SELECT keywords FROM chunks LIMIT 1")
        print("✓ chunks.keywords 字段已存在")
    except sqlite3.OperationalError:
        print("→ 添加 chunks.keywords 字段...")
        cursor.execute("ALTER TABLE chunks ADD COLUMN keywords TEXT")
        db.commit()
        print("✓ chunks.keywords 字段添加成功")
    
    # 检查并添加 chunks 表的 questions 字段
    try:
        cursor.execute("SELECT questions FROM chunks LIMIT 1")
        print("✓ chunks.questions 字段已存在")
    except sqlite3.OperationalError:
        print("→ 添加 chunks.questions 字段...")
        cursor.execute("ALTER TABLE chunks ADD COLUMN questions TEXT")
        db.commit()
        print("✓ chunks.questions 字段添加成功")
    
    db.close()
    print("\n数据库迁移完成！")

if __name__ == '__main__':
    migrate()
