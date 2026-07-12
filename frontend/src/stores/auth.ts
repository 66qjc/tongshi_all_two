import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, changePassword as apiChangePassword } from '@/api/auth'

export interface User {
  id: string
  name: string
  role: 'student' | 'teacher' | 'admin'
  major?: string
  needs_password_change?: boolean
}

const validRoles: User['role'][] = ['student', 'teacher', 'admin']

type StoredUserRecord = {
  id?: unknown
  name?: unknown
  role?: User['role']
  major?: unknown
  needs_password_change?: unknown
}

function clearStoredAuth() {
  localStorage.removeItem('auth_user')
  localStorage.removeItem('auth_token')
}

function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return true
    const payload = JSON.parse(atob(parts[1]!))
    if (!payload.exp) return false
    // exp 是秒级时间戳，提前 10 秒判定过期避免临界请求失败
    return payload.exp * 1000 < Date.now() + 10_000
  } catch {
    return true
  }
}

function parseStoredUser(storedUser: string | null): User | null {
  if (!storedUser) return null

  try {
    const parsed = JSON.parse(storedUser) as StoredUserRecord | null
    if (!parsed || typeof parsed !== 'object') return null
    if (typeof parsed.id !== 'string' || typeof parsed.name !== 'string') return null
    if (parsed.role === undefined || !validRoles.includes(parsed.role)) return null

    return {
      id: parsed.id,
      name: parsed.name,
      role: parsed.role,
      major: typeof parsed.major === 'string' ? parsed.major : undefined,
      needs_password_change: parsed.needs_password_change === true,
    }
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const storedUser = localStorage.getItem('auth_user')
  const storedToken = localStorage.getItem('auth_token')
  let initialUser: User | null = null
  let initialToken: string | null = storedToken

  // 启动时检查 token 是否过期，过期则清除
  if (storedToken && isTokenExpired(storedToken)) {
    clearStoredAuth()
    initialToken = null
  } else if (storedToken) {
    initialUser = parseStoredUser(storedUser)
    if (!initialUser) {
      clearStoredAuth()
      initialToken = null
    }
  } else if (storedUser) {
    clearStoredAuth()
  }

  const user = ref<User | null>(initialUser)
  const token = ref<string | null>(initialToken)

  const isLoggedIn = computed(() => !!user.value)

  function replaceAccessToken(accessToken: string) {
    token.value = accessToken
    localStorage.setItem('auth_token', accessToken)
  }

  async function login(id: string, password: string): Promise<boolean> {
    try {
      const result = await apiLogin({ id, password })
      const u: User = {
        id: result.user.id,
        name: result.user.name,
        role: result.user.role as 'student' | 'teacher' | 'admin',
        major: result.user.major,
        needs_password_change: result.user.needs_password_change,
      }
      user.value = u
      localStorage.setItem('auth_user', JSON.stringify(u))
      replaceAccessToken(result.access_token)
      return true
    } catch {
      return false
    }
  }

  async function register(id: string, name: string, password: string, role: 'student' | 'teacher', major?: string): Promise<boolean> {
    try {
      await apiRegister({ id, name, password, role, major })
      // 注册成功后自动登录
      return await login(id, password)
    } catch {
      return false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    clearStoredAuth()
  }

  async function changePassword(oldPassword: string, newPassword: string): Promise<boolean> {
    try {
      const result = await apiChangePassword({ old_password: oldPassword, new_password: newPassword })
      replaceAccessToken(result.access_token)
      // 修改密码成功后，清除强制改密标记
      if (user.value) {
        user.value.needs_password_change = false
        localStorage.setItem('auth_user', JSON.stringify(user.value))
      }
      return true
    } catch {
      return false
    }
  }

  return { user, token, isLoggedIn, login, register, logout, replaceAccessToken, changePassword }
})
