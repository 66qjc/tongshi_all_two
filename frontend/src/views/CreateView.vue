<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyProjects, getProjects, withdrawProject, type Project } from '@/api/project'
import { resolveFileUrl } from '@/utils/url'

const router = useRouter()
const projects = ref<Project[]>([])
const myProjects = ref<Project[]>([])
const loading = ref(true)
const historyLoading = ref(false)
const withdrawingId = ref<number | null>(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

onMounted(async () => {
  await Promise.all([loadProjects(), loadMyProjects()])
})

async function loadProjects() {
  loading.value = true
  try {
    const res = await getProjects(currentPage.value, pageSize.value)
    projects.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadMyProjects() {
  historyLoading.value = true
  try {
    const res = await getMyProjects(1, 100)
    myProjects.value = res.items
  } catch {
    ElMessage.error('提交历史加载失败，请稍后重试')
  } finally {
    historyLoading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProjects()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已驳回',
    withdrawn: '已撤回',
  }
  return labels[status] || '未知'
}

function getStatusType(status: string) {
  const types: Record<string, 'warning' | 'success' | 'danger' | 'info'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    withdrawn: 'info',
  }
  return types[status] || 'info'
}

function canWithdraw(project: Project) {
  return project.status !== 'withdrawn'
}

async function handleWithdraw(project: Project) {
  try {
    await ElMessageBox.confirm(
      `确定撤回作品「${project.title}」吗？撤回后作品不会继续展示或审核。`,
      '撤回确认',
      { type: 'warning', confirmButtonText: '确认撤回', cancelButtonText: '取消' },
    )
    withdrawingId.value = project.id
    await withdrawProject(project.id)
    ElMessage.success('作品已撤回')
    await Promise.all([loadProjects(), loadMyProjects()])
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('撤回失败，请稍后重试')
    }
  } finally {
    withdrawingId.value = null
  }
}
</script>

<template>
  <div class="create-page">
    <!-- Page hero -->
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1>践 · 动手创作</h1>
          <p>AI 创意作品展示，打破"AI 只是聊天框"的思维局限</p>
        </div>
      </div>
    </section>

    <!-- Gallery -->
    <section class="gallery-section">
      <div class="container">
        <div class="gallery-header">
          <h2>学生作品画廊</h2>
          <p>每一件作品都是 学生 和 AI 碰撞的火花</p>
        </div>

        <div class="projects-grid">
          <div
            v-for="project in projects"
            :key="project.id"
            class="project-card"
            :class="{ featured: project.featured }"
          >
            <!-- Project image -->
            <div class="project-image">
              <img
                v-if="project.images?.length || project.image_url"
                :src="resolveFileUrl(project.images?.[0]?.image_url || project.image_url)"
                :alt="project.title"
                class="project-thumb"
              />
              <div v-else class="image-placeholder">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                        stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <el-tag
                v-if="project.featured"
                type="warning"
                size="small"
                class="featured-badge"
              >
                精选作品
              </el-tag>
            </div>

            <div class="project-body">
              <h3 class="project-title">{{ project.title }}</h3>
              <p class="project-author">{{ project.author_name }} · {{ project.major }}</p>
              <p class="project-desc">{{ project.description }}</p>

              <div class="project-tags">
                <span v-for="tag in project.tags" :key="tag" class="project-tag">
                  {{ tag }}
                </span>
              </div>

              <div class="project-footer">
                <span class="project-likes">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
                          stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {{ project.likes }}
                </span>
                <button class="view-btn" @click="router.push(`/create/project/${project.id}`)">查看详情</button>
              </div>
            </div>
          </div>
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
      </div>
    </section>

    <!-- Upload CTA -->
    <section class="upload-section">
      <div class="container">
        <div class="upload-card">
          <div class="upload-content">
            <h3>提交你的作品</h3>
            <p>将你的 AI 创意作品展示给更多人</p>
            <p class="upload-hint">支持课程报告、演示视频链接等</p>
          </div>
          <el-button type="warning" size="large" round @click="router.push('/create/upload')">
            上传作品
          </el-button>
        </div>
      </div>
    </section>

    <section class="history-section">
      <div class="container">
        <div class="history-header">
          <div>
            <h2>我的提交历史</h2>
            <p>查看每次作品提交的审核状态，也可以撤回不想继续展示或审核的作品。</p>
          </div>
          <el-button round @click="loadMyProjects">刷新</el-button>
        </div>

        <div v-loading="historyLoading" class="history-panel">
          <div v-if="myProjects.length === 0" class="history-empty">
            还没有提交过作品
          </div>
          <div v-else class="history-list">
            <div v-for="project in myProjects" :key="project.id" class="history-item">
              <div class="history-main">
                <div class="history-title-row">
                  <h3>{{ project.title }}</h3>
                  <el-tag :type="getStatusType(project.status)" size="small" effect="plain">
                    {{ getStatusLabel(project.status) }}
                  </el-tag>
                </div>
                <p>{{ project.description }}</p>
                <div class="history-meta">
                  <span>{{ project.course_name || '未关联课程' }}</span>
                  <span>{{ project.date || '-' }}</span>
                  <span v-if="project.reject_reason">驳回原因：{{ project.reject_reason }}</span>
                </div>
              </div>
              <div class="history-actions">
                <el-button text size="small" @click="router.push(`/create/project/${project.id}`)">查看</el-button>
                <el-button
                  v-if="project.status === 'rejected'"
                  text
                  size="small"
                  type="warning"
                  @click="router.push(`/create/upload?projectId=${project.id}`)"
                >
                  修改重交
                </el-button>
                <el-button
                  v-if="canWithdraw(project)"
                  text
                  size="small"
                  type="danger"
                  :loading="withdrawingId === project.id"
                  @click="handleWithdraw(project)"
                >
                  撤回
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.create-page {
  padding-top: 60px;
}

/* Page hero */
.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
  background: var(--color-create-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: var(--color-create);
  border-radius: var(--radius-md);
  color: white;
  margin-bottom: var(--space-lg);
  box-shadow: 0 4px 14px rgba(184, 134, 11, 0.2);
}

.hero-inner h1 {
  font-family: var(--font-serif);
  font-size: 1.8rem;
  font-weight: 900;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0.05em;
}

.hero-inner p {
  font-size: 0.92rem;
  color: var(--color-text-secondary);
}

/* Gallery */
.gallery-section {
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.gallery-header {
  margin-bottom: var(--space-2xl);
}

.gallery-header h2 {
  font-family: var(--font-serif);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.05em;
}

.gallery-header p {
  font-size: 0.88rem;
  color: var(--color-text-secondary);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: var(--space-2xl);
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.project-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
}

.project-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.project-card.featured {
  border-color: var(--color-create-light);
}

.project-image {
  position: relative;
  aspect-ratio: 16 / 10;
  background: var(--color-bg-alt);
}

.project-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.featured-badge {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
}

.project-body {
  padding: var(--space-md) var(--space-lg);
}

.project-title {
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.02em;
}

.project-author {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-md);
}

.project-desc {
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  line-height: 1.65;
  margin-bottom: var(--space-md);
}

.project-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-bottom: var(--space-md);
}

