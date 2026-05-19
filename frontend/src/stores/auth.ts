import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister } from '@/api/auth'

export interface User {
  id: string
  name: string
  role: 'student' | 'teacher'
  major?: string
}

export const useAuthStore = defineStore('auth', () => {
  const storedUser = localStorage.getItem('auth_user')
  const user = ref<User | null>(storedUser ? JSON.parse(storedUser) : null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))

  const isLoggedIn = computed(() => !!user.value)

  async function login(id: string, password: string): Promise<boolean> {
    try {
      const result = await apiLogin({ id, password })
      const u: User = {
        id: result.user.id,
        name: result.user.name,
        role: result.user.role as 'student' | 'teacher',
        major: result.user.major,
      }
      user.value = u
      token.value = result.access_token
      localStorage.setItem('auth_user', JSON.stringify(u))
      localStorage.setItem('auth_token', result.access_token)
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
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_token')
  }

  return { user, token, isLoggedIn, login, register, logout }
})
