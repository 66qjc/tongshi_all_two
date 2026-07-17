import http from './http'
import type { Question } from './question'

export function submitAnswer(questionId: number, userAnswer: string, announcementId?: number | null) {
  return http.post<any, any>('/quiz/submit', {
    question_id: questionId,
    user_answer: userAnswer,
    ...(announcementId ? { announcement_id: announcementId } : {}),
  })
}

export function getQuizHistory(limit = 10) {
  return http.get<any, any[]>('/quiz/history', { params: { limit } })
}

export function getQuizStats() {
  return http.get<any, { total_questions: number; questions_done: number; accuracy: number; today_count: number }>('/quiz/stats')
}

export function getCourseQuizStats(courseId: number) {
  return http.get<any, { course_id: number; questions_done: number; accuracy: number; total_questions?: number }>(`/quiz/stats/${courseId}`)
}

/** 学生全局自由练习题池（隐藏答案与解析） */
export function getPracticeQuestions(params?: { ids?: string; random?: number }) {
  return http.get<any, Question[]>('/quiz/questions', { params })
}
