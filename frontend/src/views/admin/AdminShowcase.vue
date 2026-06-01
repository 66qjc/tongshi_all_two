<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import {
  getShowcaseAdmin,
  createShowcaseItem,
  updateShowcaseItem,
  deleteShowcaseItem,
  deleteShowcaseImage,
  type ShowcaseItemOut,
  type ShowcaseItemImageOut,
} from '../../api/showcase'

const authStore = useAuthStore()

// ── 数据状态 ──────────────────────────────────────────────────
const loading = ref(false)
const showcaseData = ref<Record<string, ShowcaseItemOut[]>>({})
const activeTab = ref('welfare')

// 两个 section 的数据
const welfareItems = computed(() => showcaseData.value['welfare'] || [])
const readingItems = computed(() => showcaseData.value['reading_club'] || [])

// 上传请求头（带 JWT token）
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`,
}))

// ── 对话框状态 ─────────────────────────────────────────────────
const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const saveLoading = ref(false)

// 表单数据
const form = ref({
  section: 'welfare',
  title: '',
  content: '',
  link_url: '',
  sort_order: 0,
  is_active: true,
})

// 封面图相关
const coverFileId = ref<number | null>(null)
const coverPreviewUrl = ref('')

// 多图片相关
const imageFileIds = ref<number[]>([])
const imagePreviewUrls = ref<{ id: number; url: string }[]>([])

// section 显示名称映射
const sectionLabels: Record<string, string> = {
  welfare: '公益课社会价值',
  reading_club: '读书会活动',
}

// ── 数据加载 ───────────────────────────────────────────────────
const fetchItems = async () => {
  loading.value = true
  try {
    const data = await getShowcaseAdmin()
    showcaseData.value = data || {}
  } catch {
    ElMessage.error('加载内容列表失败，请刷新重试')
  } finally {
    loading.value = false
  }
}

// ── 新增 ────────────────────────────────────────────────────────
const handleAdd = () => {
  isEdit.value = false
  editId.value = null
  form.value = {
    section: activeTab.value,
    title: '',
    content: '',
    link_url: '',
    sort_order: 0,
    is_active: true,
  }
  coverFileId.value = null
  coverPreviewUrl.value = ''
  imageFileIds.value = []
  imagePreviewUrls.value = []
  showDialog.value = true
}

// ── 编辑 ────────────────────────────────────────────────────────
const handleEdit = (item: ShowcaseItemOut) => {
  isEdit.value = true
  editId.value = item.id
  form.value = {
    section: item.section,
    title: item.title,
    content: item.content || '',
    link_url: item.link_url || '',
    sort_order: item.sort_order,
    is_active: item.is_active,
  }
  // 编辑时显示现有封面，新上传后才替换
  coverFileId.value = null
  coverPreviewUrl.value = item.cover_url || ''
  // 加载多图片数据
  imageFileIds.value = item.images?.map(img => img.file_id) || []
  imagePreviewUrls.value = item.images?.map(img => ({ id: img.id, url: img.url })) || []
  showDialog.value = true
}

// ── 保存（新增或编辑）─────────────────────────────────────────
const handleSave = async () => {
  if (!form.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  saveLoading.value = true
  try {
    if (isEdit.value && editId.value !== null) {
      // 编辑：只传有变化的字段
      await updateShowcaseItem(editId.value, {
        title: form.value.title.trim(),
        content: form.value.content.trim() || undefined,
        // 若新上传了图片则替换，否则不传（后端保留原图）
        ...(coverFileId.value !== null ? { cover_file_id: coverFileId.value } : {}),
        image_file_ids: imageFileIds.value,
        link_url: form.value.link_url.trim() || undefined,
        sort_order: form.value.sort_order,
        is_active: form.value.is_active,
      })
      ElMessage.success('内容更新成功')
    } else {
      // 新增
      await createShowcaseItem({
        section: form.value.section,
        title: form.value.title.trim(),
        content: form.value.content.trim() || undefined,
        cover_file_id: coverFileId.value ?? null,
        image_file_ids: imageFileIds.value,
        link_url: form.value.link_url.trim() || undefined,
        sort_order: form.value.sort_order,
      })
      ElMessage.success('内容添加成功')
    }
    showDialog.value = false
    await fetchItems()
  } catch (err: any) {
    ElMessage.error(err?.message || (isEdit.value ? '更新失败，请重试' : '添加失败，请重试'))
  } finally {
    saveLoading.value = false
  }
}

// ── 删除 ────────────────────────────────────────────────────────
const handleDelete = async (id: number) => {
  try {
    await deleteShowcaseItem(id)
    ElMessage.success('内容已删除')
    await fetchItems()
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}

// ── 封面上传回调 ───────────────────────────────────────────────
// el-upload 直接发 XHR，响应体是原始 JSON：{ code: 0, data: { file_id, url, ... } }
const handleUploadSuccess = (response: any) => {
  if (response?.code === 0 && response?.data?.file_id) {
    coverFileId.value = response.data.file_id
    coverPreviewUrl.value = response.data.url || ''
    ElMessage.success('封面上传成功')
  } else {
    ElMessage.error(response?.message || '封面上传失败，请重试')
  }
}

const handleUploadError = () => {
  ElMessage.error('封面上传失败，请检查图片格式或网络后重试')
}

// ── 多图片上传回调 ─────────────────────────────────────────────
const handleImageUploadSuccess = (response: any) => {
  if (response?.code === 0 && response?.data?.file_id) {
    imageFileIds.value.push(response.data.file_id)
    imagePreviewUrls.value.push({
      id: response.data.file_id,
      url: response.data.url || '',
    })
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error(response?.message || '图片上传失败，请重试')
  }
}

const handleImageUploadError = () => {
  ElMessage.error('图片上传失败，请检查图片格式或网络后重试')
}

// ── 删除已上传的图片 ───────────────────────────────────────────
const handleRemoveImage = async (index: number) => {
  const imageInfo = imagePreviewUrls.value[index]
  if (!imageInfo) return
  // 如果是编辑模式且图片已保存到后端，调用后端删除 API
  if (isEdit.value && editId.value !== null && imageInfo.id != null && !imageFileIds.value.includes(imageInfo.id)) {
    try {
      await deleteShowcaseImage(editId.value, imageInfo.id)
    } catch {
      ElMessage.error('删除图片失败，请重试')
      return
    }
  }
  imageFileIds.value.splice(index, 1)
  imagePreviewUrls.value.splice(index, 1)
}

// ── 工具函数 ───────────────────────────────────────────────────
/** 截取内容摘要 */
const truncate = (text: string, len: number) =>
  text && text.length > len ? text.slice(0, len) + '...' : (text || '')

/** 格式化时间 */
const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

// ── 对话框标题 ─────────────────────────────────────────────────
const dialogTitle = computed(() => {
  const sectionLabel = sectionLabels[form.value.section] || form.value.section
  return isEdit.value ? `编辑内容 · ${sectionLabel}` : `新增内容 · ${sectionLabel}`
})

onMounted(fetchItems)
</script>

<template>
  <div class="showcase-page">
    <!-- 页面标题 + 操作按钮 -->
    <div class="page-header">
      <h1 class="page-title">内容管理</h1>
      <el-button type="primary" @click="handleAdd">新增内容</el-button>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab">
      <!-- ── 公益课社会价值 ─────────────────────────────── -->
      <el-tab-pane label="公益课社会价值" name="welfare">
        <div v-loading="loading" class="tab-content">
          <template v-if="!loading">
            <!-- 空状态 -->
            <el-empty
              v-if="welfareItems.length === 0"
              description="暂无内容，点击右上角「新增内容」开始添加"
            />
            <!-- 卡片列表 -->
            <div v-else class="item-list">
              <div v-for="item in welfareItems" :key="item.id" class="item-card">
                <!-- 封面缩略图 -->
                <div class="item-cover">
                  <img v-if="item.cover_url" :src="item.cover_url" :alt="item.title" />
                  <div v-else class="cover-placeholder">
                    <span>无图</span>
                  </div>
                </div>
                <!-- 内容信息 -->
                <div class="item-info">
                  <div class="item-title">{{ item.title }}</div>
                  <div class="item-summary">{{ truncate(item.content, 60) }}</div>
                  <div v-if="item.link_url" class="item-link">🔗 {{ item.link_url }}</div>
                </div>
                <!-- 状态与操作 -->
                <div class="item-meta">
                  <div class="meta-top">
                    <el-tag v-if="item.is_active" type="success" size="small">已激活</el-tag>
                    <el-tag v-else type="info" size="small">未激活</el-tag>
                    <span class="sort-badge">排序 {{ item.sort_order }}</span>
                  </div>
                  <div class="item-date">{{ formatDate(item.created_at) }}</div>
                  <div class="item-actions">
                    <el-button size="small" type="primary" text @click="handleEdit(item)">
                      编辑
                    </el-button>
                    <el-popconfirm
                      title="确定删除该内容吗？此操作不可恢复。"
                      confirm-button-text="确定删除"
                      cancel-button-text="取消"
                      @confirm="handleDelete(item.id)"
                    >
                      <template #reference>
                        <el-button size="small" type="danger" text>删除</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </el-tab-pane>

      <!-- ── 读书会活动 ─────────────────────────────────── -->
      <el-tab-pane label="读书会活动" name="reading_club">
        <div v-loading="loading" class="tab-content">
          <template v-if="!loading">
            <!-- 空状态 -->
            <el-empty
              v-if="readingItems.length === 0"
              description="暂无内容，点击右上角「新增内容」开始添加"
            />
            <!-- 卡片列表 -->
            <div v-else class="item-list">
              <div v-for="item in readingItems" :key="item.id" class="item-card">
                <!-- 封面缩略图 -->
                <div class="item-cover">
                  <img v-if="item.cover_url" :src="item.cover_url" :alt="item.title" />
                  <div v-else class="cover-placeholder">
                    <span>无图</span>
                  </div>
                </div>
                <!-- 内容信息 -->
                <div class="item-info">
                  <div class="item-title">{{ item.title }}</div>
                  <div class="item-summary">{{ truncate(item.content, 60) }}</div>
                  <div v-if="item.link_url" class="item-link">🔗 {{ item.link_url }}</div>
                </div>
                <!-- 状态与操作 -->
                <div class="item-meta">
                  <div class="meta-top">
                    <el-tag v-if="item.is_active" type="success" size="small">已激活</el-tag>
                    <el-tag v-else type="info" size="small">未激活</el-tag>
                    <span class="sort-badge">排序 {{ item.sort_order }}</span>
                  </div>
                  <div class="item-date">{{ formatDate(item.created_at) }}</div>
                  <div class="item-actions">
                    <el-button size="small" type="primary" text @click="handleEdit(item)">
                      编辑
                    </el-button>
                    <el-popconfirm
                      title="确定删除该内容吗？此操作不可恢复。"
                      confirm-button-text="确定删除"
                      cancel-button-text="取消"
                      @confirm="handleDelete(item.id)"
                    >
                      <template #reference>
                        <el-button size="small" type="danger" text>删除</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ── 新增 / 编辑对话框 ─────────────────────────────── -->
    <el-dialog
      v-model="showDialog"
      :title="dialogTitle"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="90px" label-position="right">
        <!-- 标题 -->
        <el-form-item label="标题" required>
          <el-input
            v-model="form.title"
            placeholder="请输入标题（必填，最多 128 字）"
            maxlength="128"
            show-word-limit
            clearable
          />
        </el-form-item>

        <!-- 正文内容 -->
        <el-form-item label="正文内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="4"
            placeholder="请输入正文内容（选填）"
          />
        </el-form-item>

        <!-- 封面图片 -->
        <el-form-item label="封面图片">
          <!-- 已有封面预览 -->
          <div v-if="coverPreviewUrl" class="cover-preview">
            <img :src="coverPreviewUrl" alt="封面预览" />
            <span class="cover-preview-tip">当前封面（上传新图后替换）</span>
          </div>
          <!-- 上传控件：直接提交至后端，带 Authorization 请求头 -->
          <el-upload
            :action="'/api/upload'"
            :headers="uploadHeaders"
            accept="image/*"
            :show-file-list="true"
            :limit="1"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :on-exceed="() => ElMessage.warning('每次只能上传一张封面图')"
            list-type="picture"
          >
            <el-button size="small">{{ coverPreviewUrl ? '重新上传封面' : '选择封面图片' }}</el-button>
            <template #tip>
              <div class="upload-tip">支持 jpg / png / gif，上传后立即生效</div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 多张图片 -->
        <el-form-item label="内容图片">
          <!-- 已上传图片预览列表 -->
          <div v-if="imagePreviewUrls.length > 0" class="image-preview-list">
            <div v-for="(img, index) in imagePreviewUrls" :key="index" class="image-preview-item">
              <img :src="img.url" alt="图片预览" />
              <span class="image-remove-btn" @click="handleRemoveImage(index)">×</span>
            </div>
          </div>
          <!-- 上传控件 -->
          <el-upload
            :action="'/api/upload'"
            :headers="uploadHeaders"
            accept="image/*"
            :show-file-list="false"
            :on-success="handleImageUploadSuccess"
            :on-error="handleImageUploadError"
            multiple
          >
            <el-button size="small">选择图片（可多选）</el-button>
            <template #tip>
              <div class="upload-tip">支持 jpg / png / gif，可上传多张图片</div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 链接 URL -->
        <el-form-item label="链接 URL">
          <el-input
            v-model="form.link_url"
            placeholder="选填，填写后前端显示「了解详情」按钮"
            clearable
          />
        </el-form-item>

        <!-- 排序值 -->
        <el-form-item label="排序值">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
          <span class="form-hint">数字越小越靠前，默认 0</span>
        </el-form-item>

        <!-- 激活状态（编辑时才显示） -->
        <el-form-item v-if="isEdit" label="激活状态">
          <el-switch
            v-model="form.is_active"
            active-text="已激活（前台可见）"
            inactive-text="已下架（前台不显示）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="handleSave">
          {{ isEdit ? '保存修改' : '确认添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── 页面整体 ──────────────────────────────────────────────── */
.showcase-page {
  max-width: 1100px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin: 0;
}

/* ── Tab 内容区 ───────────────────────────────────────────── */
.tab-content {
  min-height: 200px;
  padding-top: 16px;
}

/* ── 卡片列表 ─────────────────────────────────────────────── */
.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: box-shadow var(--duration-fast, 0.15s);
}

.item-card:hover {
  box-shadow: var(--shadow-sm);
}

/* 封面缩略图 */
.item-cover {
  flex-shrink: 0;
  width: 120px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg-alt);
}

.item-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-alt);
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

/* 内容信息 */
.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-summary {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 4px;
}

.item-link {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 操作区域 */
.item-meta {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  min-width: 130px;
}

.meta-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sort-badge {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  background: var(--color-bg-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
}

.item-date {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.item-actions {
  display: flex;
  gap: 4px;
}

/* ── 表单 ─────────────────────────────────────────────────── */
.cover-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.cover-preview img {
  width: 120px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.cover-preview-tip {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.upload-tip {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.form-hint {
  margin-left: 10px;
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

/* ── 多图片预览 ─────────────────────────────────────────────── */
.image-preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.image-preview-item {
  position: relative;
  width: 120px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.image-preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.image-remove-btn:hover {
  background: rgba(192, 57, 43, 0.9);
}
</style>
