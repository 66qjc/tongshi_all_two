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

// 创建教师账号
export function createTeacher(data: { id: string; name: string; major?: string }) {
    return http.post<any, any>('/admin/teachers', data)
}

// 查询教师关联数据
export function getTeacherDependencies(teacherId: string) {
    return http.get<any, {
        course_count: number
        class_count: number
        announcement_count: number
        project_count: number
        showcase_count: number
    }>(`/admin/teachers/${teacherId}/dependencies`)
}

// 删除教师（force=true 时级联删除关联数据）
export function deleteTeacher(teacherId: string, force = false) {
    return http.delete<any, any>(`/admin/teachers/${teacherId}`, { params: { force } })
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

export async function downloadTeacherImportTemplate() {
    const token = localStorage.getItem('auth_token')
    const response = await fetch('/api/admin/teachers/import/template', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    if (!response.ok) {
        throw new Error('下载模板失败')
    }
    return await response.blob()
}

// 修改密码（登录用户通用）
export function changePassword(data: { old_password: string; new_password: string }) {
    return http.put<any, { message: string; access_token: string }>('/change-password', data)
}

// —— 密码重置申请 ——

export interface PasswordResetRequest {
    id: number
    user_id: string
    user_name: string
    message: string
    status: string
    resolved_by: string | null
    resolved_by_name: string
    temp_password: string
    resolved_at: string
    created_at: string
}

export function getAdminPasswordResetRequests(status?: string) {
    const params = status ? `?status=${encodeURIComponent(status)}` : ''
    return http.get<any, PasswordResetRequest[]>(`/admin/password-reset-requests${params}`)
}

export function adminApprovePasswordResetRequest(requestId: number) {
    return http.post<any, { message: string; temp_password: string }>(`/admin/password-reset-requests/${requestId}/approve`)
}

export function adminRejectPasswordResetRequest(requestId: number, reason?: string) {
    return http.post<any, { message: string }>(`/admin/password-reset-requests/${requestId}/reject`, { reason: reason || '' })
}


// —— 回收站与审计日志 ——
export interface DeletedResourceItem {
    id: number | string
    name: string
    deleted_at: string
    deleted_by: string | null
}

export interface DeletedResourcePage {
    items: DeletedResourceItem[]
    total: number
    page: number
    page_size: number
}

export interface AuditLogItem {
    id: number
    user_id: string | null
    user_role: string | null
    action: string
    resource_type: string | null
    resource_id: string | null
    resource_name: string | null
    details: Record<string, unknown>
    ip_address: string | null
    user_agent: string | null
    status: string
    error_message: string | null
    created_at: string
}

export interface AuditLogPage {
    items: AuditLogItem[]
    total: number
    page: number
    page_size: number
}

export function getDeletedResources(resourceType: string, page = 1, pageSize = 20) {
    return http.get<any, DeletedResourcePage>(`/admin/deleted/${resourceType}`, { params: { page, page_size: pageSize } })
}

export function restoreDeletedResource(resourceType: string, id: number | string) {
    return http.post<any, DeletedResourceItem>(`/admin/restore/${resourceType}/${id}`)
}

export function purgeDeletedResource(resourceType: string, id: number | string) {
    return http.delete<any, { id: number | string }>(`/admin/purge/${resourceType}/${id}`)
}

export interface AuditLogQueryParams {
    user_id?: string
    action?: string
    resource_type?: string
    resource_id?: string
    status?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
}

export function getAuditLogs(params: AuditLogQueryParams) {
    return http.get<any, AuditLogPage>('/admin/audit-logs', { params })
}

export async function downloadAuditLogs(params?: AuditLogQueryParams) {
    const token = localStorage.getItem('auth_token')
    const query = new URLSearchParams()
    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') query.append(key, String(value))
    })
    const suffix = query.toString() ? `?${query.toString()}` : ''
    const response = await fetch(`/api/admin/audit-logs/export${suffix}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    if (!response.ok) throw new Error('审计日志导出失败')
    return await response.blob()
}
