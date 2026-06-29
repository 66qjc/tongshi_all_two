/** 答题进度草稿本地保存与恢复。 */
export interface QuizDraft {
  courseId: number | null
  currentQuestionId: number | null
  answeredQuestionIds: number[]
  answers: Record<number, string>
  results?: Record<number, boolean>
  updatedAt: number
}

const key = (courseId: number) => `quiz-draft:${courseId}`

export function loadQuizDraft(courseId: number | null): QuizDraft | null {
  if (!courseId) return null
  const raw = localStorage.getItem(key(courseId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as QuizDraft
  } catch {
    localStorage.removeItem(key(courseId))
    return null
  }
}

export function saveQuizDraft(draft: QuizDraft) {
  if (!draft.courseId) return
  localStorage.setItem(key(draft.courseId), JSON.stringify({ ...draft, updatedAt: Date.now() }))
}

export function clearQuizDraft(courseId: number | null) {
  if (!courseId) return
  localStorage.removeItem(key(courseId))
}
