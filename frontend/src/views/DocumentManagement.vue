<template>
  <div class="doc-management">
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-button 
            :icon="ArrowLeft" 
            @click="backToList"
            circle
          />
          <h2>文档管理</h2>
        </div>
        <div class="actions">
          <el-button 
            type="info" 
            :icon="QuestionFilled"
            @click="showMethodInfoDialog = true"
          >
            分块方式说明
          </el-button>
          <el-upload
            :action="`/api/knowledge-bases/${kbId}/documents`"
            :show-file-list="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            multiple
          >
            <el-button type="primary" :icon="Upload">上传文档</el-button>
          </el-upload>
          <el-button 
            type="success" 
            :icon="Operation"
            :disabled="selectedDocs.length === 0"
            @click="executeBatchChunking"
            :loading="chunking"
          >
            批量分块 ({{ selectedDocs.length }})
          </el-button>
          <el-button 
            type="danger" 
            :icon="Delete"
            :disabled="selectedDocs.length === 0"
            @click="batchDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card>
      <el-table 
        :data="documents" 
        @selection-change="handleSelectionChange"
        v-loading="loading"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="文档名称" min-width="250">
          <template #default="{ row }">
            <div class="doc-name-cell">
              <span class="doc-name">{{ row.name }}</span>
              <el-tag 
                :type="getFormatType(row.file_format)" 
                size="small"
                class="format-tag"
              >
                {{ (row.file_format || 'txt').toUpperCase() }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_status" label="分块状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.chunk_status)">
              {{ getStatusText(row.chunk_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数量" width="100">
          <template #default="{ row }">
            {{ row.chunk_count || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="分块方式" width="250">
          <template #default="{ row }">
            <div v-if="row.chunk_status === 'not_chunked'">
              <el-select 
                v-model="row.selected_method" 
                placeholder="选择分块方式"
                size="small"
                style="width: 100%"
              >
                <el-option
                  v-for="method in chunkMethods"
                  :key="method.value"
                  :label="method.name"
                  :value="method.value"
                />
              </el-select>
            </div>
            <div v-else-if="row.chunk_status === 'chunking'" class="chunking-status">
              <el-progress 
                :percentage="row.chunk_progress || 0" 
                :stroke-width="6"
                :show-text="true"
              />
              <span class="progress-text">{{ getMethodText(row.chunk_method) }} - 处理中...</span>
            </div>
            <span v-else>{{ getMethodText(row.chunk_method) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.chunk_status === 'not_chunked'"
              link 
              type="success" 
              @click="executeChunkingSingle(row)"
              :disabled="!row.selected_method"
            >
              执行分块
            </el-button>
            <el-button 
              v-else-if="row.chunk_status === 'chunked'"
              link 
              type="primary" 
              @click="viewChunks(row)"
            >
              查看
            </el-button>
            <el-button 
              v-else-if="row.chunk_status === 'chunking'"
              link 
              type="info"
              disabled
            >
              处理中
            </el-button>
            <el-button link type="danger" @click="deleteDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>



    <!-- 分块参数设置对话框 -->
    <el-dialog 
      v-model="showParamsDialog" 
      :title="currentDoc ? '设置分块参数' : '批量分块参数设置'" 
      width="500px"
    >
      <el-form :model="chunkParams" label-width="140px">
        <el-form-item label="关键词提取数量">
          <el-input-number 
            v-model="chunkParams.keyword_count" 
            :min="1" 
            :max="20" 
            :step="1"
          />
          <div class="form-tip">每个分块提取的关键词数量</div>
        </el-form-item>
        <el-form-item label="生成问题数量">
          <el-input-number 
            v-model="chunkParams.question_count" 
            :min="1" 
            :max="10" 
            :step="1"
          />
          <div class="form-tip">为每个分块生成的问题数量</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showParamsDialog = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="currentDoc ? confirmChunkingSingle() : confirmBatchChunking()"
          :loading="chunking"
        >
          确定分块
        </el-button>
      </template>
    </el-dialog>

    <!-- 分块方式说明对话框 -->
    <el-dialog v-model="showMethodInfoDialog" title="分块方式说明" width="900px">
      <div class="method-info-container">
        <el-card 
          v-for="method in chunkMethods" 
          :key="method.value"
          class="method-info-card"
          shadow="hover"
        >
          <template #header>
            <div class="method-header">
              <span class="method-name">{{ method.name }}</span>
              <el-tag type="primary" size="small">{{ method.value }}</el-tag>
            </div>
          </template>
          <div class="method-info-content">
            <div class="info-item">
              <span class="info-label">适用场景：</span>
              <span class="info-text scenario-text">{{ method.scenario }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">说明：</span>
              <span class="info-text">{{ method.description }}</span>
            </div>
            <div class="info-item pros-item">
              <span class="info-label">优点：</span>
              <span class="info-text">{{ method.pros }}</span>
            </div>
            <div class="info-item cons-item">
              <span class="info-label">缺点：</span>
              <span class="info-text">{{ method.cons }}</span>
            </div>
          </div>
        </el-card>
      </div>
      <template #footer>
        <el-button type="primary" @click="showMethodInfoDialog = false">知道了</el-button>
      </template>
    </el-dialog>

    <!-- 查看分块结果对话框 -->
    <el-dialog v-model="showChunksDialog" title="分块结果" width="1200px">
      <el-table :data="chunks" max-height="500">
        <el-table-column prop="chunk_index" label="序号" width="80" />
        <el-table-column prop="content" label="内容" min-width="300">
          <template #default="{ row }">
            <div class="chunk-content">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="关键词" width="200">
          <template #default="{ row }">
            <div v-if="row.keywords">
              <el-tag 
                v-for="(keyword, idx) in JSON.parse(row.keywords)" 
                :key="idx"
                size="small"
                style="margin: 2px"
              >
                {{ keyword }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="生成问题" width="300">
          <template #default="{ row }">
            <div v-if="row.questions" class="questions-list">
              <div 
                v-for="(question, idx) in JSON.parse(row.questions)" 
                :key="idx"
                class="question-item"
              >
                {{ idx + 1 }}. {{ question }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="元数据" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.metadata">{{ JSON.parse(row.metadata).type || '通用' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Upload, Operation, Delete, QuestionFilled, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const kbId = ref(route.params.id)

const documents = ref([])
const selectedDocs = ref([])
const loading = ref(false)
const showChunksDialog = ref(false)
const showMethodInfoDialog = ref(false)
const showParamsDialog = ref(false)
const chunking = ref(false)
const chunks = ref([])
const currentDoc = ref(null)
const chunkParams = ref({
  keyword_count: 5,
  question_count: 3
})

const chunkMethods = [
  {
    value: 'naive',
    name: '朴素分块',
    scenario: '适用场景：简单文档、通用文本',
    description: '按固定token数切分，支持重叠区域，最简单快速的分块方式',
    pros: '实现简单，处理速度快，适用于大多数文本场景',
    cons: '可能在句子或段落中间切断，不考虑文档的语义结构'
  },
  {
    value: 'general',
    name: '通用分块',
    scenario: '适用场景：结构化文档、技术文档',
    description: '智能识别段落、章节等结构，按语义单元切分',
    pros: '保持段落完整性，适合有明确结构的文档',
    cons: '对文档格式有一定要求'
  },
  {
    value: 'book',
    name: '书籍分块',
    scenario: '适用场景：书籍、长篇文档、学术论文',
    description: '识别章节、标题层级，按书籍结构进行分块',
    pros: '保留文档层级结构，适合长文档和书籍',
    cons: '需要明确的章节标记'
  },
  {
    value: 'paper',
    name: '论文分块',
    scenario: '适用场景：学术论文、研究报告',
    description: '识别摘要、引言、方法、结论等论文结构',
    pros: '针对论文结构优化，保留学术文档的逻辑性',
    cons: '仅适用于标准论文格式'
  },
  {
    value: 'resume',
    name: '简历分块',
    scenario: '适用场景：简历、个人档案',
    description: '识别教育经历、工作经验、技能等简历模块',
    pros: '针对简历结构优化，便于信息提取',
    cons: '仅适用于简历类文档'
  },
  {
    value: 'table',
    name: '表格分块',
    scenario: '适用场景：包含大量表格的文档',
    description: '识别并保留表格结构，转换为键值对格式',
    pros: '保持表格数据的完整性，便于结构化数据检索',
    cons: '需要准确的表格识别能力'
  },
  {
    value: 'qa',
    name: '问答分块',
    scenario: '适用场景：FAQ文档、问答知识库',
    description: '识别问题-答案对结构',
    pros: '天然适配问答场景，检索准确度高',
    cons: '仅适用于问答格式的内容'
  }
]

const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/knowledge-bases/${kbId.value}/documents`)
    documents.value = response.data.map(doc => ({
      ...doc,
      selected_method: null // 为每个文档添加选择的分块方式字段
    }))
    
    // 如果有正在分块的文档，启动轮询
    const chunkingDocs = documents.value.filter(doc => doc.chunk_status === 'chunking')
    if (chunkingDocs.length > 0) {
      startProgressPolling(chunkingDocs.map(d => d.id))
    }
  } catch (error) {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

let progressPollingTimer = null

const startProgressPolling = (docIds) => {
  // 清除之前的定时器
  if (progressPollingTimer) {
    clearInterval(progressPollingTimer)
  }
  
  // 每秒轮询一次进度
  progressPollingTimer = setInterval(async () => {
    let allCompleted = true
    
    for (const docId of docIds) {
      try {
        const response = await axios.get(`/api/documents/${docId}/progress`)
        const doc = documents.value.find(d => d.id === docId)
        
        if (doc) {
          doc.chunk_status = response.data.status
          doc.chunk_progress = response.data.progress
          
          if (response.data.status === 'chunking') {
            allCompleted = false
          }
        }
      } catch (error) {
        console.error('获取进度失败:', error)
      }
    }
    
    // 如果所有文档都完成了，停止轮询并刷新列表
    if (allCompleted) {
      clearInterval(progressPollingTimer)
      progressPollingTimer = null
      loadDocuments()
    }
  }, 1000)
}

const handleSelectionChange = (selection) => {
  selectedDocs.value = selection
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  loadDocuments()
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const executeChunkingSingle = async (doc) => {
  if (!doc.selected_method) {
    ElMessage.warning('请先选择分块方式')
    return
  }

  currentDoc.value = doc
  showParamsDialog.value = true
}

const confirmChunkingSingle = async () => {
  chunking.value = true
  try {
    // 先更新状态为分块中
    currentDoc.value.chunk_status = 'chunking'
    currentDoc.value.chunk_progress = 0
    
    const response = await axios.post('/api/documents/batch-chunk', {
      document_ids: [currentDoc.value.id],
      chunk_method: currentDoc.value.selected_method,
      params: chunkParams.value
    })
    
    showParamsDialog.value = false
    
    if (response.data[0].success) {
      // 启动进度轮询
      startProgressPolling([currentDoc.value.id])
      ElMessage.success('分块任务已启动')
    } else {
      ElMessage.error(`分块失败: ${response.data[0].error}`)
      // 恢复状态
      currentDoc.value.chunk_status = 'not_chunked'
      currentDoc.value.chunk_progress = 0
    }
  } catch (error) {
    console.error('分块失败:', error)
    ElMessage.error('分块失败: ' + (error.response?.data?.error || error.message))
    // 恢复状态
    currentDoc.value.chunk_status = 'not_chunked'
    currentDoc.value.chunk_progress = 0
  } finally {
    chunking.value = false
  }
}

const executeBatchChunking = async () => {
  // 筛选出未分块的选中文档
  const notChunkedDocs = selectedDocs.value.filter(doc => doc.chunk_status === 'not_chunked')
  
  if (notChunkedDocs.length === 0) {
    ElMessage.warning('没有可分块的文档')
    return
  }

  // 检查是否所有文档都选择了分块方式
  const docsWithoutMethod = notChunkedDocs.filter(doc => !doc.selected_method)
  if (docsWithoutMethod.length > 0) {
    ElMessage.warning(`有 ${docsWithoutMethod.length} 个文档未选择分块方式，请先选择分块方式`)
    return
  }

  currentDoc.value = null
  showParamsDialog.value = true
}

const confirmBatchChunking = async () => {
  const notChunkedDocs = selectedDocs.value.filter(doc => doc.chunk_status === 'not_chunked')
  
  chunking.value = true
  try {
    // 先更新所有文档状态为分块中
    notChunkedDocs.forEach(doc => {
      doc.chunk_status = 'chunking'
      doc.chunk_progress = 0
    })
    
    // 按照每个文档选择的分块方式进行分块
    const results = []
    for (const doc of notChunkedDocs) {
      try {
        const response = await axios.post('/api/documents/batch-chunk', {
          document_ids: [doc.id],
          chunk_method: doc.selected_method,
          params: chunkParams.value
        })
        results.push(...response.data)
      } catch (error) {
        console.error(`文档 ${doc.name} 分块失败:`, error)
        results.push({
          document_id: doc.id,
          success: false,
          error: error.message
        })
      }
    }
    
    showParamsDialog.value = false
    
    // 启动进度轮询
    const successDocs = results.filter(r => r.success).map(r => r.document_id)
    if (successDocs.length > 0) {
      startProgressPolling(successDocs)
    }
    
    const successCount = results.filter(r => r.success).length
    const failCount = results.length - successCount
    
    if (failCount === 0) {
      ElMessage.success(`已启动 ${successCount} 个文档的分块任务`)
    } else {
      ElMessage.warning(`已启动 ${successCount} 个文档的分块任务，${failCount} 个失败`)
      // 刷新失败的文档状态
      setTimeout(() => loadDocuments(), 1000)
    }
  } catch (error) {
    console.error('批量分块错误:', error)
    ElMessage.error('批量分块失败')
    loadDocuments()
  } finally {
    chunking.value = false
  }
}

const viewChunks = async (doc) => {
  try {
    const response = await axios.get(`/api/documents/${doc.id}/chunks`)
    chunks.value = response.data
    showChunksDialog.value = true
  } catch (error) {
    ElMessage.error('加载分块结果失败')
  }
}



const deleteDoc = async (doc) => {
  try {
    await ElMessageBox.confirm('确定要删除这个文档吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    try {
      await axios.delete(`/api/documents/${doc.id}`)
      ElMessage.success('删除成功')
      loadDocuments()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败: ' + (error.response?.data?.error || error.message))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除操作错误:', error)
    }
  }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedDocs.value.length} 个文档吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    let successCount = 0
    let failCount = 0
    
    for (const doc of selectedDocs.value) {
      try {
        await axios.delete(`/api/documents/${doc.id}`)
        successCount++
      } catch (error) {
        console.error(`删除文档 ${doc.name} 失败:`, error)
        failCount++
      }
    }
    
    if (failCount === 0) {
      ElMessage.success(`成功删除 ${successCount} 个文档`)
    } else {
      ElMessage.warning(`成功删除 ${successCount} 个文档，失败 ${failCount} 个`)
    }
    
    loadDocuments()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除错误:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}

const backToList = () => {
  router.push('/')
}

const formatSize = (size) => {
  if (!size) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
  return (size / 1024 / 1024).toFixed(2) + ' MB'
}

const getStatusType = (status) => {
  const map = {
    'not_chunked': 'info',
    'chunked': 'success',
    'chunking': 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'not_chunked': '未分块',
    'chunked': '已分块',
    'chunking': '分块中'
  }
  return map[status] || status
}

const getMethodText = (method) => {
  if (!method) return '-'
  const found = chunkMethods.find(m => m.value === method)
  return found ? found.name : method
}

const getFormatType = (format) => {
  const typeMap = {
    'pdf': 'danger',
    'txt': 'info',
    'md': 'success',
    'csv': 'warning',
    'doc': 'primary',
    'docx': 'primary',
    'xls': 'warning',
    'xlsx': 'warning'
  }
  return typeMap[format?.toLowerCase()] || 'info'
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.doc-management {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 15px;
}

.title-section h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.actions {
  display: flex;
  gap: 10px;
}

.chunk-content {
  max-height: 100px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.5;
}

.method-info-container {
  max-height: 600px;
  overflow-y: auto;
  padding: 10px;
}

.method-info-card {
  margin-bottom: 20px;
}

.method-info-card:last-child {
  margin-bottom: 0;
}

.method-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.method-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.method-info-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  line-height: 1.6;
}

.info-label {
  font-weight: 600;
  color: #606266;
  min-width: 90px;
  flex-shrink: 0;
}

.info-text {
  color: #606266;
  flex: 1;
}

.scenario-text {
  color: #409eff;
  font-weight: 500;
}

.pros-item .info-text {
  color: #67c23a;
}

.cons-item .info-text {
  color: #e6a23c;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.question-item {
  font-size: 12px;
  line-height: 1.4;
  color: #606266;
}

.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.doc-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.format-tag {
  flex-shrink: 0;
  font-weight: 600;
}

.chunking-status {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.progress-text {
  font-size: 12px;
  color: #606266;
}
</style>
