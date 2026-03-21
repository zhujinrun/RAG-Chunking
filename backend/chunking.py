import re
import json
import jieba.analyse
import chardet
import os
from database import get_db

# PDF解析库
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: pdfplumber未安装，PDF文件将无法解析")

class ChunkingService:
    def detect_encoding(self, file_path):
        """检测文件编码"""
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            
            # 如果检测到的编码是GB2312或GBK，统一使用GBK
            if encoding and encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
                encoding = 'gbk'
            # 如果检测失败或置信度太低，尝试常见编码
            elif not encoding or result['confidence'] < 0.7:
                # 尝试常见编码
                for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        raw_data.decode(enc)
                        encoding = enc
                        break
                    except:
                        continue
            
            return encoding or 'utf-8'
    
    def read_file_content(self, file_path):
        """读取文件内容，自动检测编码和文件类型"""
        # 检查文件扩展名
        _, ext = os.path.splitext(file_path.lower())
        
        # 如果是PDF文件
        if ext == '.pdf':
            return self.read_pdf_content(file_path)
        
        # 其他文本文件
        encoding = self.detect_encoding(file_path)
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # 如果还是失败，尝试使用errors='ignore'
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
    
    def read_pdf_content(self, file_path):
        """读取PDF文件内容"""
        if not PDF_SUPPORT:
            raise ValueError('PDF解析库未安装，请安装pdfplumber: pip install pdfplumber')
        
        try:
            text_content = []
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # 提取文本
                        page_text = page.extract_text()
                        
                        if page_text:
                            # 添加页码标记
                            text_content.append(f"\n--- 第 {page_num} 页 ---\n")
                            text_content.append(page_text)
                        
                        # 提取表格
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables, 1):
                                text_content.append(f"\n[表格 {page_num}-{table_idx}]\n")
                                # 将表格转换为文本格式
                                for row in table:
                                    if row:
                                        # 过滤None值
                                        row_text = ' | '.join([str(cell).strip() if cell else '' for cell in row])
                                        if row_text.strip():
                                            text_content.append(row_text)
                    except Exception as page_error:
                        print(f"处理第 {page_num} 页时出错: {page_error}")
                        text_content.append(f"\n--- 第 {page_num} 页解析失败 ---\n")
                        continue
            
            result = '\n'.join(text_content)
            
            # 如果提取的内容为空或太短，可能是扫描版PDF
            if len(result.strip()) < 100:
                raise ValueError('PDF内容提取失败，可能是扫描版PDF或加密PDF')
            
            return result
        
        except Exception as e:
            raise ValueError(f'PDF解析失败: {str(e)}')
    
    def chunk_document(self, document_id, method, params, progress_callback=None):
        """根据指定方法对文档进行分块"""
        from database import get_db
        import time
        
        # 获取文档信息 - 立即关闭连接
        db = get_db()
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (document_id,)).fetchone()
        db.close()
        
        if not doc:
            raise ValueError('文档不存在')
        
        # 报告进度：开始读取文件
        if progress_callback:
            progress_callback(10)
        
        # 读取文档内容（自动检测编码）
        try:
            content = self.read_file_content(doc['file_path'])
        except Exception as e:
            raise ValueError(f'读取文件失败: {str(e)}')
        
        # 报告进度：开始分块
        if progress_callback:
            progress_callback(30)
        
        # 根据方法选择分块策略
        try:
            if method == 'naive':
                chunks = self.naive_chunking(content, params)
            elif method == 'general':
                chunks = self.general_chunking(content, params)
            elif method == 'book':
                chunks = self.book_chunking(content, params)
            elif method == 'paper':
                chunks = self.paper_chunking(content, params)
            elif method == 'resume':
                chunks = self.resume_chunking(content, params)
            elif method == 'table':
                chunks = self.table_chunking(content, params)
            elif method == 'qa':
                chunks = self.qa_chunking(content, params)
            else:
                raise ValueError(f'不支持的分块方法: {method}')
        except Exception as e:
            raise ValueError(f'分块处理失败: {str(e)}')
        
        # 报告进度：分块完成，开始处理
        if progress_callback:
            progress_callback(50)
        
        # 提取关键词和生成问题的数量
        keyword_count = params.get('keyword_count', 5)
        question_count = params.get('question_count', 3)
        
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            raise ValueError('分块结果为空，请检查文档内容或选择其他分块方式')
        
        # 保存分块结果 - 使用短连接策略，每次操作后立即关闭
        # 先删除旧的chunks
        db = get_db()
        try:
            db.execute('DELETE FROM chunks WHERE document_id = ?', (document_id,))
            db.commit()
        finally:
            db.close()
        
        # 分批保存chunks，避免长时间持有连接
        batch_size = 5
        for batch_start in range(0, total_chunks, batch_size):
            batch_end = min(batch_start + batch_size, total_chunks)
            
            # 为每批数据创建新连接
            db = get_db()
            try:
                for idx in range(batch_start, batch_end):
                    chunk_data = chunks[idx]
                    try:
                        # 提取关键词
                        keywords = self.extract_keywords(chunk_data['content'], keyword_count)
                        # 生成问题
                        questions = self.generate_questions(chunk_data['content'], question_count)
                        
                        db.execute(
                            'INSERT INTO chunks (document_id, chunk_index, content, metadata, parent_chunk_id, keywords, questions) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (document_id, idx, chunk_data['content'], json.dumps(chunk_data.get('metadata', {})), 
                             chunk_data.get('parent_id'), json.dumps(keywords), json.dumps(questions))
                        )
                    except Exception as e:
                        print(f"处理第 {idx} 个chunk时出错: {e}")
                        continue
                
                # 提交当前批次
                db.commit()
            finally:
                db.close()
            
            # 报告进度：处理中
            if progress_callback and total_chunks > 0:
                progress = 50 + int((batch_end) / total_chunks * 40)
                progress_callback(progress)
            
            # 短暂休眠，让其他操作有机会执行
            time.sleep(0.01)
        
        # 更新文档状态和分块数量 - 使用新连接
        db = get_db()
        try:
            db.execute(
                'UPDATE documents SET chunk_status = ?, chunk_method = ?, chunk_count = ?, chunk_progress = ? WHERE id = ?',
                ('chunked', method, total_chunks, 100, document_id)
            )
            db.commit()
        finally:
            db.close()
        
        # 报告进度：完成
        if progress_callback:
            progress_callback(100)
        
        return total_chunks
    
    def extract_keywords(self, text, topK=5):
        """提取关键词"""
        try:
            # 限制文本长度，避免处理过长文本
            if len(text) > 5000:
                text = text[:5000]
            
            keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
            return keywords if keywords else []
        except Exception as e:
            print(f"关键词提取失败: {e}")
            # 如果jieba失败，使用简单的词频统计
            try:
                words = re.findall(r'[\u4e00-\u9fa5]+', text[:1000])
                word_freq = {}
                for word in words:
                    if len(word) >= 2:
                        word_freq[word] = word_freq.get(word, 0) + 1
                sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                return [word for word, freq in sorted_words[:topK]]
            except:
                return []
    
    def generate_questions(self, text, count=3):
        """生成问题（简化版）"""
        try:
            questions = []
            
            # 限制文本长度
            if len(text) > 2000:
                text = text[:2000]
            
            # 基于内容生成简单问题
            sentences = re.split(r'[。！？.!?]', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            for i, sentence in enumerate(sentences[:count]):
                # 简单的问题生成模板
                if '是' in sentence or '为' in sentence:
                    questions.append(f"关于这段内容，{sentence[:20]}...的具体情况是什么？")
                elif '如何' in sentence or '怎么' in sentence:
                    questions.append(f"{sentence[:30]}...？")
                else:
                    questions.append(f"这段内容中提到的{sentence[:15]}...是什么意思？")
                
                if len(questions) >= count:
                    break
            
            # 如果生成的问题不够，添加通用问题
            while len(questions) < count:
                questions.append(f"这段内容的主要观点是什么？")
            
            return questions[:count]
        except Exception as e:
            print(f"问题生成失败: {e}")
            return ["这段内容的主要观点是什么？"] * count
    
    def naive_chunking(self, content, params):
        """朴素分块 - 最简单的固定大小分块"""
        chunk_size = params.get('chunk_size', 500)
        overlap = params.get('overlap', 50)
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk_content = content[start:end]
            
            chunks.append({
                'content': chunk_content,
                'metadata': {'start': start, 'end': end, 'method': 'naive'}
            })
            
            start = end - overlap
        
        return chunks
    
    def general_chunking(self, content, params):
        """通用分块 - 智能识别段落和章节"""
        chunk_size = params.get('chunk_size', 1000)
        overlap = params.get('overlap', 100)
        
        # 按段落分割
        paragraphs = re.split(r'\n\n+', content)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            # 如果当前段落加入后超过限制
            if current_length + para_length > chunk_size and current_chunk:
                # 保存当前chunk
                chunks.append({
                    'content': '\n\n'.join(current_chunk),
                    'metadata': {'method': 'general', 'paragraphs': len(current_chunk)}
                })
                
                # 保留重叠部分
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-1]
                    current_chunk = [overlap_text, para]
                    current_length = len(overlap_text) + para_length
                else:
                    current_chunk = [para]
                    current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # 保存最后一个chunk
        if current_chunk:
            chunks.append({
                'content': '\n\n'.join(current_chunk),
                'metadata': {'method': 'general', 'paragraphs': len(current_chunk)}
            })
        
        return chunks
    
    def parent_child_chunking(self, content, params):
        """父子分块（已废弃，使用general代替）"""
        return self.general_chunking(content, params)
    
    def recursive_chunking(self, content, params):
        """递归分块（已废弃，使用general代替）"""
        return self.general_chunking(content, params)
    
    def semantic_chunking(self, content, params):
        """智能分块（已废弃，使用general代替）"""
        return self.general_chunking(content, params)
    
    def table_chunking(self, content, params):
        """表格分块（支持CSV和Markdown表格）"""
        chunks = []
        lines = content.split('\n')
        
        # 检测表格类型
        # 检查是否包含CSV格式（第一行有逗号）
        has_csv = False
        has_markdown_table = False
        
        for line in lines[:10]:  # 检查前10行
            if ',' in line and not line.startswith('#'):
                has_csv = True
                break
            if '|' in line:
                has_markdown_table = True
                break
        
        if has_csv:
            # CSV格式
            chunks = self._chunk_csv_table(lines)
        elif has_markdown_table:
            # Markdown格式
            chunks = self._chunk_markdown_table(lines)
        else:
            # 非表格内容，使用通用分块
            chunks = self.general_chunking(content, params)
        
        return chunks
    
    def _chunk_csv_table(self, lines):
        """处理CSV表格 - 使用键值对格式"""
        chunks = []
        
        if not lines:
            return chunks
        
        # 第一行是表头
        header_line = lines[0].strip()
        if not header_line:
            return chunks
        
        # 解析表头字段
        headers = [h.strip() for h in header_line.split(',')]
        
        # 处理每一行数据，转换为键值对格式
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            
            # 解析数据行
            values = [v.strip() for v in line.split(',')]
            
            # 确保字段数量匹配
            if len(values) != len(headers):
                # 如果字段数量不匹配，跳过或补齐
                if len(values) < len(headers):
                    values.extend([''] * (len(headers) - len(values)))
                else:
                    values = values[:len(headers)]
            
            # 构建键值对格式的内容
            kv_pairs = []
            for header, value in zip(headers, values):
                kv_pairs.append(f"{header}: {value}")
            
            chunk_content = '\n'.join(kv_pairs)
            
            chunks.append({
                'content': chunk_content,
                'metadata': {
                    'type': 'table',
                    'format': 'csv',
                    'row': i,
                    'field_count': len(headers)
                }
            })
        
        return chunks
    
    def _chunk_markdown_table(self, lines):
        """处理Markdown表格 - 使用键值对格式，支持标题和多个表格"""
        chunks = []
        
        in_table = False
        table_header = None
        table_rows = []
        current_title = None  # 当前表格的标题
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行
            if not line:
                # 如果在表格中遇到空行，表格结束
                if in_table and table_header and table_rows:
                    chunks.extend(self._convert_markdown_table_to_kv(table_header, table_rows, current_title))
                    table_header = None
                    table_rows = []
                    in_table = False
                i += 1
                continue
            
            # 检测Markdown标题
            if line.startswith('#'):
                # 保存之前的表格
                if table_header and table_rows:
                    chunks.extend(self._convert_markdown_table_to_kv(table_header, table_rows, current_title))
                    table_header = None
                    table_rows = []
                
                # 更新当前标题
                current_title = line.lstrip('#').strip()
                in_table = False
                i += 1
                continue
            
            # 检测表格行（必须包含|且不是分隔符行）
            if '|' in line:
                # 检查是否是分隔符行
                is_separator = all(c in '|-: \t' for c in line)
                
                if is_separator:
                    # 这是分隔符行，跳过
                    i += 1
                    continue
                
                if not in_table:
                    # 开始新表格，这是表头
                    in_table = True
                    table_header = line
                else:
                    # 表格数据行
                    table_rows.append(line)
            else:
                # 非表格行
                if in_table and table_header and table_rows:
                    # 表格结束，处理表格内容
                    chunks.extend(self._convert_markdown_table_to_kv(table_header, table_rows, current_title))
                    table_header = None
                    table_rows = []
                    in_table = False
            
            i += 1
        
        # 处理最后的表格
        if table_header and table_rows:
            chunks.extend(self._convert_markdown_table_to_kv(table_header, table_rows, current_title))
        
        return chunks
    
    def _convert_markdown_table_to_kv(self, header_line, data_rows, title=None):
        """将Markdown表格转换为键值对格式"""
        chunks = []
        
        # 解析表头 - 去掉首尾的空字符串
        header_parts = header_line.split('|')
        headers = [h.strip() for h in header_parts if h.strip()]
        
        # 处理每一行数据
        for row_idx, row_line in enumerate(data_rows):
            # 解析数据行 - 去掉首尾的空字符串
            value_parts = row_line.split('|')
            values = [v.strip() for v in value_parts if v.strip() or (v == '' and value_parts.index(v) > 0 and value_parts.index(v) < len(value_parts) - 1)]
            
            # 简化：直接取中间的值
            values = [v.strip() for v in value_parts[1:-1]] if len(value_parts) > 2 else []
            
            # 确保字段数量匹配
            if len(values) != len(headers):
                if len(values) < len(headers):
                    values.extend([''] * (len(headers) - len(values)))
                else:
                    values = values[:len(headers)]
            
            # 构建键值对格式的内容
            kv_pairs = []
            
            # 如果有标题，添加到内容开头
            if title:
                kv_pairs.append(f"表格: {title}")
                kv_pairs.append("")  # 空行分隔
            
            for header, value in zip(headers, values):
                kv_pairs.append(f"{header}: {value}")
            
            chunk_content = '\n'.join(kv_pairs)
            
            chunks.append({
                'content': chunk_content,
                'metadata': {
                    'type': 'table',
                    'format': 'markdown',
                    'row': row_idx + 1,
                    'title': title or '未命名表格'
                }
            })
        
        return chunks
    
    def qa_chunking(self, content, params):
        """问答分块"""
        qa_pattern = r'(?:问题?[:：]|Q[:：])\s*(.+?)\s*(?:答案?[:：]|A[:：])\s*(.+?)(?=(?:问题?[:：]|Q[:：])|$)'
        matches = re.findall(qa_pattern, content, re.DOTALL | re.IGNORECASE)
        
        chunks = []
        for question, answer in matches:
            chunks.append({
                'content': f"问题: {question.strip()}\n答案: {answer.strip()}",
                'metadata': {'type': 'qa', 'question': question.strip(), 'answer': answer.strip()}
            })
        
        if not chunks:
            return self.general_chunking(content, params)
        
        return chunks

    
    def book_chunking(self, content, params):
        """书籍分块 - 识别章节结构"""
        chunks = []
        lines = content.split('\n')
        
        current_chapter = None
        current_section = []
        chapter_pattern = re.compile(r'^(第[一二三四五六七八九十百千\d]+[章节部篇]|Chapter\s+\d+|CHAPTER\s+\d+)', re.IGNORECASE)
        
        max_chunk_size = params.get('max_size', 3000)  # 最大chunk大小
        
        for line in lines:
            line = line.strip()
            
            # 检测章节标题
            is_chapter = chapter_pattern.match(line)
            is_short_title = len(line) < 50 and line and not line.endswith(('。', '！', '？', '.', '!', '?', '，', ','))
            
            if is_chapter or is_short_title:
                # 保存上一章节
                if current_section:
                    content_text = '\n'.join(current_section)
                    if len(content_text) > 100:
                        chunks.append({
                            'content': content_text,
                            'metadata': {'type': 'chapter', 'title': current_chapter or '未命名章节'}
                        })
                
                current_chapter = line
                current_section = [line]
            else:
                if line:
                    current_section.append(line)
                
                # 如果当前章节过长，进行分段
                current_length = sum(len(l) for l in current_section)
                if current_length > max_chunk_size:
                    content_text = '\n'.join(current_section)
                    chunks.append({
                        'content': content_text,
                        'metadata': {'type': 'chapter', 'title': current_chapter or '未命名章节'}
                    })
                    current_section = []
        
        # 保存最后一章
        if current_section:
            content_text = '\n'.join(current_section)
            if len(content_text) > 100:
                chunks.append({
                    'content': content_text,
                    'metadata': {'type': 'chapter', 'title': current_chapter or '未命名章节'}
                })
        
        # 如果没有识别到章节，使用通用分块
        if not chunks:
            print("书籍分块未识别到章节，使用通用分块")
            return self.general_chunking(content, params)
        
        print(f"书籍分块完成，共 {len(chunks)} 个chunk")
        return chunks
    
    def paper_chunking(self, content, params):
        """论文分块 - 识别论文结构"""
        chunks = []
        lines = content.split('\n')
        
        # 论文常见章节
        section_keywords = [
            'abstract', '摘要', 'introduction', '引言', '绪论',
            'related work', '相关工作', 'methodology', '方法', '方法论',
            'experiment', '实验', 'result', '结果', 'discussion', '讨论',
            'conclusion', '结论', 'reference', '参考文献', 'acknowledgment', '致谢'
        ]
        
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # 检测章节标题
            is_section = False
            for keyword in section_keywords:
                if keyword in line_lower and len(line.strip()) < 100:
                    is_section = True
                    break
            
            if is_section:
                # 保存上一节
                if current_content:
                    content_text = '\n'.join(current_content)
                    if len(content_text) > 50:
                        chunks.append({
                            'content': content_text,
                            'metadata': {'type': 'paper_section', 'section': current_section or '未命名'}
                        })
                
                current_section = line.strip()
                current_content = [line.strip()]
            else:
                if line.strip():
                    current_content.append(line.strip())
        
        # 保存最后一节
        if current_content:
            content_text = '\n'.join(current_content)
            if len(content_text) > 50:
                chunks.append({
                    'content': content_text,
                    'metadata': {'type': 'paper_section', 'section': current_section or '未命名'}
                })
        
        return chunks if chunks else self.general_chunking(content, params)
    
    def resume_chunking(self, content, params):
        """简历分块 - 识别简历模块"""
        chunks = []
        lines = content.split('\n')
        
        # 简历常见模块
        section_keywords = [
            '个人信息', '基本信息', 'personal', 'contact',
            '教育背景', '教育经历', 'education',
            '工作经历', '工作经验', 'experience', 'employment',
            '项目经验', '项目经历', 'project',
            '技能', '专业技能', 'skill',
            '证书', '资格证书', 'certificate',
            '自我评价', 'summary', 'objective'
        ]
        
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # 检测模块标题
            is_section = False
            for keyword in section_keywords:
                if keyword in line_lower and len(line.strip()) < 50:
                    is_section = True
                    break
            
            if is_section:
                # 保存上一模块
                if current_content:
                    content_text = '\n'.join(current_content)
                    if len(content_text) > 20:
                        chunks.append({
                            'content': content_text,
                            'metadata': {'type': 'resume_section', 'section': current_section or '未命名'}
                        })
                
                current_section = line.strip()
                current_content = [line.strip()]
            else:
                if line.strip():
                    current_content.append(line.strip())
        
        # 保存最后一模块
        if current_content:
            content_text = '\n'.join(current_content)
            if len(content_text) > 20:
                chunks.append({
                    'content': content_text,
                    'metadata': {'type': 'resume_section', 'section': current_section or '未命名'}
                })
        
        return chunks if chunks else self.general_chunking(content, params)
