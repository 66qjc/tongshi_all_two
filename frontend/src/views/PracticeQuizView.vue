<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Question } from '@/api/question'
import { getPracticeQuestions, submitAnswer as apiSubmitAnswer } from '@/api/quiz'
import { loadQuizDraft, saveQuizDraft, clearQuizDraft } from '@/composables/useQuizDraft'
import { getAnnouncementQuestions, recordCompletion } from '@/api/announcement'

const route = useRoute()
const router = useRouter()
const routeAnnouncementId = computed(() => {
  const raw = route.params.announcementId
  const value = Array.isArray(raw) ? raw[0] : raw
  const id = Number(value)
  return Number.isFinite(id) && id > 0 ? id : null
})
const courseId = computed(() => {
  const id = Number(route.params.courseId)
  return Number.isFinite(id) && id > 0 ? id : null
})
const questionIds = computed(() => {
  const raw = route.query.question_ids as string | undefined
  if (!raw) return null
  return raw.split(',').map(Number).filter(n => !isNaN(n))
})
const announcementId = computed(() => {
  if (routeAnnouncementId.value) return routeAnnouncementId.value
  const raw = route.query.announcement_id as string | undefined
  const id = raw ? Number(raw) : null
  return id && Number.isFinite(id) ? id : null
})
const isAssignmentMode = computed(() => announcementId.value !== null)
const enteredFromInbox = computed(() => route.name === 'practice-announcement')
const assignmentBackText = computed(() => enteredFromInbox.value ? '返回消息' : '返回上一页')
const randomCount = computed(() => {
  const raw = route.query.random as string | undefined
  return raw ? Number(raw) : null
})

const mockQuestions = ref<Question[]>([])
const loading = ref(true)
const loadError = ref('')
const assignmentTitle = ref('')

// Fisher-Yates 洗牌
function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    const current = a[i]!
    a[i] = a[j]!
    a[j] = current
  }
  return a
}

watch([courseId, announcementId, questionIds, randomCount], async () => {
  loading.value = true
  loadError.value = ''
  try {
    let qs: Question[]
    if (announcementId.value) {
      const data = await getAnnouncementQuestions(announcementId.value)
      assignmentTitle.value = data.announcement.title
      qs = data.questions
    } else {
      // 自由练习：全局题池，不再依赖 courseId
      qs = await getPracticeQuestions({
        ids: questionIds.value?.join(','),
        random: randomCount.value || undefined,
      })
      if (!qs.length) {
        loadError.value = '你尚未加入课程，或当前没有可练习的题目'
      }
    }
    mockQuestions.value = qs
  } catch (error) {
    mockQuestions.value = []
    loadError.value = error instanceof Error ? error.message : '题目加载失败'
  } finally {
    loading.value = false
  }
}, { immediate: true })

const currentIndex = ref(0)
const selectedOption = ref<string | null>(null)
const selectedOptions = ref<Set<string>>(new Set())
const fillAnswer = ref('')
const submitted = ref(false)
const answers = ref<(string | null)[]>([])
const results = ref<(boolean | null)[]>([])
/** 提交后由接口回填的正确答案/解析，避免拉题时预下发答案 */
const revealAnswers = ref<(string | null)[]>([])
const revealExplanations = ref<(string | null)[]>([])
const practiceFinished = ref(false)

// 加载题目后尝试恢复草稿（作业入口跳过）
watch(mockQuestions, (qs) => {
  if (!qs.length) return
  practiceFinished.value = false
  // 从作业入口进入时不恢复草稿，每次全新开始
  if (isAssignmentMode.value) {
    answers.value = qs.map(() => null)
    results.value = qs.map(() => null)
    revealAnswers.value = qs.map(() => null)
    revealExplanations.value = qs.map(() => null)
    currentIndex.value = 0
    resetState()
    return
  }
  const draft = loadQuizDraft(null, 'global')
  if (draft && draft.scope === 'global-practice') {
    // 恢复已答状态
    const restoredAnswers: (string | null)[] = qs.map(() => null)
    const restoredResults: (boolean | null)[] = qs.map(() => null)
    const restoredRevealAnswers: (string | null)[] = qs.map(() => null)
    const restoredRevealExplanations: (string | null)[] = qs.map(() => null)
    qs.forEach((q, idx) => {
      if (draft.answeredQuestionIds.includes(q.id) && draft.answers[q.id] !== undefined) {
        const wasCorrect = draft.results?.[q.id]
        if (wasCorrect === true) {
          // 仅恢复答对的题目状态；答错的题留空让用户重新作答，
          // 正确答案需重新提交后由接口回填，避免显示"回答错误"却看不到答案。
          restoredAnswers[idx] = draft.answers[q.id] ?? null
          restoredResults[idx] = true
        }
      }
    })
    answers.value = restoredAnswers
    results.value = restoredResults
    revealAnswers.value = restoredRevealAnswers
    revealExplanations.value = restoredRevealExplanations
    // 恢复到上次题目位置
    if (draft.currentQuestionId) {
      const idx = qs.findIndex(q => q.id === draft.currentQuestionId)
      if (idx >= 0) currentIndex.value = idx
    }
    resetState()
    // 恢复后全部答对：直接进入总结并清理残留草稿
    if (restoredResults.every(r => r === true)) {
      practiceFinished.value = true
      clearQuizDraft(null, 'global')
    }
  } else {
    answers.value = qs.map(() => null)
    results.value = qs.map(() => null)
    revealAnswers.value = qs.map(() => null)
    revealExplanations.value = qs.map(() => null)
    currentIndex.value = 0
    resetState()
  }
})

