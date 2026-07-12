/** 将后端相对地址解析为浏览器可访问地址，仅允许安全的 Web 外链协议。 */
export function resolveFileUrl(url: string | undefined | null): string {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('//')) return url
  if (/^[a-z][a-z\d+.-]*:/i.test(url)) return ''

  const base = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (!base) return url

  const normalizedBase = base.replace(/\/+$/, '')
  const normalizedPath = url.startsWith('/') ? url : `/${url}`
  return `${normalizedBase}${normalizedPath}`
}
