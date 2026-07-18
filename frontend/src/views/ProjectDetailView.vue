<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProject,
  toggleLike as apiToggleLike,
  deleteMyProject,
  guestLikeProject,
  type Project,
} from '@/api/project'
import { useAuthStore } from '@/stores/auth'
import { resolveFileUrl } from '@/utils/url'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'
import AuthenticatedFileImage from '@/components/common/AuthenticatedFileImage.vue'

interface ProtectedImageSource {
  fileId?: number
  url: string
  key: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const project = ref<Project | null>(null)
const loading = ref(true)
const liked = ref(false)
const deleting = ref(false)
const relatedProjects = ref<{ id: number; title: string; author: string }[]>([])
const previewImage = ref<ProtectedImageSource | null>(null)
const imagePreviewVisible = ref(false)

const projectId = computed(() => Number(route.params.id))
const guestLikeKey = computed(() => `guest_liked_${projectId.value}`)
const imageList = computed<ProtectedImageSource[]>(() => {
  if (!project.value) return []
  if (project.value.images && project.value.images.length > 0) {
    return project.value.images.map((item, index) => ({
      fileId: item.file_id,
      url: item.image_url,
      key: String(item.id || item.file_id || `${project.value?.id}-${index}`),
    }))
  }
  if (!project.value.image_url && !project.value.cover_file_id) return []
  return [{
    fileId: project.value.cover_file_id,
    url: project.value.image_url,
    key: `legacy-${project.value.id}`,
  }]
})
const projectCover = computed<ProtectedImageSource | null>(() => {
  if (!project.value) return null
  const firstImage = imageList.value[0]
  const fileId = project.value.cover_file_id || firstImage?.fileId
  const url = firstImage?.url || project.value.image_url
  return fileId || url ? { fileId, url, key: `cover-${project.value.id}` } : null
})
const canResubmit = computed(() => {
  if (!project.value) return false
  return project.value.status === 'rejected' && project.value.author_id === authStore.user?.id
})
const canDelete = computed(() => {
  if (!project.value || !authStore.user) return false
  return project.value.author_id === authStore.user.id
    && (project.value.status === 'pending' || project.value.status === 'rejected')
})
const projectLink = computed(() => project.value?.link_url || project.value?.video_url || '')
const reportSource = computed(() => {
  const currentProject = project.value
  if (!currentProject) return ''
  if (currentProject.report_file_id) return `/api/files/${currentProject.report_file_id}`
  return currentProject.report_url || ''
})
const reportEnabled = computed(() => Boolean(reportSource.value))
const {
  resolvedUrl: reportResolvedUrl,
  loading: reportLoading,
  error: reportError,
} = useAuthenticatedFileUrl(reportSource, { enabled: reportEnabled })

onMounted(async () => {
  try {
    project.value = await getProject(projectId.value)
    if (authStore.isLoggedIn) {
      liked.value = project.value?.is_liked ?? false
    } else {
      liked.value = localStorage.getItem(guestLikeKey.value) === '1'
    }
  } finally {
    loading.value = false
  }
})

async function toggleLike() {
  if (!project.value) return
  if (!authStore.isLoggedIn) {
    if (localStorage.getItem(guestLikeKey.value) === '1') return
    const result = await guestLikeProject(project.value.id)
    project.value.likes = result.likes
    liked.value = true
    localStorage.setItem(guestLikeKey.value, '1')
    return
  }
  const result = await apiToggleLike(project.value.id)
  project.value.likes = result.likes
  liked.value = result.liked
}

async function handleDelete() {
  if (!project.value || deleting.value) return
  try {
    await ElMessageBox.confirm(
      `将删除「${project.value.title}」。删除后不可在「我的作品」中恢复，如需再次展示请重新上传。`,
      '确认删除作品？',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await deleteMyProject(project.value.id)
    ElMessage.success('已删除')
    router.push('/create')
  } catch {
    // 业务错误由拦截器提示
  } finally {
    deleting.value = false
  }
}

function goResubmit() {
  if (!project.value) return
  router.push(`/create/upload?projectId=${project.value.id}`)
}

function openPreview(image: ProtectedImageSource) {
  previewImage.value = image
  imagePreviewVisible.value = true
}
</script>

<template>
  <div class="detail-page">
    <div class="container">
      <button class="back-btn" @click="router.push('/create')">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        返回作品列表
      </button>

      <div v-if="project" class="detail-content">
        <div class="project-image">
          <AuthenticatedFileImage
            v-if="projectCover"
            :file-id="projectCover.fileId"
            :fallback-url="projectCover.url"
            alt="作品图片"
            class="hero-image"
          />
          <div v-else class="image-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span>暂无作品图片</span>
          </div>
        </div>

        <div v-if="project.reject_reason" class="reject-alert">
          <strong>驳回原因：</strong>{{ project.reject_reason }}
        </div>

        <div class="project-header">
          <div>
            <h1>{{ project.title }}</h1>
            <p class="project-author">{{ project.author_name }} · {{ project.major }}</p>
          </div>
          <button class="like-btn" :class="{ liked }" @click="toggleLike">
            <svg width="20" height="20" viewBox="0 0 24 24" :fill="liked ? 'currentColor' : 'none'">
              <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            {{ project.likes }}
          </button>
        </div>

        <div v-if="canResubmit || canDelete" class="resubmit-bar">
          <el-button v-if="canResubmit" type="warning" round @click="goResubmit">修改后重新提交</el-button>
          <el-button v-if="canDelete" type="danger" round plain :loading="deleting" @click="handleDelete">删除作品</el-button>
        </div>

        <section class="detail-section">
          <h3>作品介绍</h3>
          <p>{{ project.description }}</p>
        </section>

        <section class="detail-section">
          <h3>技术栈</h3>
          <div class="tags">
            <span v-for="tag in project.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </section>

        <section v-if="imageList.length > 0" class="detail-section">
          <h3>作品图片</h3>
          <div class="gallery-grid">
            <button
              v-for="(image, index) in imageList"
              :key="image.key"
              class="gallery-item"
              @click="openPreview(image)"
            >
              <AuthenticatedFileImage
                :file-id="image.fileId"
                :fallback-url="image.url"
                :alt="`作品图片 ${index + 1}`"
              />
            </button>
          </div>
        </section>

        <section v-if="reportSource" class="detail-section">
          <h3>课程报告</h3>
          <a v-if="reportResolvedUrl" :href="reportResolvedUrl" target="_blank" rel="noopener" class="video-link">
            在新窗口打开 PDF 报告
          </a>
          <p v-else-if="reportLoading">正在获取报告访问地址，请稍候。</p>
          <p v-else-if="reportError">{{ reportError }}</p>
        </section>

        <section v-if="projectLink" class="detail-section">
          <h3 class="project-link-title">作品链接</h3>
          <a :href="resolveFileUrl(projectLink)" target="_blank" rel="noopener" class="external-link">
            {{ projectLink }}
          </a>
        </section>

        <section v-if="relatedProjects.length > 0" class="detail-section">
          <h3>相关作品</h3>
          <div class="related-grid">
            <div
              v-for="rp in relatedProjects"
              :key="rp.id"
              class="related-card"
              @click="router.push(`/create/project/${rp.id}`)"
            >
              <div class="related-image">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                        stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </div>
              <div class="related-info">
                <h4>{{ rp.title }}</h4>
                <p>{{ rp.author }}</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div v-else class="not-found">
        <h2>作品未找到</h2>
        <p>该作品可能已被移除或链接无效</p>
        <button class="btn-back" @click="router.push('/create')">返回作品列表</button>
      </div>
    </div>

    <el-dialog v-model="imagePreviewVisible" width="720px" append-to-body @close="previewImage = null">
      <AuthenticatedFileImage
        v-if="previewImage"
        :file-id="previewImage.fileId"
        :fallback-url="previewImage.url"
        alt="作品大图"
        class="preview-image"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.detail-page {
  padding-top: 60px;
  padding-bottom: var(--space-3xl);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
  transition: color var(--duration-fast);
}

.back-btn:hover {
  color: var(--color-create);
}

.project-image {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-xl);
}

.hero-image {
  width: 100%;
  max-height: 420px;
  object-fit: cover;
  display: block;
}

.image-placeholder {
  aspect-ratio: 16 / 9;
  background: var(--color-bg-alt);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.reject-alert {
  margin-bottom: var(--space-lg);
  padding: var(--space-md);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: var(--radius-sm);
  color: #b91c1c;
  font-size: 0.9rem;
  line-height: 1.7;
}

.project-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.project-header h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  text-wrap: balance;
}

.project-author {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.like-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
  flex-shrink: 0;
}

.like-btn:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.like-btn.liked {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}

.resubmit-bar {
  margin-bottom: var(--space-xl);
}

.detail-section {
  margin-bottom: var(--space-xl);
}

.detail-section h3 {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  text-wrap: balance;
}

.detail-section p {
  max-width: 72ch;
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.tag {
  padding: 0.3rem 0.8rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-md);
}

.gallery-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-card);
}

.gallery-item img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.video-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.6rem 1.2rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-create);
  background: var(--color-create-bg);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.video-link:hover {
  background: rgba(245, 158, 11, 0.12);
}

.external-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.6rem 1.2rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border: 1px solid rgba(79, 70, 229, 0.15);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
  word-break: break-all;
}

.external-link:hover {
  background: rgba(79, 70, 229, 0.12);
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}

.related-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.related-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.related-image {
  aspect-ratio: 16 / 10;
  background: var(--color-bg-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.related-info {
  padding: var(--space-md);
}

.related-info h4 {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 2px;
}

.related-info p {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.preview-image {
  width: 100%;
  max-height: 75vh;
  object-fit: contain;
  display: block;
}

.not-found {
  text-align: center;
  padding: var(--space-4xl) 0;
}

.not-found h2 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  text-wrap: balance;
}

.not-found p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
}

.btn-back {
  padding: 0.6rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: var(--color-create);
  border-radius: var(--radius-full);
}

@media (max-width: 768px) {
  .related-grid,
  .gallery-grid {
    grid-template-columns: 1fr;
  }

  .project-header {
    flex-direction: column;
    gap: var(--space-md);
  }
}
</style>
