import http from './http'

export interface LessonProgressDetail {
  lesson_id: number
  course_id: number
  title: string
  status: 'not_started' | 'in_progress' | 'completed'
  progress_percent: number
  last_position: number
  duration_seconds: number
  view_count: number
  is_fast_completion: boolean
  first_viewed_at?: string | null
  last_viewed_at?: string | null
  completed_at?: string | null
}

export interface CourseProgress {
  last_lesson_id: number | null
  total_lessons: number
  completed_lessons: number
  total_duration: number
  completion_rate: number
  lessons: LessonProgressDetail[]
}


export interface LessonAnalyticsItem {
  lesson_id: number
  title: string
  view_count: number
  viewed_students: number
  avg_progress_percent: number
  completion_rate: number
  avg_duration: number
  fast_completion_count: number
}

export interface StudentProgressAnalyticsItem {
  student_id: string
  student_name: string
  completed_lessons: number
  total_lessons: number
  completion_rate: number
  duration_seconds: number
  fast_completion_count: number
}

export interface CourseAnalytics {
  student_count: number
  lesson_count: number
  avg_completion_rate: number
  avg_duration: number
  most_viewed_lessons: LessonAnalyticsItem[]
  low_completion_lessons: LessonAnalyticsItem[]
  student_progress: {
    items: StudentProgressAnalyticsItem[]
    total: number
    page: number
    page_size: number
  }
}

export interface LessonProgressPayload {
  progress_percent: number
  last_position?: number
  duration_seconds?: number
  visit_started?: boolean
}

export function getCourseProgress(courseId: number) {
  return http.get<any, CourseProgress>(`/courses/${courseId}/progress`)
}

export function saveCourseProgress(courseId: number, lessonId: number) {
  return http.post<any, { last_lesson_id: number }>(`/courses/${courseId}/progress`, { lesson_id: lessonId })
}

export function reportLessonProgress(courseId: number, lessonId: number, data: LessonProgressPayload) {
  return http.post<any, LessonProgressDetail>(`/courses/${courseId}/lessons/${lessonId}/progress`, {
    progress_percent: data.progress_percent,
    last_position: data.last_position ?? 0,
    duration_seconds: data.duration_seconds ?? 0,
    visit_started: data.visit_started ?? false,
  })
}

export function reportLessonProgressKeepalive(courseId: number, lessonId: number, data: LessonProgressPayload) {
  const token = localStorage.getItem('auth_token')
  return fetch(`/api/courses/${courseId}/lessons/${lessonId}/progress`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      progress_percent: data.progress_percent,
      last_position: data.last_position ?? 0,
      duration_seconds: data.duration_seconds ?? 0,
      visit_started: data.visit_started ?? false,
    }),
    keepalive: true,
  })
}

export function getCourseAnalytics(courseId: number, page = 1, pageSize = 20) {
  return http.get<any, CourseAnalytics>(`/courses/${courseId}/analytics`, {
    params: { page, page_size: pageSize },
  })
}
