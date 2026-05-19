<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  id: '',
  password: '',
})
const loading = ref(false)

const rules = {
  id: [{ required: true, message: '请输入学号或工号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!form.id.trim() || !form.password.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  loading.value = true
  const success = await authStore.login(form.id.trim(), form.password)
  loading.value = false
  if (success) {
    ElMessage.success(`欢迎回来，${authStore.user!.name}`)
    if (authStore.user!.role === 'teacher') {
      router.push('/teacher')
    } else {
      router.push('/')
    }
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Left brand -->
      <div class="brand-side">
        <div class="brand-content">
          <div class="brand-logo">
            <svg viewBox="0 0 32 32" width="48" height="48">
              <defs>
                <linearGradient id="loginGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color: var(--color-primary)" />
                  <stop offset="100%" style="stop-color: var(--color-learn)" />
                </linearGradient>
              </defs>
              <circle cx="16" cy="16" r="14" fill="url(#loginGrad)" />
              <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700"
                    fill="white" font-family="sans-serif">探</text>
            </svg>
          </div>
          <h1>探 · 练 · 创 · 行</h1>
          <p>AI 通识课教学平台</p>
          <div class="brand-modules">
            <span class="bm" style="color: var(--color-learn)">探 · 学</span>
            <span class="bm" style="color: var(--color-practice)">练 · 习</span>
            <span class="bm" style="color: var(--color-create)">造 · 创</span>
            <span class="bm" style="color: var(--color-act)">行 · 动</span>
          </div>
        </div>
      </div>

      <!-- Right form -->
      <div class="form-side">
        <div class="form-content">
          <h2>登录</h2>
          <p class="form-subtitle">使用学号或工号登录平台</p>

          <div class="form-group">
            <label>学号 / 工号</label>
            <el-input v-model="form.id" placeholder="请输入学号或工号" size="large" />
          </div>

          <div class="form-group">
            <label>密码</label>
            <el-input v-model="form.password" type="password" placeholder="请输入密码"
                      size="large" show-password @keyup.enter="handleLogin" />
          </div>

          <el-button type="primary" size="large" round :loading="loading"
                     class="btn-submit" @click="handleLogin">
            登录
          </el-button>

          <div class="form-footer">
            <span>没有账号？</span>
            <router-link to="/register" class="link">去注册</router-link>
          </div>

          <div class="demo-hint">
            <p>测试账号：</p>
            <p>学生：2025001 / 123456</p>
            <p>教师：T001 / 123456</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-alt);
  padding: var(--space-xl);
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 900px;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.brand-side {
  flex: 1;
  background: var(--gradient-hero);
  padding: var(--space-4xl) var(--space-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-content {
  text-align: center;
  color: white;
}

.brand-logo {
  margin-bottom: var(--space-xl);
}

.brand-content h1 {
  font-size: 1.8rem;
  font-weight: 800;
  margin-bottom: var(--space-sm);
}

.brand-content p {
  font-size: 0.95rem;
  opacity: 0.7;
  margin-bottom: var(--space-2xl);
}

.brand-modules {
  display: flex;
  gap: var(--space-lg);
  justify-content: center;
}

.bm {
  font-size: 0.85rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.12);
  padding: 0.3rem 0.8rem;
  border-radius: var(--radius-full);
}

.form-side {
  flex: 1;
  padding: var(--space-4xl) var(--space-2xl);
  display: flex;
  align-items: center;
}

.form-content {
  width: 100%;
  max-width: 340px;
  margin: 0 auto;
}

.form-content h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.form-subtitle {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2xl);
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.btn-submit {
  width: 100%;
  margin-top: var(--space-sm);
  font-weight: 600;
}

.form-footer {
  text-align: center;
  margin-top: var(--space-xl);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.link {
  color: var(--color-primary);
  font-weight: 600;
  margin-left: var(--space-xs);
}

.demo-hint {
  margin-top: var(--space-xl);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

@media (max-width: 768px) {
  .brand-side {
    display: none;
  }

  .form-side {
    padding: var(--space-2xl) var(--space-xl);
  }
}
</style>