const currentQuestion = computed((): Question | null => mockQuestions.value[currentIndex.value] ?? null)
const totalQuestions = computed(() => mockQuestions.value.length)
const progress = computed(() => totalQuestions.value > 0 ? Math.round(((currentIndex.value + 1) / totalQuestions.value) * 100) : 0)
const allDone = computed(() => totalQuestions.value > 0 && results.value.every(r => r !== null))
const canSubmit = computed(() => {
  const q = currentQuestion.value
  if (!q) return false
  if (q.type === 'multi_choice') return selectedOptions.value.size > 0
  if (q.type === 'choice') return !!selectedOption.value
  return fillAnswer.value.trim().length > 0
})

const optionLabels = ['A', 'B', 'C', 'D']
const optionItems = computed(() => (currentQuestion.value?.options ?? []).map((text, index) => ({
  label: optionLabels[index] ?? String.fromCharCode(65 + index),
  text,
})))

async function submitAnswer() {
  const q = currentQuestion.value
  if (!q) return
  let userAnswer: string
  if (q.type === 'multi_choice') {
    if (selectedOptions.value.size === 0) return
    userAnswer = [...selectedOptions.value].sort().join('')
  } else if (q.type === 'choice') {
    if (!selectedOption.value) return
    userAnswer = selectedOption.value
  } else {
    if (!fillAnswer.value.trim()) return
    userAnswer = fillAnswer.value.trim()
  }
  const result = await apiSubmitAnswer(q.id, userAnswer, announcementId.value)
  answers.value[currentIndex.value] = userAnswer
  results.value[currentIndex.value] = result.is_correct
  revealAnswers.value[currentIndex.value] = result.correct_answer ?? ''
  revealExplanations.value[currentIndex.value] = result.explanation ?? ''
  persistDraft()
  if (result.is_correct) {
    if (currentIndex.value < totalQuestions.value - 1) {
      nextQuestion()
      return
    }
    if (isAssignmentMode.value) {
      await finishPractice()
      return
    }
    practiceFinished.value = true
    clearQuizDraft(null, 'global')
    return
  }
  submitted.value = true
}

function nextQuestion() {
  if (currentIndex.value < totalQuestions.value - 1) {
    currentIndex.value++
    resetState()
    persistDraft()
  }
}

function prevQuestion() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    resetState()
    persistDraft()
  }
}

function goToQuestion(index: number) {
  currentIndex.value = index
  resetState()
  persistDraft()
}

function resetState() {
  const q = currentQuestion.value
  if (!q) return
  const idx = currentIndex.value
  if (results.value[idx] !== null) {
    submitted.value = true
    const answer = answers.value[idx] ?? ''
    if (q.type === 'multi_choice') {
      selectedOptions.value = new Set(answer ? answer.split('') : [])
    }
    selectedOption.value = q.type === 'choice' ? answer : null
    fillAnswer.value = q.type === 'fill' ? answer : ''
  } else {
    submitted.value = false
    selectedOption.value = null
    selectedOptions.value = new Set()
    fillAnswer.value = ''
  }
}

function selectOption(label: string | undefined) {
  if (!submitted.value && label) {
    selectedOption.value = label
    // 单选题选择后立即自动提交（优化手机体验）
    if (currentQuestion.value?.type === 'choice') {
      submitAnswer()
    }
  }
}

function toggleMultiOption(label: string) {
  if (submitted.value) return
  const next = new Set(selectedOptions.value)
  if (next.has(label)) {
    next.delete(label)
  } else {
    next.add(label)
  }
  selectedOptions.value = next
}

