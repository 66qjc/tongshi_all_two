import http from './http'

// 课程基础信息
export interface Course {
  id: number
  name: string
}

export interface Question {
  id: number
  type: 'choice' | 'fill'
  chapter_id: number
  chapter_name: string   // 后端返回的章节名称
  course_id: number | null  // 后端返回的课程ID
  course_name: string    // 后端返回的课程名称
  stem: string
  options: string[]
  answer: string
  explanation: string
}

export function getQuestions(params?: { chapter_id?: number; type?: string; course_id?: number }) {
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

// 获取课程列表
export function getCourses() {
  return http.get<any, Course[]>('/questions/courses')
}

// 新建课程（供课程管理页面复用）
export function createCourse(data: { name: string }) {
  return http.post<any, { id: number }>('/questions/courses', data)
}
