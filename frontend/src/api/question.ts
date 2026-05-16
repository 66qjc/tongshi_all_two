import http from './http'

export interface Question {
  id: number
  type: 'choice' | 'fill'
  chapter_id: number
  stem: string
  options: string[]
  answer: string
  explanation: string
}

export function getQuestions(params?: { chapter_id?: number; type?: string }) {
  return http.get<any, Question[]>('/questions', { params })
}

export function getChapterQuestions(chapterId: number) {
  return http.get<any, Question[]>(`/questions/chapter/${chapterId}`)
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
