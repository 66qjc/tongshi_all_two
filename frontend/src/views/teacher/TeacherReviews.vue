<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAllProjects, approveProject, rejectProject } from '@/api/teacher'
import type { Project } from '@/api/project'

const projects = ref<Project[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    projects.value = await getAllProjects()
  } finally {
    loading.value = false
  }
})

const drawerVisible = ref(false)
const selectedProject = ref<Project | null>(null)
const rejectReason = ref('')

const statusMap: Record<string, { label: string; type: string }> = {
  pending: { label: '待审', type: 'warning' },
  approved: { label: '通过', type: 'success' },
  rejected: { label: '驳回', type: 'danger' },
}

function openDetail(p: Project) {
  selectedProject.value = p
  rejectReason.value = ''
  drawerVisible.value = true
}

async function handleApprove() {
  if (!selectedProject.value) return
  try {
    await approveProject(selectedProject.value.id)
    selectedProject.value.status = 'approved'
    drawerVisible.value = false
    ElMessage.success('已通过')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleReject() {
  if (!selectedProject.value) return
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回理由')
    return
  }
  try {
    await rejectProject(selectedProject.value.id, rejectReason.value.trim())
    selectedProject.value.status = 'rejected'
    selectedProject.value.reject_reason = rejectReason.value.trim()
    drawerVisible.value = false
    ElMessage.success('已驳回')
  } catch {
    ElMessage.error('操作失败')
  }
}

function handleBatchDownload() {
  const token = localStorage.getItem('auth_token')
  const url = `/api/teacher/projects/batch-download?token=${encodeURIComponent(token || '')}`
  window.open(url, '_blank')
}
</script>

<template>
  <div class="reviews-page">
    <div class="page-header">
      <h1>作品审核</h1>
      <el-button round @click="handleBatchDownload">批量下载 PDF</el-button>
    </div>

    <div class="status-summary">
      <span class="summary-item">
        待审 <strong>{{ projects.filter(p => p.status === 'pending').length }}</strong>
      </span>
      <span class="summary-item">
        已通过 <strong>{{ projects.filter(p => p.status === 'approved').length }}</strong>
      </span>
      <span class="summary-item">
        已驳回 <strong>{{ projects.filter(p => p.status === 'rejected').length }}</strong>
      </span>
    </div>

    <el-table :data="projects" stripe style="width: 100%">
      <el-table-column prop="title" label="作品名称" min-width="180" />
      <el-table-column prop="author_name" label="作者" width="100" />
      <el-table-column prop="major" label="专业" width="120" />
      <el-table-column prop="date" label="提交时间" width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]!.type as any" size="small" effect="plain">
            {{ statusMap[row.status]!.label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Detail drawer -->
    <el-drawer v-model="drawerVisible" title="作品详情" size="480px">
      <template v-if="selectedProject">
        <div class="detail-section">
          <h3>{{ selectedProject.title }}</h3>
          <p class="detail-meta">{{ selectedProject.author_name }} · {{ selectedProject.major }}</p>
        </div>

        <div class="detail-section">
          <label>作品描述</label>
          <p class="detail-desc">{{ selectedProject.description }}</p>
        </div>

        <div class="detail-section">
          <label>技术标签</label>
          <div class="detail-tags">
            <span v-for="tag in selectedProject.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>

        <div v-if="selectedProject.link_url" class="detail-section">
          <label>外链</label>
          <a :href="selectedProject.link_url" target="_blank" rel="noopener" class="detail-link">
            {{ selectedProject.link_url }}
          </a>
        </div>

        <div class="detail-section">
          <label>当前状态</label>
          <el-tag :type="statusMap[selectedProject.status]!.type as any" size="small" effect="plain">
            {{ statusMap[selectedProject.status]!.label }}
          </el-tag>
          <p v-if="selectedProject.reject_reason" class="reject-reason">驳回理由：{{ selectedProject.reject_reason }}</p>
        </div>

        <div v-if="selectedProject.status === 'pending'" class="detail-actions">
          <el-button type="success" round @click="handleApprove">通过</el-button>
          <div class="reject-area">
            <el-input v-model="rejectReason" type="textarea" :rows="2" placeholder="填写驳回理由" />
            <el-button type="danger" round @click="handleReject">驳回</el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.status-summary {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-lg);
}

.summary-item {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.summary-item strong {
  font-weight: 700;
  color: var(--color-text);
  margin-left: var(--space-xs);
}

.detail-section {
  margin-bottom: var(--space-xl);
}

.detail-section h3 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.detail-meta {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.detail-section label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-sm);
}

.detail-desc {
  font-size: 0.9rem;
  color: var(--color-text);
  line-height: 1.7;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.tag {
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
}

.reject-reason {
  margin-top: var(--space-sm);
  font-size: 0.85rem;
  color: #ef4444;
}

.detail-link {
  font-size: 0.85rem;
  color: var(--color-primary);
  word-break: break-all;
}

.detail-actions {
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border-light);
}

.reject-area {
  margin-top: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
</style>
