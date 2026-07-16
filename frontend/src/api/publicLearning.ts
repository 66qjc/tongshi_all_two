import http from './http'
import type { CourseDetail, CourseListResult, Course } from './course'
import type { Material } from './material'

export interface PublicCourse extends Course {}

export type PublicCourseListResult = Omit<CourseListResult, 'courses'> & {
  courses: PublicCourse[]
}

type PublicCourseDetail = CourseDetail

const mojibakePattern =
  /[\u00c0-\u00ff\u8119\u8117\u76f2\u6c13\u732b\u8305\u951a\u5192\u5e3d\u8c8c\u8d38\u4e48\u73ab\u679a\u9709\u7164\u6ca1\u7709]/

export function fixMojibakeText(text: string): string {
  if (!text || !mojibakePattern.test(text)) return text

  try {
    const bytes = Uint8Array.from(Array.from(text, (char) => char.charCodeAt(0) & 0xff))
    const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    return hasMoreChinese(decoded, text) ? decoded : text
  } catch {
    return text
  }
}

function hasMoreChinese(decoded: string, original: string) {
  return countChinese(decoded) > countChinese(original) && !decoded.includes('\uFFFD')
}

function countChinese(text: string) {
  return (text.match(/[\u4e00-\u9fff]/g) || []).length
}

function normalizeTextFields<T>(value: T): T {
  if (typeof value === 'string') return fixMojibakeText(value) as T
  if (Array.isArray(value)) return value.map((item) => normalizeTextFields(item)) as T
  if (!value || typeof value !== 'object') return value

  const result: Record<string, unknown> = {}
  for (const [key, fieldValue] of Object.entries(value as Record<string, unknown>)) {
    result[key] = normalizeTextFields(fieldValue)
  }
  return result as T
}

export function normalizeMaterial(material: Material): Material {
  return normalizeTextFields(material)
}

export function normalizePublicCourse(course: PublicCourse): PublicCourse {
  const normalized = normalizeTextFields(course)
  return {
    ...normalized,
    material_count: Number(normalized.material_count ?? 0),
    question_count: Number(normalized.question_count ?? 0),
    class_count: Number(normalized.class_count ?? 0),
  }
}

function normalizePublicCourseDetail(detail: PublicCourseDetail): PublicCourseDetail {
  const normalized = normalizeTextFields(detail)
  return {
    ...normalized,
    material_count: Number(normalized.material_count ?? 0),
    question_count: Number(normalized.question_count ?? 0),
    class_count: Number(normalized.class_count ?? 0),
    stages: (normalized.stages ?? []).map((stage) => ({
      ...stage,
      materials: (stage.materials ?? []).map(normalizeMaterial),
    })),
    uncategorized_materials: (normalized.uncategorized_materials ?? []).map(normalizeMaterial),
  }
}

export function getPublicCourses(keyword?: string) {
  return http
    .get<any, PublicCourseListResult>('/public/learning/courses', {
      params: keyword ? { keyword } : undefined,
    })
    .then((data) => ({
      ...data,
      hint: data.hint ? fixMojibakeText(data.hint) : data.hint,
      courses: (data.courses ?? []).map(normalizePublicCourse),
    }))
}

export function getPublicCourseDetail(courseId: number, silentError = false) {
  return http
    .get<any, PublicCourseDetail>(`/public/learning/courses/${courseId}`, {
      silentError,
    })
    .then(normalizePublicCourseDetail)
}

export function getPublicMaterials(params?: {
  course_id?: number
  keyword?: string
  limit?: number
}) {
  return http
    .get<any, { items: Material[]; total: number }>('/public/learning/materials', {
      params,
    })
    .then((data) => ({
      ...data,
      items: (data.items ?? []).map(normalizeMaterial),
    }))
}

export function getPublicMaterialFileUrl(materialId: number) {
  return `/api/public/learning/materials/${materialId}/file`
}
