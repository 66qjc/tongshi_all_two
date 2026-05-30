import http from './http'

export function submitAnswer(questionId: number, userAnswer: string) {
  return http.post<any, any>('/quiz/submit', { question_id: questionId, user_answer: userAnswer })
}

export function getQuizHistory(limit = 10) {
  return http.get<any, any[]>('/quiz/history', { params: { limit } })
}

export function getQuizStats() {
  return http.get<any, { total_questions: number; questions_done: number; accuracy: number; today_count: number }>('/quiz/stats')
}

export function getCourseQuizStats(courseId: number) {
  return http.get<any, { course_id: number; questions_done: number; accuracy: number }>(`/quiz/stats/${courseId}`)
}
