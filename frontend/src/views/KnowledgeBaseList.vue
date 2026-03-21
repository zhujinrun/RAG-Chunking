<template>
  <div class="kb-list-container">
    <el-card class="header-card">
      <h1>知识库文档管理与分块系统</h1>
      <el-button type="primary" @click="showCreateDialog = true" :icon="Plus">创建知识库</el-button>
    </el-card>

    <el-card v-loading="loading">
      <div v-if="knowledgeBases.length === 0" class="empty-state">
        <el-empty description="暂无知识库，点击上方按钮创建">
          <el-button type="primary" @click="showCreateDialog = true">创建知识库</el-button>
        </el-empty>
      </div>
      <div v-else class="kb-grid">
        <el-card 
          v-for="kb in knowledgeBases" 
          :key="kb.id"
          class="kb-card"
          shadow="hover"
          @click="enterKnowledgeBase(kb.id)"
        >
          <template #header>
            <div class="kb-card-header">
              <span class="kb-name">{{ kb.name }}</span>
              <el-button 
                link 
                type="danger" 
                :icon="Delete"
                @click.stop="deleteKB(kb)"
              />
            </div>
          </template>
          <div class="kb-card-body">
            <p class="kb-description">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-meta">
              <el-tag size="small" type="info">
                <el-icon><Calendar /></el-icon>
                {{ formatTime(kb.created_at) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="创建知识库" width="500px">
      <el-form :model="newKB" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newKB.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newKB.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createKnowledgeBase">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Delete, Calendar } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const showCreateDialog = ref(false)
const newKB = ref({ name: '', description: '' })
const knowledgeBases = ref([])
const loading = ref(false)

const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/knowledge-bases')
    knowledgeBases.value = response.data
  } catch (error) {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

const createKnowledgeBase = async () => {
  if (!newKB.value.name) {
    ElMessage.warning('请输入知识库名称')
    return
  }

  try {
    const response = await axios.post('/api/knowledge-bases', newKB.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    newKB.value = { name: '', description: '' }
    router.push(`/kb/${response.data.id}/documents`)
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const enterKnowledgeBase = (id) => {
  router.push(`/kb/${id}/documents`)
}

const deleteKB = async (kb) => {
  try {
    await ElMessageBox.confirm(`确定要删除知识库"${kb.name}"吗？这将删除所有相关文档和分块数据。`, '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`/api/knowledge-bases/${kb.id}`)
    ElMessage.success('删除成功')
    loadKnowledgeBases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const formatTime = (time) => {
  return new Date(time).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.kb-list-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-card h1 {
  margin-bottom: 20px;
  font-size: 24px;
  color: #303133;
}

.empty-state {
  padding: 40px 0;
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.kb-card {
  cursor: pointer;
  transition: all 0.3s;
}

.kb-card:hover {
  transform: translateY(-4px);
}

.kb-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kb-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.kb-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kb-description {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  min-height: 44px;
  margin: 0;
}

.kb-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-meta .el-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
