import http from './http'
import type { Material, MaterialCreatePayload } from './material'
import type { Question } from './question'

export interface AdminPublicCourse {
  id: number
  name: string
  created_at: string
  created_by: string
  is_public: boolean
  material_count: number
  question_count: number
  sync_copy_count?: number
  synced_material_count?: number
  synced_question_count?: number
  sync_status?: 'not_synced' | 'partial' | 'synced'
}

export interface AdminCourseStage {
  id: number
  course_id: number
  source_stage_id?: number | null
  name: string
  sort_order: number
  created_at?: string
}

export type AdminMaterialPayload = Omit<MaterialCreatePayload, 'course_id'>

export interface AdminQuestionPayload {
  type: 'choice' | 'fill' | 'multi_choice'
  stem: string
  options: string[]
  answer: string
  explanation: string
  tags: string[]
}

export interface AdminQuestionContributionLog {
  id: number
  public_course_id: number
  public_course_name: string
  operator_id: string
  operator_name: string
  operator_role: string
  action: string
  question_count: number
  created_at: string
}

export function getAdminPublicCourses() {
  return http.get<any, AdminPublicCourse[]>('/admin/public-courses')
}

export function createAdminPublicCourse(data: { name: string; description?: string }) {
  return http.post<any, AdminPublicCourse>('/admin/public-courses', data)
}

export function updateAdminPublicCourse(id: number, data: { name: string; description?: string }) {
  return http.put<any, AdminPublicCourse>(`/admin/public-courses/${id}`, data)
}

export function deleteAdminPublicCourse(id: number) {
  return http.delete<any, any>(`/admin/public-courses/${id}`)
}

export function getAdminPublicCourseStages(courseId: number) {
  return http.get<any, AdminCourseStage[]>(`/admin/public-courses/${courseId}/stages`)
}

export function createAdminPublicCourseStage(courseId: number, data: { name: string; sort_order: number }) {
  return http.post<any, AdminCourseStage>(`/admin/public-courses/${courseId}/stages`, data)
}

export function updateAdminPublicCourseStage(courseId: number, stageId: number, data: { name?: string; sort_order?: number }) {
  return http.put<any, AdminCourseStage>(`/admin/public-courses/${courseId}/stages/${stageId}`, data)
}

export function deleteAdminPublicCourseStage(courseId: number, stageId: number) {
  return http.delete<any, any>(`/admin/public-courses/${courseId}/stages/${stageId}`)
}

export function getAdminPublicMaterials(courseId: number) {
  return http.get<any, Material[]>(`/admin/public-courses/${courseId}/materials`)
}

export function createAdminPublicMaterial(courseId: number, data: AdminMaterialPayload) {
  return http.post<any, Material>(`/admin/public-courses/${courseId}/materials`, data)
}

export function updateAdminPublicMaterial(courseId: number, materialId: number, data: AdminMaterialPayload) {
  return http.put<any, Material>(`/admin/public-courses/${courseId}/materials/${materialId}`, data)
}

export function deleteAdminPublicMaterial(courseId: number, materialId: number) {
  return http.delete<any, any>(`/admin/public-courses/${courseId}/materials/${materialId}`)
}

export function getAdminPublicQuestions(courseId: number) {
  return http.get<any, Question[]>(`/admin/public-courses/${courseId}/questions`)
}

export function createAdminPublicQuestion(courseId: number, data: AdminQuestionPayload) {
  return http.post<any, Question>(`/admin/public-courses/${courseId}/questions`, data)
}

export function updateAdminPublicQuestion(courseId: number, questionId: number, data: AdminQuestionPayload) {
  return http.put<any, Question>(`/admin/public-courses/${courseId}/questions/${questionId}`, data)
}

export function deleteAdminPublicQuestion(courseId: number, questionId: number) {
  return http.delete<any, any>(`/admin/public-courses/${courseId}/questions/${questionId}`)
}

export function batchDeleteAdminPublicQuestions(courseId: number, questionIds: number[]) {
  return http.post<any, { deleted_count: number; deleted_ids: number[]; missing_ids: number[] }>(
    `/admin/public-courses/${courseId}/questions/batch-delete`,
    { question_ids: questionIds },
  )
}

export function getAdminPublicQuestionContributions(courseId: number, page = 1, page_size = 20) {
  return http.get<any, { items: AdminQuestionContributionLog[]; total: number; page: number; page_size: number }>(
    `/admin/public-courses/${courseId}/question-contributions`,
    { params: { page, page_size } },
  )
}

export function importAdminPublicQuestions(courseId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<any, { success_count: number; skip_count: number; fail_count: number; skips: { row: number; reason: string }[]; errors: { row: number; reason: string }[] }>(
    `/admin/public-courses/${courseId}/questions/import`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

export async function downloadAdminQuestionTemplate(type: 'all' | 'choice' | 'fill' | 'multi_choice' = 'all') {
  const token = localStorage.getItem('auth_token')
  const response = await fetch(`/api/admin/public-courses/questions/import/template?template_type=${type}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!response.ok) {
    throw new Error('模板下载失败')
  }
  return await response.blob()
}
