<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyProjects, getProjects, type Project } from '@/api/project'
import { resolveFileUrl } from '@/utils/url'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(true)

// 分页
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)
const myProjects = ref<Project[]>([])
const mySubmissionsVisible = ref(false)
const mySubmissionsLoading = ref(false)

const statusMap: Record<string, { label: string; type: 'success' | 'warning' | 'danger' | 'info' }> = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
}

onMounted(async () => {
  await loadProjects()
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

function handlePageChange(page: number) {
  currentPage.value = page
  loadProjects()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function getProjectStatus(project: Project) {
  return statusMap[project.status] || { label: project.status || '未知状态', type: 'info' as const }
}

async function openMySubmissions() {
  mySubmissionsVisible.value = true
  await loadMySubmissions()
}

async function loadMySubmissions() {
  mySubmissionsLoading.value = true
  try {
    const res = await getMyProjects(1, 50)
    myProjects.value = res.items
  } finally {
    mySubmissionsLoading.value = false
  }
}

function goProject(project: Project) {
  router.push(`/create/project/${project.id}`)
}

function goResubmit(project: Project) {
  router.push(`/create/upload?projectId=${project.id}`)
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
          <h1>造 · 智创未来</h1>
          <p>AI + 硬件创意作品展示，打破"AI 只是聊天框"的思维局限</p>
        </div>
      </div>
    </section>

    <!-- Gallery -->
    <section class="gallery-section">
      <div class="container">
        <div class="gallery-header">
          <h2>学生作品画廊</h2>
          <p>每一件作品都是 AI 与硬件碰撞的火花</p>
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
            <p>将你的 AI + 硬件创意作品展示给更多人</p>
            <p class="upload-hint">支持课程报告、演示视频链接、硬件接线图等</p>
          </div>
          <el-button type="warning" size="large" round @click="router.push('/create/upload')">
            上传作品
          </el-button>
          <el-button size="large" round @click="openMySubmissions">
            我的提交
          </el-button>
        </div>
      </div>
    </section>

    <el-drawer v-model="mySubmissionsVisible" title="我的提交" size="620px">
      <div v-loading="mySubmissionsLoading" class="submissions-panel">
        <div v-if="!mySubmissionsLoading && myProjects.length === 0" class="my-empty-state">
          <p>你还没有提交作品。</p>
          <el-button type="warning" round @click="router.push('/create/upload')">上传作品</el-button>
        </div>

        <div v-else class="submission-list">
          <div v-for="project in myProjects" :key="project.id" class="submission-item">
            <div class="submission-main" @click="goProject(project)">
              <div class="submission-head">
                <h3>{{ project.title }}</h3>
                <el-tag :type="getProjectStatus(project).type" size="small" effect="plain">
                  {{ getProjectStatus(project).label }}
                </el-tag>
              </div>
              <p class="submission-desc">{{ project.description || '暂无作品描述' }}</p>
              <p v-if="project.status === 'pending'" class="submission-note">作品正在等待教师审核。</p>
              <p v-if="project.status === 'rejected'" class="submission-reject">
                驳回原因：{{ project.reject_reason || '请根据教师意见修改后重新提交。' }}
              </p>
            </div>
            <div class="submission-actions">
              <el-button v-if="project.status === 'rejected'" type="warning" round @click="goResubmit(project)">
                修改后重新提交
              </el-button>
              <el-button v-else round @click="goProject(project)">查看详情</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.create-page {
  padding-top: 64px;
}

/* Page hero */
.page-hero {
  padding: var(--space-3xl) 0;
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
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, var(--color-create-light), var(--color-create));
  border-radius: var(--radius-lg);
  color: white;
  margin-bottom: var(--space-lg);
}

.hero-inner h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.hero-inner p {
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

/* Gallery */
.gallery-section {
  padding: var(--space-3xl) 0;
}

.gallery-header {
  margin-bottom: var(--space-2xl);
}

.gallery-header h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.gallery-header p {
  font-size: 0.95rem;
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
  gap: var(--space-xl);
}

.project-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
}

.project-card:hover {
  transform: translateY(-4px);
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
  padding: var(--space-lg);
}

.project-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.project-author {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-md);
}

.project-desc {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-md);
}

.project-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-bottom: var(--space-md);
}

.project-tag {
  padding: 0.2rem 0.6rem;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(245, 158, 11, 0.15);
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
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.project-likes svg {
  color: #ef4444;
}

.view-btn {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-create);
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
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: var(--radius-lg);
}

.upload-card :deep(.el-button + .el-button) {
  margin-left: var(--space-sm);
}

.upload-content h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.upload-content p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.upload-hint {
  font-size: 0.8rem !important;
  color: var(--color-text-muted) !important;
  margin-top: var(--space-xs);
}

.submissions-panel {
  min-height: 240px;
}

.my-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
}

.submission-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.submission-item {
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.submission-main {
  cursor: pointer;
}

.submission-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-sm);
}

.submission-head h3 {
  min-width: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.submission-desc,
.submission-note,
.submission-reject {
  font-size: 0.85rem;
  line-height: 1.6;
}

.submission-desc {
  color: var(--color-text-secondary);
}

.submission-note {
  margin-top: var(--space-xs);
  color: var(--color-text-muted);
}

.submission-reject {
  margin-top: var(--space-sm);
  padding: var(--space-sm);
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: var(--radius-sm);
}

.submission-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-md);
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
}
</style>
