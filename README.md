# 知识库文档管理与分块系统

基于需求文档实现的完整知识库管理系统，支持多种智能分块策略，参考RAGFlow的分块方法设计。

## 技术栈

- 前端：Vue 3 + Vite + Element Plus
- 后端：Python Flask
- 数据库：SQLite
- 中文分词：jieba
- 编码检测：chardet
- PDF解析：pdfplumber、PyPDF2

## 项目结构

```
├── frontend/              # 前端项目
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   │   ├── KnowledgeBaseList.vue    # 知识库列表
│   │   │   └── DocumentManagement.vue   # 文档管理
│   │   ├── router/       # 路由配置
│   │   ├── App.vue       # 根组件
│   │   └── main.js       # 入口文件
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/              # 后端项目
│   ├── app.py           # Flask应用主文件
│   ├── database.py      # 数据库初始化和操作
│   ├── chunking.py      # 分块策略实现
│   ├── migrate_db.py    # 数据库迁移脚本
│   ├── requirements.txt # Python依赖
│   ├── setup.bat        # Windows环境配置脚本
│   ├── setup.sh         # Linux/Mac环境配置脚本
│   ├── run.bat          # Windows启动脚本
│   └── run.sh           # Linux/Mac启动脚本
├── sample-data/         # 测试数据
│   ├── naive_test.txt
│   ├── general_test.txt
│   ├── book_test.txt
│   ├── paper_test.txt
│   ├── resume_test.txt
│   ├── table.csv
│   ├── markdown_table_test.md
│   ├── qa_test_part1.txt
│   ├── qa_test_part2.txt
│   └── README.md        # 测试文件说明
└── README.md
```

## 功能特性

### 1. 知识库管理
- 创建知识库（名称、描述）
- 知识库列表展示（卡片式布局）
- 删除知识库（级联删除所有文档和分块）
- 进入知识库查看文档

### 2. 文档管理
- 文档上传（支持多文件、自动编码检测）
- 支持多种文件格式：TXT、MD、CSV、PDF
- 文档列表展示（名称、大小、上传时间、分块状态、分块数量）
- 批量选择操作
- 单个/批量删除文档
- 返回知识库列表

### 3. 七种分块策略（参考RAGFlow）

#### 朴素分块 (Naive Chunking)
- 最简单的固定大小分块
- 按固定token数切分，支持重叠区域
- 适用于简单文档、快速原型开发

#### 通用分块 (General Chunking)
- 智能识别段落、章节等结构
- 按语义单元切分，保持段落完整性
- 适用于结构化文档、技术文档

#### 书籍分块 (Book Chunking)
- 识别章节标题（第X章、Chapter X等）
- 按书籍结构进行分块
- 适用于书籍、长篇文档、学术论文

#### 论文分块 (Paper Chunking)
- 识别论文标准结构（摘要、引言、方法、结论等）
- 按论文章节分块
- 适用于学术论文、研究报告

#### 简历分块 (Resume Chunking)
- 识别简历模块（教育背景、工作经历、技能等）
- 按模块分块
- 适用于简历、个人档案

#### 表格分块 (Table Chunking)
- 支持CSV和Markdown表格
- 转换为键值对格式（字段名: 值）
- 每行数据独立成块，包含完整字段信息
- 适用于数据报告、统计表格

#### 问答分块 (Q&A Chunking)
- 识别问题-答案对结构
- 每个Q&A作为独立单元
- 适用于FAQ文档、问答知识库

### 4. 智能特性
- **自动编码检测**：支持UTF-8、GBK、GB2312等多种编码
- **PDF解析**：使用pdfplumber提取PDF文本和表格内容
- **关键词提取**：使用jieba自动提取每个chunk的关键词（可配置数量）
- **问题生成**：为每个chunk自动生成相关问题（可配置数量）
- **分块参数配置**：支持自定义关键词数量和问题数量
- **分块方式说明**：提供详细的分块方式介绍和使用建议

## 安装和运行

### 后端启动

#### Windows系统

```bash
cd backend
# 首次运行：配置环境（创建虚拟环境并安装依赖）
setup.bat

# 后续运行：直接启动服务
run.bat
```

#### Linux/Mac系统

```bash
cd backend
# 首次运行：配置环境（创建虚拟环境并安装依赖）
chmod +x setup.sh run.sh
./setup.sh

# 后续运行：直接启动服务
./run.sh
```

后端将运行在 http://localhost:5000

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端将运行在 http://localhost:3000

