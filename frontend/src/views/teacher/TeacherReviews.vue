<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveProject, downloadProjectReportsZip, getAllProjects, rejectProject } from '@/api/teacher'
import type { Project } from '@/api/project'
import { resolveFileUrl } from '@/utils/url'

const projects = ref<Project[]>([])
const loading = ref(true)
const downloading = ref(false)
const drawerVisible = ref(false)
const selectedProject = ref<Project | null>(null)
const rejectReason = ref('')
const imagePreviewVisible = ref(false)
const previewImage = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref<string | null>(null)
const searchKeyword = ref('')

const statusMap: Record<string, { label: string; type: 'warning' | 'success' | 'danger' }> = {
  pending: { label: '待审', type: 'warning' },
  approved: { label: '通过', type: 'success' },
  rejected: { label: '驳回', type: 'danger' },
}

const imageList = computed(() => {
  if (!selectedProject.value) return []
  if (selectedProject.value.images && selectedProject.value.images.length > 0) {
    return selectedProject.value.images.map(item => resolveFileUrl(item.image_url))
  }
  return selectedProject.value.image_url ? [resolveFileUrl(selectedProject.value.image_url)] : []
})
const materialsSummary = computed(() => ({
  hasReport: Boolean(selectedProject.value?.report_url || selectedProject.value?.report_file_id),
  imageCount: imageList.value.length,
  hasVideo: Boolean(selectedProject.value?.video_url),
  hasLink: Boolean(selectedProject.value?.link_url),
}))

const reportPreviewUrl = computed(() => {
  const p = selectedProject.value
  if (!p) return ''
  if (p.report_file_id) return resolveFileUrl(`/api/files/${p.report_file_id}`)
  return resolveFileUrl(p.report_url)
})

onMounted(async () => {
  await loadProjects()
})

