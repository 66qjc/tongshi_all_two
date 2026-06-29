/**
 * 将后端返回的文件 URL（如 /uploads/xxx）解析为浏览器可访问的完整地址。
 *
 * 开发环境：Vite 代理 /uploads 到后端，相对路径即可工作，无需处理。
 * 生产环境：通过 VITE_API_BASE 环境变量指定后端地址，拼接为绝对 URL。
 *
 * /api/ 文件路径需要认证，自动追加 ?token=xxx，兼容 <a> / <iframe> / <img> 等
 * 无法携带 Authorization 请求头的 HTML 元素。
 */
export function resolveFileUrl(url: string | undefined | null): string {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  const base = import.meta.env.VITE_API_BASE as string | undefined
  const fullUrl = base ? `${base.replace(/\/$/, '')}${url}` : url
  if (url.startsWith('/api/files/') || url.startsWith('/api/materials/')) {
    const token = localStorage.getItem('auth_token')
    if (token) {
      const separator = fullUrl.includes('?') ? '&' : '?'
      return `${fullUrl}${separator}token=${encodeURIComponent(token)}`
    }
  }
  return fullUrl
}