const correctCount = computed(() => results.value.filter(r => r === true).length)

/** 完成练习：标记作业完成并展示总结 */
async function finishPractice() {
  if (practiceFinished.value) return
  if (announcementId.value) {
    try {
      await recordCompletion(announcementId.value)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '作业完成状态提交失败')
      return
    }
  }
  practiceFinished.value = true
  if (!isAssignmentMode.value) clearQuizDraft(null, 'global')
  else clearQuizDraft(courseId.value)
}

// 自由练习没有作业上下文，全部答完后直接展示总结。
// 存在答错题目时不自动切换，让学生先查看答案解析，手动点击"完成练习"。
watch(allDone, (done) => {
  if (done && !isAssignmentMode.value && !practiceFinished.value) {
    const allCorrect = results.value.every(r => r === true)
    if (allCorrect) {
      practiceFinished.value = true
      clearQuizDraft(null, 'global')
    }
  }
})

/** 保存当前答题草稿到 localStorage（自由练习用全局键） */
function persistDraft() {
  if (isAssignmentMode.value) return
  const qs = mockQuestions.value
  const answeredIds: number[] = []
  const answersMap: Record<number, string> = {}
  const resultsMap: Record<number, boolean> = {}
  qs.forEach((q, idx) => {
    if (answers.value[idx] !== null) {
      answeredIds.push(q.id)
      answersMap[q.id] = answers.value[idx]!
      if (results.value[idx] !== null) {
        resultsMap[q.id] = results.value[idx]!
      }
    }
  })
  saveQuizDraft({
    courseId: null,
    scope: 'global-practice',
    currentQuestionId: qs[currentIndex.value]?.id ?? null,
    answeredQuestionIds: answeredIds,
    answers: answersMap,
    results: resultsMap,
    updatedAt: Date.now(),
  }, 'global')
}

async function backToPrevious() {
  // 作业模式下全部答完但未点"完成练习"时，自动记录完成
  if (isAssignmentMode.value && allDone.value && !practiceFinished.value && announcementId.value) {
    await recordCompletion(announcementId.value).catch(() => {})
    practiceFinished.value = true
  }
  if (window.history.length > 1) {
    router.back()
    return
  }
  if (isAssignmentMode.value) {
    router.push(enteredFromInbox.value ? '/inbox' : '/practice/assignments')
    return
  }
  router.push('/practice')
}
</script>

