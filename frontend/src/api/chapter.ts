import http from './http'

export interface Chapter {
  id: number
  course_id: number | null
  course_name: string
  num: string
  title: string
  desc: string
  topics: string[]
  status: string
  sort_order: number
  videos: number
  docs: number
  progress: number
  types: { name: string; icon: string; count: number }[]
  total: number
  done: number
  accuracy: number
  day_of_week: string
  class_periods: string
  schedule_note: string
}

export interface ChapterManagePayload {
  num: string
  title: string
  desc: string
  topics: string[]
  status: string
  sort_order: number
  course_id: number | null
  day_of_week: string
  class_periods: string
  schedule_note: string
}

export function getChapters() {
  return http.get<any, Chapter[]>('/chapters')
}

export function getChapterContents(chapterId: number) {
  return http.get<any, any[]>(`/chapters/${chapterId}/contents`)
}

export function createChapter(data: ChapterManagePayload) {
  return http.post<any, { id: number }>('/chapters', data)
}

export function updateChapter(id: number, data: ChapterManagePayload) {
  return http.put<any, any>(`/chapters/${id}`, data)
}

export function deleteChapter(id: number) {
  return http.delete<any, any>(`/chapters/${id}`)
}

export function updateChapterSchedule(
  id: number,
  data: { course_id?: number | null; day_of_week?: string; class_periods?: string; schedule_note?: string },
) {
  return http.put<any, any>(`/chapters/${id}/schedule`, data)
}
