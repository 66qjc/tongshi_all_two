<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAllMaterials, createMaterial, deleteMaterial as apiDeleteMaterial, type Material } from '@/api/material'
import { getChapters, updateChapterSchedule, type Chapter } from '@/api/chapter'

const materials = ref<Material[]>([])
const chapters = ref<Chapter[]>([])
const loading = ref(true)

const chapterNames = ['人工智能概述', '计算机基础知识', 'AI 理论基础', 'AI 工具使用', 'AI 前沿与应用', 'AI 伦理与未来']
const chapterIdMap: Record<string, number> = {}
chapterNames.forEach((ch, i) => { chapterIdMap[ch] = i + 1 })

const filterChapter = ref('')
const dialogVisible = ref(false)

const newMaterial = reactive({
  chapter: '',
  type: 'video' as 'video' | 'pdf',
  title: '',
})

const filteredMaterials = ref<Material[]>([])

const scheduleDialogVisible = ref(false)
const scheduleChapter = ref<Chapter | null>(null)
const scheduleForm = reactive({
  day_of_week: '',
  class_periods: '',
  schedule_note: '',
})

const dayOptions = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

onMounted(async () => {
  try {
    const [m, c] = await Promise.all([getAllMaterials(), getChapters()])
    materials.value = m
    chapters.value = c
    filteredMaterials.value = m
  } finally {
    loading.value = false
  }
})

function handleFilter() {
  filteredMaterials.value = filterChapter.value
    ? materials.value.filter(m => m.chapter === filterChapter.value)
    : materials.value
}

function openUpload() {
  newMaterial.chapter = ''
  newMaterial.type = 'video'
  newMaterial.title = ''
  dialogVisible.value = true
}

async function handleUpload() {
  if (!newMaterial.chapter || !newMaterial.title.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    const chapterId = chapterIdMap[newMaterial.chapter] || 1
    await createMaterial({ chapter_id: chapterId, type: newMaterial.type, title: newMaterial.title.trim() })
    materials.value = await getAllMaterials()
    dialogVisible.value = false
    handleFilter()
    ElMessage.success('资料上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该资料？', '提示', { type: 'warning' })
    await apiDeleteMaterial(id)
    materials.value = materials.value.filter(m => m.id !== id)
    handleFilter()
    ElMessage.success('已删除')
  } catch {}
}

function openSchedule(ch: Chapter) {
  scheduleChapter.value = ch
  Object.assign(scheduleForm, {
    day_of_week: ch.day_of_week || '',
    class_periods: ch.class_periods || '',
    schedule_note: ch.schedule_note || '',
  })
  scheduleDialogVisible.value = true
}

async function handleSaveSchedule() {
  if (!scheduleChapter.value) return
  try {
    await updateChapterSchedule(scheduleChapter.value.id, scheduleForm)
    // Update local
    scheduleChapter.value.day_of_week = scheduleForm.day_of_week
    scheduleChapter.value.class_periods = scheduleForm.class_periods
    scheduleChapter.value.schedule_note = scheduleForm.schedule_note
    ElMessage.success('时间安排已保存')
    scheduleDialogVisible.value = false
  } catch {
    ElMessage.error('保存失败')
  }
}
</script>

<template>
  <div class="materials-page">
    <div class="page-header">
      <h1>资料管理</h1>
      <el-button type="primary" round @click="openUpload">上传资料</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterChapter" placeholder="全部章节" clearable size="default"
                 style="width: 200px" @change="handleFilter">
        <el-option v-for="ch in chapterNames" :key="ch" :label="ch" :value="ch" />
      </el-select>
      <span class="filter-count">共 {{ filteredMaterials.length }} 个资料</span>
    </div>

    <!-- Chapter schedule -->
    <div class="schedule-section" v-if="chapters.length > 0">
      <h2 class="section-title">课程时间安排</h2>
      <div class="schedule-grid">
        <div v-for="ch in chapters" :key="ch.id" class="schedule-card" @click="openSchedule(ch)">
          <span class="schedule-num">{{ ch.num }}</span>
          <div class="schedule-info">
            <span class="schedule-name">{{ ch.title }}</span>
            <span v-if="ch.day_of_week" class="schedule-time">
              {{ ch.day_of_week }} 第{{ ch.class_periods }}节
              <span v-if="ch.schedule_note" class="schedule-note">({{ ch.schedule_note }})</span>
            </span>
            <span v-else class="schedule-empty">未设置时间</span>
          </div>
          <span class="schedule-edit">编辑</span>
        </div>
      </div>
    </div>

    <el-table :data="filteredMaterials" stripe style="width: 100%">
      <el-table-column prop="title" label="文件名称" min-width="200" />
      <el-table-column prop="chapter" label="所属章节" width="160" />
      <el-table-column prop="type" label="类型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.type === 'video' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'video' ? '视频' : 'PDF' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="100" />
      <el-table-column prop="date" label="上传时间" width="120" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" text size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Upload dialog -->
    <el-dialog v-model="dialogVisible" title="上传资料" width="480px">
      <div class="form-group">
        <label>所属章节</label>
        <el-select v-model="newMaterial.chapter" placeholder="选择章节" size="large" style="width: 100%">
          <el-option v-for="ch in chapterNames" :key="ch" :label="ch" :value="ch" />
        </el-select>
      </div>
      <div class="form-group">
        <label>资料类型</label>
        <el-radio-group v-model="newMaterial.type" size="large">
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="pdf">PDF</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>资料标题</label>
        <el-input v-model="newMaterial.title" placeholder="输入资料标题" size="large" />
      </div>
      <div class="form-group">
        <label>文件</label>
        <div class="upload-zone-small">
          <span>点击或拖拽上传文件</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- Schedule dialog -->
    <el-dialog v-model="scheduleDialogVisible" :title="scheduleChapter ? `设置时间: ${scheduleChapter.title}` : '设置时间'" width="420px">
      <div class="form-group">
        <label>星期</label>
        <el-select v-model="scheduleForm.day_of_week" placeholder="选择星期" size="large" style="width: 100%" clearable>
          <el-option v-for="d in dayOptions" :key="d" :label="d" :value="d" />
        </el-select>
      </div>
      <div class="form-group">
        <label>节次</label>
        <el-input v-model="scheduleForm.class_periods" placeholder="如：1-3 或 5" size="large" />
      </div>
      <div class="form-group">
        <label>备注</label>
        <el-input v-model="scheduleForm.schedule_note" placeholder="如：双周" size="large" />
      </div>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSchedule">保存</el-button>
      </template>
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

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.filter-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
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

.upload-zone-small {
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone-small:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.schedule-section {
  margin-bottom: var(--space-xl);
  padding-bottom: var(--space-xl);
  border-bottom: 1px solid var(--color-border-light);
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-sm);
}

.schedule-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.schedule-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-xs);
}

.schedule-num {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-border);
  font-family: var(--font-mono);
  flex-shrink: 0;
  width: 32px;
}

.schedule-info {
  flex: 1;
  min-width: 0;
}

.schedule-name {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

.schedule-time {
  display: block;
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 500;
}

.schedule-note {
  color: var(--color-text-muted);
  font-weight: 400;
}

.schedule-empty {
  display: block;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.schedule-edit {
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 500;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .schedule-grid {
    grid-template-columns: 1fr;
  }
}
</style>