.project-tag {
  padding: 0.15rem 0.5rem;
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(184, 134, 11, 0.12);
}

.project-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.project-likes {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.project-likes svg {
  color: #c0392b;
}

.view-btn {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-create);
  letter-spacing: 0.03em;
  transition: opacity var(--duration-fast);
}

.view-btn:hover {
  opacity: 0.7;
}

/* Upload CTA */
.upload-section {
  padding: var(--space-2xl) 0;
}

.upload-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xl) var(--space-2xl);
  background: var(--color-create-bg);
  border: 1px solid rgba(184, 134, 11, 0.12);
  border-radius: var(--radius-md);
}

.upload-content h3 {
  font-family: var(--font-serif);
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.03em;
}

.upload-content p {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.upload-hint {
  font-size: 0.75rem !important;
  color: var(--color-text-muted) !important;
  margin-top: var(--space-xs);
}

.history-section {
  padding: 0 0 var(--space-3xl);
}

.history-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.history-header h2 {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.05em;
}

.history-header p,
.history-empty,
.history-meta {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.history-panel {
  min-height: 96px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.history-empty {
  padding: var(--space-2xl);
  text-align: center;
}

.history-list {
  display: flex;
  flex-direction: column;
}

.history-item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-lg);
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border-light);
}

.history-item:last-child {
  border-bottom: 0;
}

.history-main {
  min-width: 0;
}

.history-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.history-title-row h3 {
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--color-text);
  word-break: break-word;
}

.history-main p {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  line-height: 1.6;
  margin-bottom: var(--space-sm);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.history-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: var(--space-xs);
}

@media (max-width: 1024px) {
  .projects-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }

  .upload-card {
    flex-direction: column;
    text-align: center;
    gap: var(--space-lg);
  }

  .history-header,
  .history-item {
    flex-direction: column;
    align-items: stretch;
  }

  .history-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