<template>
  <div class="quiz-page">
    <section class="quiz-hero">
      <div class="container">
        <div class="quiz-header">
          <button class="back-btn" @click="backToPrevious">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ isAssignmentMode ? assignmentBackText : '退出练习' }}
          </button>
          <div class="quiz-info">
            <h2>{{ isAssignmentMode ? assignmentTitle || '作业练习' : '课程练习' }}</h2>
            <span class="quiz-progress-text">{{ currentIndex + 1 }} / {{ totalQuestions }} 题</span>
          </div>
        </div>
        <el-progress :percentage="progress" :stroke-width="6" :show-text="false" color="var(--color-practice)" />
      </div>
    </section>

    <!-- All done summary -->
    <section v-if="loading" class="summary-section">
      <div class="container">
        <div class="summary-card">
          <h2>题目加载中...</h2>
        </div>
      </div>
    </section>

    <section v-else-if="loadError" class="summary-section">
      <div class="container">
        <div class="summary-card">
          <h2>无法开始练习</h2>
          <p class="summary-text">{{ loadError }}</p>
          <div class="summary-actions">
            <button class="btn-retry" @click="backToPrevious">
              {{ isAssignmentMode ? assignmentBackText : '返回练习列表' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="totalQuestions === 0" class="summary-section">
      <div class="container">
        <div class="summary-card">
          <h2>暂无可练习题目</h2>
          <p class="summary-text">{{ isAssignmentMode ? '作业暂未配置题目，请联系老师。' : '该课程暂未配置题目，请稍后再试。' }}</p>
          <div class="summary-actions">
            <button class="btn-retry" @click="backToPrevious">
              {{ isAssignmentMode ? assignmentBackText : '返回练习列表' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="practiceFinished" class="summary-section">
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
          <p class="summary-text">正确率 {{ totalQuestions > 0 ? Math.round(correctCount / totalQuestions * 100) : 0 }}%</p>
          <div class="summary-actions">
            <button class="btn-retry" @click="backToPrevious">
              {{ isAssignmentMode ? assignmentBackText : '返回练习列表' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Question area -->
    <section v-else-if="currentQuestion" class="question-section">
      <div class="container">
        <div class="question-card">
          <div class="question-stem">
            <span class="q-label">Q{{ currentIndex + 1 }}.</span>
            {{ currentQuestion.stem }}
            <span v-if="currentQuestion.type === 'multi_choice'" class="multi-tag">（多选题）</span>
          </div>

          <!-- Multi choice question -->
          <div v-if="currentQuestion.type === 'multi_choice'" class="options-list">
            <div
              v-for="item in optionItems"
              :key="item.label"
              class="option-item"
              :class="{
                selected: selectedOptions.has(item.label),
                correct: submitted && (revealAnswers[currentIndex] || '').includes(item.label),
                wrong: submitted && selectedOptions.has(item.label) && !(revealAnswers[currentIndex] || '').includes(item.label),
              }"
              @click="toggleMultiOption(item.label)"
            >
              <span class="option-check">{{ selectedOptions.has(item.label) ? '☑' : '☐' }}</span>
              <span class="option-label">{{ item.label }}</span>
              <span class="option-text">{{ item.text }}</span>
            </div>
            <div v-if="!submitted" class="multi-hint">可选择多个选项，选好后点击"提交答案"</div>
          </div>

          <!-- Choice question -->
          <div v-else-if="currentQuestion.type === 'choice'" class="options-list">
            <div
              v-for="item in optionItems"
              :key="item.label"
              class="option-item"
              :class="{
                selected: selectedOption === item.label,
                correct: submitted && item.label === revealAnswers[currentIndex],
                wrong: submitted && selectedOption === item.label && item.label !== revealAnswers[currentIndex],
              }"
              @click="selectOption(item.label)"
            >
              <span class="option-label">{{ item.label }}</span>
              <span class="option-text">{{ item.text }}</span>
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
            <button class="btn-submit" :disabled="!canSubmit" @click="submitAnswer">
              提交答案
            </button>
          </div>

          <!-- Result feedback -->
          <div v-if="submitted && results[currentIndex] === false" class="result-box" :class="results[currentIndex] ? 'correct' : 'wrong'">
            <div class="result-header">
              <svg v-if="results[currentIndex]" width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>{{ results[currentIndex] ? '回答正确' : '回答错误' }}</span>
            </div>
            <div v-if="!results[currentIndex] && revealAnswers[currentIndex]" class="result-answer">
              正确答案：<strong>{{ revealAnswers[currentIndex] }}</strong>
            </div>
            <div v-if="revealExplanations[currentIndex]" class="result-explanation">
              <span class="explanation-label">解析：</span>{{ revealExplanations[currentIndex] }}
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
            <button v-if="currentIndex === totalQuestions - 1 && submitted" class="nav-btn btn-finish" @click="finishPractice">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              完成练习
            </button>
            <button v-else class="nav-btn" :disabled="currentIndex === totalQuestions - 1" @click="nextQuestion">
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
  padding-top: 60px;
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
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  text-align: right;
  text-wrap: balance;
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
  border-radius: var(--radius-md);
  max-width: 480px;
  margin: 0 auto;
}

.summary-icon {
  color: var(--color-practice);
  margin-bottom: var(--space-lg);
}

.summary-card h2 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
  text-wrap: balance;
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
  border-radius: var(--radius-md);
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

.option-check {
  font-size: 1.1rem;
  width: 24px;
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.option-item.selected .option-check {
  color: var(--color-practice);
}

.option-item.correct .option-check {
  color: #10b981;
}

.option-item.wrong .option-check {
  color: #ef4444;
}

.multi-tag {
  font-size: 0.8rem;
  font-weight: 600;
  color: #d97706;
  margin-left: 4px;
  white-space: nowrap;
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

/* Multi-choice checkbox */
.option-checkbox {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-border);
  border-radius: 4px;
  flex-shrink: 0;
  transition: all var(--duration-fast);
}

.option-checkbox.checked {
  border-color: var(--color-practice);
  background: var(--color-practice);
  color: white;
}

.option-item.correct .option-checkbox {
  border-color: #10b981;
  background: #10b981;
  color: white;
}

.option-item.wrong .option-checkbox {
  border-color: #ef4444;
  background: #ef4444;
  color: white;
}

.multi-hint {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: var(--space-sm);
  text-align: center;
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

.btn-submit:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.btn-finish {
  color: white;
  background: #10b981;
  border-color: #10b981;
}

.btn-finish:hover {
  color: white;
  background: #059669;
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
