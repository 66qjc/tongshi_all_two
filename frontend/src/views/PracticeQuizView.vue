<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCourseQuestions, type Question } from '@/api/question'
import { submitAnswer as apiSubmitAnswer } from '@/api/quiz'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => Number(route.params.courseId) || 1)

const mockQuestions = ref<Question[]>([])
const loading = ref(true)

watch(courseId, async () => {
  loading.value = true
  try {
    mockQuestions.value = await getCourseQuestions(courseId.value)
  } finally {
    loading.value = false
  }
}, { immediate: true })

const currentIndex = ref(0)
const selectedOption = ref<string | null>(null)
const fillAnswer = ref('')
const submitted = ref(false)
const answers = ref<(string | null)[]>([])
const results = ref<(boolean | null)[]>([])

watch(mockQuestions, (qs) => {
  answers.value = qs.map(() => null)
  results.value = qs.map(() => null)
})

const currentQuestion = computed((): Question => mockQuestions.value[currentIndex.value]!)
const totalQuestions = computed(() => mockQuestions.value.length)
const progress = computed(() => Math.round(((currentIndex.value + 1) / totalQuestions.value) * 100))
const allDone = computed(() => results.value.every(r => r !== null))

const optionLabels = ['A', 'B', 'C', 'D']

async function submitAnswer() {
  const q = currentQuestion.value
  let userAnswer: string
  if (q.type === 'choice') {
    if (!selectedOption.value) return
    userAnswer = selectedOption.value
  } else {
    if (!fillAnswer.value.trim()) return
    userAnswer = fillAnswer.value.trim()
  }
  const result = await apiSubmitAnswer(q.id, userAnswer)
  answers.value[currentIndex.value] = userAnswer
  results.value[currentIndex.value] = result.is_correct
  submitted.value = true
}

function nextQuestion() {
  if (currentIndex.value < totalQuestions.value - 1) {
    currentIndex.value++
    resetState()
  }
}

function prevQuestion() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    resetState()
  }
}

function goToQuestion(index: number) {
  currentIndex.value = index
  resetState()
}

function resetState() {
  const idx = currentIndex.value
  if (results.value[idx] !== null) {
    submitted.value = true
    selectedOption.value = currentQuestion.value.type === 'choice' ? (answers.value[idx] ?? null) : null
    fillAnswer.value = currentQuestion.value.type === 'fill' ? (answers.value[idx] ?? '') : ''
  } else {
    submitted.value = false
    selectedOption.value = null
    fillAnswer.value = ''
  }
}

function selectOption(label: string | undefined) {
  if (!submitted.value && label) selectedOption.value = label
}

const correctCount = computed(() => results.value.filter(r => r === true).length)
</script>

<template>
  <div class="quiz-page">
    <section class="quiz-hero">
      <div class="container">
        <div class="quiz-header">
          <button class="back-btn" @click="router.push('/practice')">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            退出练习
          </button>
          <div class="quiz-info">
            <h2>课程练习</h2>
            <span class="quiz-progress-text">{{ currentIndex + 1 }} / {{ totalQuestions }} 题</span>
          </div>
        </div>
        <el-progress :percentage="progress" :stroke-width="6" :show-text="false" color="var(--color-practice)" />
      </div>
    </section>

    <!-- All done summary -->
    <section v-if="allDone" class="summary-section">
      <div class="container">
        <div class="summary-card">
          <div class="summary-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h2>练习完成！</h2>
          <div class="summary-score">
            <span class="score-num">{{ correctCount }}</span>
            <span class="score-sep">/</span>
            <span class="score-total">{{ totalQuestions }}</span>
          </div>
          <p class="summary-text">正确率 {{ Math.round(correctCount / totalQuestions * 100) }}%</p>
          <div class="summary-actions">
            <button class="btn-retry" @click="router.push('/practice')">返回练习列表</button>
          </div>
        </div>
      </div>
    </section>

    <!-- Question area -->
    <section v-else class="question-section">
      <div class="container">
        <div class="question-card">
          <div class="question-stem">
            <span class="q-label">Q{{ currentIndex + 1 }}.</span>
            {{ currentQuestion.stem }}
          </div>

          <!-- Choice question -->
          <div v-if="currentQuestion.type === 'choice'" class="options-list">
            <div
              v-for="(opt, i) in currentQuestion.options"
              :key="i"
              class="option-item"
              :class="{
                selected: selectedOption === optionLabels[i],
                correct: submitted && optionLabels[i] === currentQuestion.answer,
                wrong: submitted && selectedOption === optionLabels[i] && optionLabels[i] !== currentQuestion.answer,
              }"
              @click="selectOption(optionLabels[i])"
            >
              <span class="option-label">{{ optionLabels[i] }}</span>
              <span class="option-text">{{ opt }}</span>
            </div>
          </div>

          <!-- Fill question -->
          <div v-else class="fill-area">
            <el-input
              v-model="fillAnswer"
              placeholder="请输入答案..."
              size="large"
              :disabled="submitted"
              @keyup.enter="!submitted && submitAnswer()"
            />
          </div>

          <!-- Submit button -->
          <div v-if="!submitted" class="action-bar">
            <button class="btn-submit" @click="submitAnswer">
              提交答案
            </button>
          </div>

          <!-- Result feedback -->
          <div v-if="submitted" class="result-box" :class="results[currentIndex] ? 'correct' : 'wrong'">
            <div class="result-header">
              <svg v-if="results[currentIndex]" width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>{{ results[currentIndex] ? '回答正确' : '回答错误' }}</span>
            </div>
            <div v-if="!results[currentIndex]" class="result-answer">
              正确答案：<strong>{{ currentQuestion.answer }}</strong>
            </div>
            <div class="result-explanation">
              <span class="explanation-label">解析：</span>{{ currentQuestion.explanation }}
            </div>
          </div>

          <!-- Navigation -->
          <div class="nav-bar">
            <button class="nav-btn" :disabled="currentIndex === 0" @click="prevQuestion">
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              上一题
            </button>
            <button class="nav-btn" :disabled="currentIndex === totalQuestions - 1" @click="nextQuestion">
              下一题
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                <path d="M4 10h12m-4-4l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Question number bar -->
        <div class="q-nav-bar">
          <button
            v-for="(_, i) in mockQuestions"
            :key="i"
            class="q-nav-item"
            :class="{
              current: i === currentIndex,
              correct: results[i] === true,
              wrong: results[i] === false,
            }"
            @click="goToQuestion(i)"
          >
            {{ i + 1 }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.quiz-page {
  padding-top: 64px;
  min-height: 100vh;
  background: var(--color-bg-alt);
}

.quiz-hero {
  padding: var(--space-xl) 0;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: color var(--duration-fast);
}

.back-btn:hover {
  color: var(--color-practice);
}

.quiz-info h2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  text-align: right;
}

