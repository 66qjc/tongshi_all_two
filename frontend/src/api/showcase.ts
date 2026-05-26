import http from './http'

export interface ShowcaseItemOut {
    id: number
    section: string
    title: string
    content: string
    cover_url: string
    link_url: string
    sort_order: number
    is_active: boolean
    created_at: string
}

export interface ShowcaseItemCreate {
    section: string
    title: string
    content?: string
    cover_file_id?: number | null
    link_url?: string
    sort_order?: number
}

export interface ShowcaseItemUpdate {
    title?: string
    content?: string
    cover_file_id?: number | null
    link_url?: string
    sort_order?: number
    is_active?: boolean
}

/** 公开接口：获取所有激活内容，按 section 分组 */
export function getShowcase() {
    return http.get<any, Record<string, ShowcaseItemOut[]>>('/showcase')
}

/** 管理员接口：获取所有内容（含未激活） */
export function getShowcaseAdmin() {
    return http.get<any, Record<string, ShowcaseItemOut[]>>('/showcase/admin')
}

/** 管理员新增图文内容 */
export function createShowcaseItem(data: ShowcaseItemCreate) {
    return http.post<any, ShowcaseItemOut>('/showcase', data)
}

/** 管理员修改图文内容 */
export function updateShowcaseItem(id: number, data: ShowcaseItemUpdate) {
    return http.put<any, ShowcaseItemOut>(`/showcase/${id}`, data)
}

/** 管理员删除图文内容 */
export function deleteShowcaseItem(id: number) {
    return http.delete<any, { id: number }>(`/showcase/${id}`)
}