## API 接口

### 知识库相关
- `GET /api/knowledge-bases` - 获取所有知识库列表
- `POST /api/knowledge-bases` - 创建知识库
- `DELETE /api/knowledge-bases/<kb_id>` - 删除知识库（级联删除）
- `GET /api/knowledge-bases/<kb_id>/documents` - 获取文档列表

### 文档相关
- `POST /api/knowledge-bases/<kb_id>/documents` - 上传文档
- `DELETE /api/documents/<doc_id>` - 删除文档
- `POST /api/documents/batch-chunk` - 批量分块
- `GET /api/documents/<doc_id>/chunks` - 获取分块结果

## 数据库设计

### knowledge_bases 表
- id: 主键
- name: 知识库名称
- description: 描述
- created_at: 创建时间

### documents 表
- id: 主键
- knowledge_base_id: 所属知识库
- name: 文档名称
- file_path: 文件路径
- file_size: 文件大小
- upload_time: 上传时间
- chunk_status: 分块状态（not_chunked/chunked/chunking）
- chunk_method: 分块方式
- chunk_count: 分块数量

### chunks 表
- id: 主键
- document_id: 所属文档
- chunk_index: 分块序号
- content: 分块内容
- metadata: 元数据（JSON，包含type、format等）
- parent_chunk_id: 父分块ID（预留字段）
- keywords: 关键词（JSON数组）
- questions: 生成的问题（JSON数组）
- created_at: 创建时间

## 使用流程

### 基本流程
1. 访问 http://localhost:3000 进入知识库列表
2. 点击"创建知识库"，输入名称和描述
3. 自动跳转到文档管理页面
4. 点击"上传文档"，选择要上传的文件
5. 在"分块方式"列的下拉框中为每个文档选择合适的分块方式
6. 点击"执行分块"按钮（单个文档）或勾选多个文档后点击"批量分块"
7. 在弹出的对话框中设置关键词提取数量和生成问题数量
8. 确认后开始分块
9. 分块完成后，点击"查看"按钮查看分块结果

### 分块方式选择建议
- 简单文本 → 朴素分块或通用分块
- 书籍、教程 → 书籍分块
- 学术论文 → 论文分块
- 简历 → 简历分块
- 表格数据 → 表格分块
- FAQ文档 → 问答分块

### 测试数据
在 `sample-data/` 目录下提供了完整的测试文件，每种分块方式都有对应的测试文档。详见 `sample-data/README.md`。

## 注意事项

- 上传的文件会保存在 `backend/uploads/` 目录
- 数据库文件为 `backend/knowledge_base.db`
- 确保后端先启动，前端才能正常访问API
- 首次运行需要执行 setup 脚本配置环境
- 支持多种文件编码，系统会自动检测
- 表格分块会将每行数据转换为键值对格式
- 关键词提取和问题生成基于jieba分词

## 数据库迁移

如果数据库结构有更新，可以使用迁移脚本：

Windows:
```bash
cd backend
migrate.bat
```

Linux/Mac:
```bash
cd backend
chmod +x migrate.sh
./migrate.sh
```

或者删除数据库重新初始化（会丢失所有数据）：
```bash
cd backend
rm knowledge_base.db  # Linux/Mac
del knowledge_base.db  # Windows
python -c "from database import init_db; init_db()"
```

## 技术亮点

1. **智能编码检测**：使用chardet自动检测文件编码，支持UTF-8、GBK等多种编码
2. **PDF文档解析**：使用pdfplumber提取PDF文本和表格，保持内容完整性
3. **键值对表格分块**：参考RAGFlow，将表格转换为易于理解的键值对格式
4. **自动关键词提取**：使用jieba分词自动提取每个chunk的关键词
5. **智能问题生成**：为每个chunk生成相关问题，便于问答系统使用
6. **多种分块策略**：提供7种分块方式，适应不同类型的文档
7. **虚拟环境隔离**：后端使用独立虚拟环境，避免依赖冲突
8. **数据库迁移**：支持平滑的数据库结构升级

## 开发计划

- [x] 支持PDF文档格式
- [ ] 支持Word（DOCX）文档格式
- [ ] 支持更多文档格式（PPT、Excel等）
- [ ] 增加向量化和检索功能
- [ ] 支持自定义分块参数
- [ ] 添加分块效果评估指标
- [ ] 支持混合分块策略
- [ ] 增加分块结果的人工审核和调整功能
- [ ] 集成大语言模型进行问答

## 许可证

MIT License
