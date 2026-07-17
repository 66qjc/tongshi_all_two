/** 答题进度草稿本地保存与恢复。 */
export interface QuizDraft {
  courseId: number | null
  scope?: 'global-practice' | `course:${number}`
  currentQuestionId: number | null
  answeredQuestionIds: number[]
  answers: Record<number, string>
  results?: Record<number, boolean>
  updatedAt: number
}

const GLOBAL_SCOPE = 'global-practice'
const globalKey = 'quiz-draft:global-practice'
const courseKey = (courseId: number) => `quiz-draft:${courseId}`

export function loadQuizDraft(courseId: number | null, scope: 'global' | 'course' = 'course'): QuizDraft | null {
  // 自由练习统一使用全局作用域；旧课程草稿不迁移也不读取
  if (scope === 'global') {
    const raw = localStorage.getItem(globalKey)
    if (!raw) return null
    try {
      return JSON.parse(raw) as QuizDraft
    } catch {
      localStorage.removeItem(globalKey)
      return null
    }
  }
  if (!courseId) return null
  const raw = localStorage.getItem(courseKey(courseId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as QuizDraft
  } catch {
    localStorage.removeItem(courseKey(courseId))
    return null
  }
}

export function saveQuizDraft(draft: QuizDraft, scope: 'global' | 'course' = 'course') {
  if (scope === 'global' || draft.scope === GLOBAL_SCOPE) {
    localStorage.setItem(globalKey, JSON.stringify({
      ...draft,
      courseId: null,
      scope: GLOBAL_SCOPE,
      updatedAt: Date.now(),
    }))
    return
  }
  if (!draft.courseId) return
  localStorage.setItem(courseKey(draft.courseId), JSON.stringify({ ...draft, updatedAt: Date.now() }))
}

export function clearQuizDraft(courseId: number | null, scope: 'global' | 'course' = 'course') {
  if (scope === 'global') {
    localStorage.removeItem(globalKey)
    return
  }
  if (!courseId) return
  localStorage.removeItem(courseKey(courseId))
}