async function loadProjects() {
  loading.value = true
  try {
    const res = await getAllProjects(
      statusFilter.value || undefined,
      searchKeyword.value || undefined,
      currentPage.value,
      pageSize.value,
    )
    projects.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('作品数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  loadProjects()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProjects()
}

function handleStatusChange() {
  currentPage.value = 1
  loadProjects()
}

function openDetail(project: Project) {
  selectedProject.value = project
  rejectReason.value = ''
  drawerVisible.value = true
}

function openImagePreview(imageUrl: string) {
  previewImage.value = imageUrl
  imagePreviewVisible.value = true
}

async function handleApprove() {
  if (!selectedProject.value) return
  try {
    await ElMessageBox.confirm(
      `确定通过作品「${selectedProject.value.title}」吗？`,
      '审核确认',
      { type: 'warning' },
    )
    await approveProject(selectedProject.value.id)
    drawerVisible.value = false
    ElMessage.success('已通过')
    loadProjects()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('审核失败，请稍后重试')
    }
  }
}

async function handleReject() {
  if (!selectedProject.value) return
  const reason = rejectReason.value.trim()
  if (!reason) {
    ElMessage.warning('请填写驳回理由')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定驳回作品「${selectedProject.value.title}」吗？驳回理由将反馈给学生。`,
      '审核确认',
      { type: 'warning' },
    )
    await rejectProject(selectedProject.value.id, reason)
    drawerVisible.value = false
    ElMessage.success('已驳回')
    loadProjects()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('驳回失败，请稍后重试')
    }
  }
}

async function handleBatchDownload() {
  downloading.value = true
  try {
    const { blob, filename } = await downloadProjectReportsZip()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '批量下载失败')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="reviews-page">
    <div class="page-header">
      <h1>作品审核</h1>
      <el-button round :loading="downloading" @click="handleBatchDownload">批量下载报告</el-button>
    </div>

    <div class="status-summary">
      <el-select
        v-model="statusFilter"
        placeholder="全部状态"
        clearable
        size="default"
        style="width: 140px"
        @change="handleStatusChange"
      >
        <el-option label="全部状态" :value="null" />
        <el-option label="待审" value="pending" />
        <el-option label="通过" value="approved" />
        <el-option label="驳回" value="rejected" />
      </el-select>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索作品名称"
        clearable
        size="default"
        style="width: 200px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #prefix>
          <span style="font-size: 0.85rem; color: var(--color-text-muted);">🔍</span>
        </template>
      </el-input>
      <span class="filter-count">共 {{ total }} 条</span>
    </div>

    <el-table :data="projects" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="作品名称" min-width="180" />
      <el-table-column prop="author_name" label="作者" width="120" />
      <el-table-column prop="major" label="专业" width="120" />
      <el-table-column prop="date" label="提交时间" width="120" />
      <el-table-column label="材料" width="200">
        <template #default="{ row }">
          <span class="material-meta">PDF {{ row.report_url || row.report_file_id ? '已上传' : '未上传' }}</span>
          <span class="material-meta">图片 {{ row.images?.length || (row.image_url ? 1 : 0) }} 张</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type || 'info'" size="small" effect="plain">
            {{ statusMap[row.status]?.label || '未知' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && projects.length === 0" class="empty-state">
      <p>当前没有待审核或已通过的作品。</p>
    </div>

    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="handlePageChange"
      />
    </div>

    <el-drawer v-model="drawerVisible" title="作品详情" size="640px">
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

        <div class="detail-section">
          <label>材料完整性</label>
          <div class="summary-grid">
            <div class="summary-chip">PDF：{{ materialsSummary.hasReport ? '已上传' : '未上传' }}</div>
            <div class="summary-chip">图片：{{ materialsSummary.imageCount }} 张</div>
            <div class="summary-chip">视频：{{ materialsSummary.hasVideo ? '有' : '无' }}</div>
            <div class="summary-chip">外链：{{ materialsSummary.hasLink ? '有' : '无' }}</div>
          </div>
        </div>

        <div class="detail-section">
          <label>课程报告</label>
          <div v-if="reportPreviewUrl" class="pdf-preview">
            <div class="pdf-actions">
              <a :href="reportPreviewUrl" target="_blank" rel="noopener" class="detail-link">
                新开查看 PDF
              </a>
            </div>
            <iframe :src="reportPreviewUrl" title="PDF 预览" class="pdf-frame"></iframe>
          </div>
          <p v-else class="empty-inline">学生未上传 PDF 报告。</p>
        </div>

        <div class="detail-section">
          <label>作品图片</label>
          <div v-if="imageList.length > 0" class="image-grid">
            <button
              v-for="(image, index) in imageList"
              :key="`${image}-${index}`"
              class="image-thumb"
              @click="openImagePreview(image)"
            >
              <img :src="image" :alt="`作品图片 ${index + 1}`" />
            </button>
          </div>
          <p v-else class="empty-inline">学生未上传作品图片。</p>
        </div>

        <div v-if="selectedProject.video_url" class="detail-section">
          <label>演示视频</label>
          <a :href="resolveFileUrl(selectedProject.video_url)" target="_blank" rel="noopener" class="detail-link">
            {{ selectedProject.video_url }}
          </a>
        </div>

        <div v-if="selectedProject.link_url" class="detail-section">
          <label>外链</label>
          <a :href="selectedProject.link_url" target="_blank" rel="noopener" class="detail-link">
            {{ selectedProject.link_url }}
          </a>
        </div>

        <div class="detail-section">
          <label>当前状态</label>
          <el-tag :type="statusMap[selectedProject.status]?.type || 'info'" size="small" effect="plain">
            {{ statusMap[selectedProject.status]?.label || '未知' }}
          </el-tag>
          <p v-if="selectedProject.reject_reason" class="reject-reason">驳回理由：{{ selectedProject.reject_reason }}</p>
        </div>

        <div v-if="selectedProject.status === 'pending'" class="detail-actions">
          <el-button type="success" round @click="handleApprove">通过</el-button>
          <div class="reject-area">
            <el-input v-model="rejectReason" type="textarea" :rows="2" placeholder="请填写驳回理由" />
            <el-button type="danger" round @click="handleReject">驳回</el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="imagePreviewVisible" width="720px" append-to-body @close="previewImage = ''">
      <img v-if="previewImage" :src="previewImage" alt="作品大图" class="preview-image" />
    </el-dialog>
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

.material-meta {
  display: block;
  font-size: 0.8rem;
  color: var(--color-text-muted);
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

.detail-tags,
.summary-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.tag,
.summary-chip {
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
}

.pdf-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.pdf-actions {
  display: flex;
  justify-content: flex-end;
}

.pdf-frame {
  width: 100%;
  height: 320px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}

.image-thumb {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg-card);
}

.image-thumb img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.empty-inline {
  font-size: 0.85rem;
  color: var(--color-text-muted);
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

.preview-image {
  width: 100%;
  max-height: 75vh;
  object-fit: contain;
  display: block;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.filter-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl);
}

@media (max-width: 768px) {
  .image-grid {
    grid-template-columns: 1fr;
  }
}
</style>
