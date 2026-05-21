<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { createProject } from '@/api/project'
import { uploadFile } from '@/api/upload'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  title: '',
  description: '',
  videoUrl: '',
  linkUrl: '',
})

const tags = ref<string[]>([])
const tagInput = ref('')
const reportFile = ref<File | null>(null)
const imageFile = ref<File | null>(null)
const reportInput = ref<HTMLInputElement | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)
const submitting = ref(false)

const currentUserName = computed(() => authStore.user?.name || '当前用户')
const currentMajor = computed(() => authStore.user?.major || '未设置')

function addTag() {
  const value = tagInput.value.trim()
  if (value && !tags.value.includes(value) && tags.value.length < 5) {
    tags.value.push(value)
    tagInput.value = ''
  }
}

function removeTag(index: number) {
  tags.value.splice(index, 1)
}

function handleReportUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    reportFile.value = input.files[0]
  }
}

function handleImageUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    imageFile.value = input.files[0]
  }
}

async function handleSubmit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写作品名称')
    return
  }
  if (!form.description.trim()) {
    ElMessage.warning('请填写作品描述')
    return
  }

  submitting.value = true
  try {
    let reportUrl = ''
    let imageUrl = ''

    if (reportFile.value) {
      const result = await uploadFile(reportFile.value)
      reportUrl = result.url
    }
    if (imageFile.value) {
      const result = await uploadFile(imageFile.value)
      imageUrl = result.url
    }

    await createProject({
      title: form.title.trim(),
      description: form.description.trim(),
      tags: tags.value,
      video_url: form.videoUrl.trim() || undefined,
      report_url: reportUrl || undefined,
      image_url: imageUrl || undefined,
      link_url: form.linkUrl.trim() || undefined,
    })

    ElMessage.success('作品提交成功')
    router.push('/create')
  } catch {
    ElMessage.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="upload-page">
    <div class="container">
      <button class="back-btn" @click="router.push('/create')">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        返回作品列表
      </button>

      <div class="upload-card">
        <h1>提交你的作品</h1>
        <p class="subtitle">提交后由教师端统一审核，报告和展示图会随作品一起保存。</p>

        <div class="meta-row">
          <div class="meta-item">
            <span class="meta-label">提交人</span>
            <span class="meta-value">{{ currentUserName }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">所属专业</span>
            <span class="meta-value">{{ currentMajor }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>作品名称 <span class="req">*</span></label>
          <el-input v-model="form.title" placeholder="给你的作品起个名字" size="large" />
        </div>

        <div class="form-group">
          <label>作品描述 <span class="req">*</span></label>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="5"
            placeholder="描述作品的功能、技术实现和亮点"
            size="large"
          />
        </div>

        <div class="form-group">
          <label>技术标签</label>
          <div class="tag-input-row">
            <el-input
              v-model="tagInput"
              placeholder="输入标签后按回车添加"
              size="large"
              @keyup.enter="addTag"
            />
            <button class="btn-add-tag" @click="addTag">+ 添加</button>
          </div>
          <div v-if="tags.length > 0" class="tags-display">
            <span v-for="(tag, index) in tags" :key="tag" class="tag-item">
              {{ tag }}
              <button class="tag-remove" @click="removeTag(index)">&times;</button>
            </span>
          </div>
        </div>

        <div class="form-group">
          <label>课程报告（PDF）</label>
          <div class="upload-zone" @click="reportInput?.click()">
            <input ref="reportInput" type="file" accept=".pdf" hidden @change="handleReportUpload" />
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-if="!reportFile">点击或拖拽上传 PDF 文件（限 20MB）</span>
            <span v-else class="file-name">{{ reportFile.name }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>演示视频链接</label>
          <el-input v-model="form.videoUrl" placeholder="填写 Bilibili / YouTube 链接" size="large" />
        </div>

        <div class="form-group">
          <label>外链地址</label>
          <el-input v-model="form.linkUrl" placeholder="GitHub 仓库、在线演示等链接" size="large" />
        </div>

        <div class="form-group">
          <label>硬件接线图（图片）</label>
          <div class="upload-zone" @click="imageInput?.click()">
            <input ref="imageInput" type="file" accept="image/*" hidden @change="handleImageUpload" />
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-if="!imageFile">点击上传接线图（JPG/PNG，限 5MB）</span>
            <span v-else class="file-name">{{ imageFile.name }}</span>
          </div>
        </div>

        <div class="form-actions">
          <el-button type="warning" size="large" round :loading="submitting" @click="handleSubmit">
            提交作品
          </el-button>
          <el-button size="large" round @click="router.push('/create')">取消</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page {
  padding-top: 80px;
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

.upload-card {
  max-width: 680px;
  margin: 0 auto;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
}

.upload-card h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.subtitle {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
}

.meta-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.meta-item {
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.meta-label {
  display: block;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-xs);
}

.meta-value {
  display: block;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.req {
  color: #ef4444;
}

.tag-input-row {
  display: flex;
  gap: var(--space-sm);
}

.btn-add-tag {
  padding: 0 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-create);
  background: var(--color-create-bg);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  transition: all var(--duration-fast);
}

.btn-add-tag:hover {
  background: rgba(245, 158, 11, 0.12);
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.tag-remove {
  font-size: 1rem;
  line-height: 1;
  color: var(--color-text-muted);
  padding: 0 2px;
}

.tag-remove:hover {
  color: #ef4444;
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone:hover {
  border-color: var(--color-create);
  background: var(--color-create-bg);
  color: var(--color-create);
}

.file-name {
  color: var(--color-create);
  font-weight: 600;
}

.form-actions {
  display: flex;
  gap: var(--space-md);
  padding-top: var(--space-md);
}

@media (max-width: 640px) {
  .meta-row {
    grid-template-columns: 1fr;
  }
}
</style>
