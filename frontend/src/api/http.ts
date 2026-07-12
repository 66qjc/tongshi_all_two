import axios from 'axios'
import { ElMessage } from 'element-plus'

// 扩展 Axios 请求配置：silentError 为 true 时不弹出错误提示，用于公开接口与登录接口之间的无噪声兜底
declare module 'axios' {
  export interface AxiosRequestConfig {
    silentError?: boolean
  }
}

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

function normalizeValidationMessage(message: string) {
  if (message.includes('String should have at least 6 characters')) return '密码至少 6 位'
  if (message.includes('密码必须包含至少一个字母')) return '密码必须包含至少一个字母'
  if (message.includes('密码必须包含至少一个数字')) return '密码必须包含至少一个数字'
  if (message.includes('Field required')) return '请填写完整信息'
  return '提交内容不符合要求，请检查填写内容'
}

function getErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) return '网络错误'
  const data = error.response?.data
  if (data?.message) return data.message
  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    const firstMessage = String(data.detail[0]?.msg || '')
    return normalizeValidationMessage(firstMessage || '提交内容不符合要求')
  }
  if (typeof data?.detail === 'string') return data.detail
  if (error.response?.status === 422) return '提交内容不符合要求，请检查填写内容'
  return error.message || '网络错误'
}

function isLoginRequest(url?: string) {
  return url === '/token' || url?.endsWith('/token')
}

// 请求拦截器：自动带 JWT token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
http.interceptors.response.use(
  (response) => {
    const { code, message } = response.data
    if (code !== 0) {
      // 401 清除登录状态，跳转登录
      if (code === 401) {
        if (isLoginRequest(response.config.url)) {
          return Promise.reject(new Error(message || '账号或密码错误'))
        }
        localStorage.removeItem('auth_user')
        localStorage.removeItem('auth_token')
        window.location.href = '/login'
        return Promise.reject(new Error(message || '登录已过期'))
      }
      if (!response.config.silentError) {
        ElMessage.error(message || '请求失败')
      }
      return Promise.reject(new Error(message))
    }
    return response.data.data
  },
  (error) => {
    if (axios.isCancel(error) || error?.code === 'ERR_CANCELED') {
      return Promise.reject(error)
    }
    // HTTP 401（FastAPI/Starlette 层面返回的，非 BusinessException）
    if (error.response?.status === 401) {
      if (isLoginRequest(error.config?.url)) {
        return Promise.reject(new Error(getErrorMessage(error)))
      }
      localStorage.removeItem('auth_user')
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
      return Promise.reject(new Error('登录已过期'))
    }
    const message = getErrorMessage(error)
    if (!error.config?.silentError) {
      ElMessage.error(message)
    }
    return Promise.reject(new Error(message))
  }
)

export default http