.quiz-progress-text {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  text-align: right;
  display: block;
}

/* Summary */
.summary-section {
  padding: var(--space-4xl) 0;
}

.summary-card {
  text-align: center;
  padding: var(--space-3xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  max-width: 480px;
  margin: 0 auto;
}

.summary-icon {
  color: var(--color-practice);
  margin-bottom: var(--space-lg);
}

.summary-card h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.summary-score {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--space-xs);
  margin-bottom: var(--space-sm);
}

.score-num {
  font-size: 3rem;
  font-weight: 900;
  color: var(--color-practice);
  font-family: var(--font-mono);
}

.score-sep {
  font-size: 1.5rem;
  color: var(--color-text-muted);
}

.score-total {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}

.summary-text {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
}

.btn-retry {
  padding: 0.7rem 2rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: var(--color-practice);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-retry:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Question */
.question-section {
  padding: var(--space-2xl) 0;
}

.question-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
  max-width: 720px;
  margin: 0 auto var(--space-xl);
  animation: fadeIn 0.3s var(--ease-out);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.question-stem {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.7;
  margin-bottom: var(--space-xl);
}

.q-label {
  color: var(--color-practice);
  font-weight: 800;
  margin-right: var(--space-xs);
}

/* Options */
.options-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin-bottom: var(--space-xl);
}

.option-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.option-item:hover:not(.correct):not(.wrong) {
  border-color: var(--color-practice-light);
  background: var(--color-practice-bg);
}

.option-item.selected {
  border-color: var(--color-practice);
  background: var(--color-practice-bg);
}

.option-item.correct {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}

.option-item.wrong {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

.option-label {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.option-item.selected .option-label {
  color: white;
  background: var(--color-practice);
}

.option-item.correct .option-label {
  color: white;
  background: #10b981;
}

.option-item.wrong .option-label {
  color: white;
  background: #ef4444;
}

.option-text {
  font-size: 0.95rem;
  color: var(--color-text);
}

/* Fill */
.fill-area {
  margin-bottom: var(--space-xl);
}

/* Actions */
.action-bar {
  text-align: center;
  margin-bottom: var(--space-lg);
}

.btn-submit {
  padding: 0.7rem 2.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: white;
  background: var(--color-practice);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-submit:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Result */
.result-box {
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
}

.result-box.correct {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.result-box.wrong {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: var(--space-sm);
}

.result-box.correct .result-header {
  color: #10b981;
}

.result-box.wrong .result-header {
  color: #ef4444;
}

.result-answer {
  font-size: 0.9rem;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.result-explanation {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.explanation-label {
  font-weight: 600;
  color: var(--color-text);
}

/* Nav */
.nav-bar {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-practice);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.nav-btn:hover:not(:disabled) {
  background: var(--color-practice-bg);
}

.nav-btn:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

/* Question nav bar */
.q-nav-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  justify-content: center;
  max-width: 720px;
  margin: 0 auto;
}

.q-nav-item {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.q-nav-item:hover {
  border-color: var(--color-practice);
}

.q-nav-item.current {
  color: white;
  background: var(--color-practice);
  border-color: var(--color-practice);
}

.q-nav-item.correct {
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
}

.q-nav-item.wrong {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}

@media (max-width: 768px) {
  .quiz-header {
    flex-direction: column;
    gap: var(--space-sm);
    align-items: flex-start;
  }

  .quiz-info {
    text-align: left;
  }

  .quiz-info h2 {
    text-align: left;
  }

  .quiz-progress-text {
    text-align: left;
  }

  .question-card {
    padding: var(--space-lg);
  }
}
</style>
