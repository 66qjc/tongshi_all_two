<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getClasses, getClassStudents, type ClassInfo } from '@/api/class'

interface Student {
  id: string
  name: string
  major: string
}

const classes = ref<ClassInfo[]>([])
const selectedClassId = ref<number | null>(null)
const students = ref<Student[]>([])
const availableStudents = ref<Student[]>([])
const calledStudents = ref<Student[]>([])
const currentStudent = ref<Student | null>(null)
const isAnimating = ref(false)
const showResult = ref(false)
let studentRequestId = 0
let animationTimer: ReturnType<typeof setInterval> | null = null

const calledCount = computed(() => calledStudents.value.length)
const totalCount = computed(() => students.value.length)
const calledPercentage = computed(() =>
  totalCount.value > 0 ? Math.round((calledCount.value / totalCount.value) * 100) : 0
)

onMounted(async () => {
  try {
    const result = await getClasses()
    classes.value = result
    if (result.length > 0) {
      selectedClassId.value = result[0]!.id
      await loadStudents()
    } else {
      clearStudentState()
    }
  } catch (error) {
    ElMessage.error('加载班级列表失败')
  }
})

function clearStudentState() {
  students.value = []
  availableStudents.value = []
  calledStudents.value = []
  currentStudent.value = null
  showResult.value = false
}

function stopAnimation() {
  if (animationTimer !== null) {
    clearInterval(animationTimer)
    animationTimer = null
  }
  isAnimating.value = false
}

async function loadStudents() {
  if (!selectedClassId.value) {
    studentRequestId++
    clearStudentState()
    return
  }
  const currentRequestId = ++studentRequestId
  try {
    const result = await getClassStudents(selectedClassId.value)
    if (currentRequestId !== studentRequestId) return
    students.value = result.map(student => ({
      id: student.id,
      name: student.name,
      major: student.major || '',
    }))
    availableStudents.value = [...students.value]
    calledStudents.value = []
    currentStudent.value = null
    showResult.value = false
  } catch (error) {
    if (currentRequestId !== studentRequestId) return
    clearStudentState()
    ElMessage.error('加载学生列表失败')
  }
}

function pickRandomStudent() {
  if (availableStudents.value.length === 0) {
    ElMessage.warning('所有学生已被点过，请重置')
    return
  }

  isAnimating.value = true
  showResult.value = false

  // 动画效果：快速切换名字
  let count = 0
  const maxCount = 20
  animationTimer = setInterval(() => {
    const randomIndex = Math.floor(Math.random() * availableStudents.value.length)
    currentStudent.value = availableStudents.value[randomIndex]!
    count++
    if (count >= maxCount) {
      stopAnimation()
      // 最终选中
      const finalIndex = Math.floor(Math.random() * availableStudents.value.length)
      const picked = availableStudents.value[finalIndex]!
      currentStudent.value = picked
      calledStudents.value.push(picked)
      availableStudents.value.splice(finalIndex, 1)
      showResult.value = true
    }
  }, 80)
}

function resetCalledList() {
  if (calledStudents.value.length === 0) {
    ElMessage.info('当前没有已点名记录')
    return
  }
  availableStudents.value = [...students.value]
  calledStudents.value = []
  currentStudent.value = null
  showResult.value = false
  ElMessage.success('已重置点名列表')
}

async function handleClassChange() {
  stopAnimation()
  clearStudentState()
  await loadStudents()
}

onBeforeUnmount(() => {
  studentRequestId++
  stopAnimation()
})
</script>

