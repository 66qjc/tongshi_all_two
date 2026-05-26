import http from './http'

export interface TeacherItem {
    id: string
    name: string
    major: string
    created_at: string
    needs_password_change: boolean
}

export interface ImportResult {
    created_count: number
    skipped_count: number
    message: string
}

// 获取教师列表
export function getTeachers() {
    return http.get<any, TeacherItem[]>('/admin/teachers')
}

// 手动创建教师
export function createTeacher(data: { id: string; name: string; major?: string }) {
    return http.post<any, any>('/admin/teachers', data)
}

// 删除教师
export function deleteTeacher(teacherId: string) {
    return http.delete<any, any>(`/admin/teachers/${teacherId}`)
}

// 重置教师密码
export function resetTeacherPassword(teacherId: string) {
    return http.post<any, any>(`/admin/teachers/${teacherId}/reset-password`)
}

// Excel 批量导入教师
export function importTeachers(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<any, ImportResult>('/admin/teachers/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
}

// 修改密码（任何登录用户可用）
export function changePassword(data: { old_password: string; new_password: string }) {
    return http.put<any, any>('/change-password', data)
}
