from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from database import init_db, get_db
from chunking import ChunkingService
import json
import sqlite3

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化数据库
init_db()

# 执行数据库迁移
try:
    from migrate_db import migrate
    migrate()
except Exception as e:
    print(f"数据库迁移警告: {e}")

@app.route('/api/knowledge-bases', methods=['GET'])
def get_knowledge_bases():
    """获取所有知识库"""
    db = get_db()
    kbs = db.execute('SELECT * FROM knowledge_bases ORDER BY created_at DESC').fetchall()
    return jsonify([dict(kb) for kb in kbs])

@app.route('/api/knowledge-bases', methods=['POST'])
def create_knowledge_base():
    """创建知识库"""
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO knowledge_bases (name, description) VALUES (?, ?)',
        (name, description)
    )
    db.commit()
    
    return jsonify({'id': cursor.lastrowid, 'name': name, 'description': description})

@app.route('/api/knowledge-bases/<int:kb_id>', methods=['DELETE'])
def delete_knowledge_base(kb_id):
    """删除知识库及其所有文档和分块"""
    db = get_db()
    
    # 获取知识库下的所有文档
    documents = db.execute(
        'SELECT * FROM documents WHERE knowledge_base_id = ?',
        (kb_id,)
    ).fetchall()
    
    # 删除文档文件和数据
    for doc in documents:
        if os.path.exists(doc['file_path']):
            os.remove(doc['file_path'])
        db.execute('DELETE FROM chunks WHERE document_id = ?', (doc['id'],))
    
    # 删除所有文档
    db.execute('DELETE FROM documents WHERE knowledge_base_id = ?', (kb_id,))
    
    # 删除知识库
    db.execute('DELETE FROM knowledge_bases WHERE id = ?', (kb_id,))
    db.commit()
    
    return jsonify({'success': True})

@app.route('/api/knowledge-bases/<int:kb_id>/documents', methods=['GET'])
def get_documents(kb_id):
    """获取知识库的文档列表"""
    db = get_db()
    documents = db.execute(
        'SELECT * FROM documents WHERE knowledge_base_id = ? ORDER BY upload_time DESC',
        (kb_id,)
    ).fetchall()
    
    return jsonify([dict(doc) for doc in documents])

@app.route('/api/knowledge-bases/<int:kb_id>/documents', methods=['POST'])
def upload_document(kb_id):
    """上传文档"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    filename = file.filename
    file_size = 0
    
    # 获取文件格式
    file_format = os.path.splitext(filename)[1].lower().lstrip('.')
    if not file_format:
        file_format = 'unknown'
    
    filepath = os.path.join(UPLOAD_FOLDER, f"{kb_id}_{datetime.now().timestamp()}_{filename}")
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO documents (knowledge_base_id, name, file_path, file_size, file_format, chunk_status, chunk_progress) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (kb_id, filename, filepath, file_size, file_format, 'not_chunked', 0)
    )
    db.commit()
    
    doc = db.execute('SELECT * FROM documents WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return jsonify(dict(doc))

@app.route('/api/documents/batch-chunk', methods=['POST'])
def batch_chunk():
    """批量分块"""
    data = request.json
    document_ids = data.get('document_ids', [])
    chunk_method = data.get('chunk_method')
    params = data.get('params', {})
    
    chunking_service = ChunkingService()
    results = []
    
    for doc_id in document_ids:
        db = None
        try:
            # 更新状态为分块中
            db = get_db()
            db.execute(
                'UPDATE documents SET chunk_status = ?, chunk_progress = ? WHERE id = ?',
                ('chunking', 0, doc_id)
            )
            db.commit()
            db.close()
            db = None
            
            # 执行分块，传入进度回调
            def progress_callback(progress):
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        db_progress = get_db()
                        db_progress.execute(
                            'UPDATE documents SET chunk_progress = ? WHERE id = ?',
                            (progress, doc_id)
                        )
                        db_progress.commit()
                        db_progress.close()
                        break  # 成功则退出循环
                    except sqlite3.OperationalError as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"更新进度失败（已重试{max_retries}次）: {e}")
                        else:
                            import time
                            time.sleep(0.1 * retry_count)  # 递增延迟
                    except Exception as e:
                        print(f"更新进度失败: {e}")
                        break
            
            result = chunking_service.chunk_document(doc_id, chunk_method, params, progress_callback)
            results.append({'document_id': doc_id, 'success': True, 'chunks': result})
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"分块失败: {error_msg}")
            print(traceback.format_exc())
            
            # 分块失败，恢复状态
            try:
                if db:
                    db.close()
                db_recover = get_db()
                db_recover.execute(
                    'UPDATE documents SET chunk_status = ?, chunk_progress = ? WHERE id = ?',
                    ('not_chunked', 0, doc_id)
                )
                db_recover.commit()
                db_recover.close()
            except Exception as db_error:
                print(f"恢复状态失败: {db_error}")
            
            results.append({'document_id': doc_id, 'success': False, 'error': error_msg})
    
    return jsonify(results)

@app.route('/api/documents/<int:doc_id>/progress', methods=['GET'])
def get_chunk_progress(doc_id):
    """获取文档分块进度"""
    db = get_db()
    doc = db.execute('SELECT chunk_status, chunk_progress FROM documents WHERE id = ?', (doc_id,)).fetchone()
    
    if doc:
        return jsonify({
            'status': doc['chunk_status'],
            'progress': doc['chunk_progress']
        })
    
    return jsonify({'error': '文档不存在'}), 404

@app.route('/api/documents/<int:doc_id>/chunks', methods=['GET'])
def get_chunks(doc_id):
    """获取文档的分块结果"""
    db = get_db()
    chunks = db.execute(
        'SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index',
        (doc_id,)
    ).fetchall()
    
    return jsonify([dict(chunk) for chunk in chunks])

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """删除文档"""
    db = get_db()
    doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
    
    if doc:
        try:
            # 删除文件
            if os.path.exists(doc['file_path']):
                try:
                    os.remove(doc['file_path'])
                except Exception as e:
                    print(f"删除文件失败: {e}")
            
            # 删除分块数据
            db.execute('DELETE FROM chunks WHERE document_id = ?', (doc_id,))
            
            # 删除文档记录
            db.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            db.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            import traceback
            print(f"删除文档失败: {e}")
            print(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'error': '文档不存在'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
