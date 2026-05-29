import http from './http'

// 课程基础信息
export interface Course {
  id: number
  name: string
}

export interface Question {
  id: number
  type: 'choice' | 'fill'
  course_id: number
  course_name: string
  stem: string
  options: string[]
  answer: string
  explanation: string
}

export function getQuestions(params?: { type?: string; course_id?: number }) {
  return http.get<any, Question[]>('/questions', { params })
}

export function getCourseQuestions(courseId: number) {
  return http.get<any, Question[]>(`/questions/course/${courseId}`)
}

export function createQuestion(data: Partial<Question>) {
  return http.post<any, { id: number }>('/questions', data)
}

export function updateQuestion(id: number, data: Partial<Question>) {
  return http.put<any, any>(`/questions/${id}`, data)
}

export function deleteQuestion(id: number) {
  return http.delete<any, any>(`/questions/${id}`)
}

export function importQuestions(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<any, { success_count: number; fail_count: number; errors: { row: number; reason: string }[] }>('/questions/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