<template>
  <div class="random-picker">
    <div class="picker-header">
      <h1>AI 随机点名</h1>
      <p class="subtitle">课堂互动工具 · 公平随机抽取学生</p>
    </div>

    <div class="picker-controls">
      <div class="control-group">
        <label>选择班级</label>
        <el-select
          v-model="selectedClassId"
          placeholder="选择班级"
          @change="handleClassChange"
          size="large"
          style="width: 100%"
        >
          <el-option
            v-for="cls in classes"
            :key="cls.id"
            :label="`${cls.name} (${cls.course_name || ''})`"
            :value="cls.id"
          />
        </el-select>
      </div>

      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">班级人数</span>
          <span class="stat-value">{{ totalCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已点名</span>
          <span class="stat-value highlight">{{ calledCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">剩余</span>
          <span class="stat-value">{{ availableStudents.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">完成度</span>
          <span class="stat-value">{{ calledPercentage }}%</span>
        </div>
      </div>

      <el-progress
        :percentage="calledPercentage"
        :stroke-width="8"
        :show-text="false"
        color="var(--color-primary)"
      />
    </div>

    <div class="result-display">
      <div v-if="!showResult && !isAnimating" class="result-placeholder">
        <div class="placeholder-icon">🎲</div>
        <p>点击下方按钮开始随机抽取</p>
      </div>
      <div v-else class="result-card" :class="{ animating: isAnimating }">
        <div class="student-name">{{ currentStudent?.name || '-' }}</div>
        <div class="student-info">
          <span v-if="currentStudent?.major">{{ currentStudent.major }}</span>
          <span v-if="currentStudent?.id">学号: {{ currentStudent.id }}</span>
        </div>
      </div>
    </div>

    <div class="action-buttons">
      <button
        class="btn btn-primary"
        @click="pickRandomStudent"
        :disabled="isAnimating || availableStudents.length === 0"
      >
        <span v-if="isAnimating">抽取中...</span>
        <span v-else>🎯 随机点名</span>
      </button>
      <button
        class="btn btn-secondary"
        @click="resetCalledList"
        :disabled="isAnimating || calledCount === 0"
      >
        🔄 重置列表
      </button>
    </div>

    <div class="called-list-section">
      <div class="section-header">
        <h3>已点名单 ({{ calledCount }})</h3>
      </div>
      <div v-if="calledStudents.length === 0" class="empty-state">
        暂无点名记录
      </div>
      <div v-else class="called-grid">
        <div
          v-for="(student, index) in calledStudents"
          :key="student.id"
          class="called-item"
        >
          <span class="called-index">{{ index + 1 }}</span>
          <span class="called-name">{{ student.name }}</span>
          <span class="called-major">{{ student.major }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.random-picker {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--space-2xl) var(--space-lg);
}

.picker-header {
  text-align: center;
  margin-bottom: var(--space-2xl);
}

.picker-header h1 {
  font-family: var(--font-sans);
  font-size: 2rem;
  font-weight: 900;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.subtitle {
  color: var(--color-text-secondary);
  font-size: var(--text-body);
}

.picker-controls {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  margin-bottom: var(--space-xl);
}

.control-group {
  margin-bottom: var(--space-lg);
}

.control-group label {
  display: block;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  font-size: 0.9rem;
}

.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--color-text);
}

.stat-value.highlight {
  color: var(--color-primary);
}

.result-display {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-xl);
}

.result-placeholder {
  text-align: center;
  color: var(--color-text-muted);
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: var(--space-md);
  opacity: 0.5;
}

.result-card {
  background: var(--color-bg-card);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-xl);
  padding: var(--space-2xl);
  text-align: center;
  min-width: 360px;
  box-shadow: var(--shadow-lg);
  transition: transform 0.3s var(--ease-out);
}

.result-card.animating {
  animation: pulse 0.08s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.student-name {
  font-size: 2.5rem;
  font-weight: 900;
  color: var(--color-primary);
  margin-bottom: var(--space-md);
  font-family: var(--font-sans);
}

.student-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
}

.btn {
  flex: 1;
  padding: var(--space-lg) var(--space-xl);
  font-size: 1.1rem;
  font-weight: 700;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  box-shadow: 0 4px 12px rgba(45, 90, 110, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-light);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(45, 90, 110, 0.4);
}

.btn-secondary {
  background: var(--color-bg-alt);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-card);
  border-color: var(--color-primary);
}

.called-list-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
}

.section-header h3 {
  font-family: var(--font-sans);
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-2xl);
}

.called-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-sm);
}

.called-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
}

.called-index {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-full);
  font-size: 0.7rem;
  font-weight: 700;
}

.called-name {
  flex: 1;
  font-weight: 700;
  color: var(--color-text);
  font-size: 0.9rem;
}

.called-major {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
  }

  .result-card {
    min-width: auto;
    width: 100%;
  }

  .called-grid {
    grid-template-columns: 1fr;
  }
}
</style>
