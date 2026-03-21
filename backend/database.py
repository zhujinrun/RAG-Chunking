import sqlite3
from datetime import datetime

DATABASE = 'knowledge_base.db'

def get_db():
    """获取数据库连接，使用WAL模式和更长的超时时间"""
    db = sqlite3.connect(DATABASE, timeout=60.0, check_same_thread=False, isolation_level=None)
    db.row_factory = sqlite3.Row
    # 启用WAL模式，提高并发性能
    db.execute('PRAGMA journal_mode=WAL')
    # 设置busy_timeout，在锁定时自动重试
    db.execute('PRAGMA busy_timeout=60000')
    return db

def init_db():
    db = get_db()
    
    # 知识库表
    db.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 文档表
    db.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_base_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_format TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chunk_status TEXT DEFAULT 'not_chunked',
            chunk_method TEXT,
            chunk_count INTEGER DEFAULT 0,
            chunk_progress INTEGER DEFAULT 0,
            FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases (id)
        )
    ''')
    
    # 分块表
    db.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            parent_chunk_id INTEGER,
            keywords TEXT,
            questions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
    ''')
    
    db.commit()
    db.close()
