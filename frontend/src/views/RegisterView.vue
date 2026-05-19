<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  id: '',
  name: '',
  password: '',
  confirmPassword: '',
  role: 'student' as 'student' | 'teacher',
  major: '',
})
const loading = ref(false)

const majors = [
  '自动化专业', '机械工程', '测控技术', '电气工程',
  '材料科学', '光学工程', '计算机科学', '电子信息',
]

const isStudent = computed(() => form.role === 'student')

async function handleRegister() {
  if (!form.id.trim() || !form.name.trim() || !form.password.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  if (isStudent.value && !form.major) {
    ElMessage.warning('请选择专业')
    return
  }

  loading.value = true
  const success = await authStore.register(
    form.id.trim(),
    form.name.trim(),
    form.password,
    form.role,
    isStudent.value ? form.major : undefined,
  )
  loading.value = false
  if (success) {
    ElMessage.success('注册成功！')
    if (form.role === 'teacher') {
      router.push('/teacher')
    } else {
      router.push('/')
    }
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-container">
      <!-- Left brand -->
      <div class="brand-side">
        <div class="brand-content">
          <div class="brand-logo">
            <svg viewBox="0 0 32 32" width="48" height="48">
              <defs>
                <linearGradient id="regGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color: var(--color-primary)" />
                  <stop offset="100%" style="stop-color: var(--color-learn)" />
                </linearGradient>
              </defs>
              <circle cx="16" cy="16" r="14" fill="url(#regGrad)" />
              <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700"
                    fill="white" font-family="sans-serif">探</text>
            </svg>
          </div>
          <h1>探 · 练 · 创 · 行</h1>
          <p>AI 通识课教学平台</p>
        </div>
      </div>

      <!-- Right form -->
      <div class="form-side">
        <div class="form-content">
          <h2>注册</h2>
          <p class="form-subtitle">创建你的平台账号</p>

          <div class="form-group">
            <label>身份</label>
            <el-radio-group v-model="form.role" size="large">
              <el-radio-button value="student">学生</el-radio-button>
              <el-radio-button value="teacher">教师</el-radio-button>
            </el-radio-group>
          </div>

          <div class="form-group">
            <label>学号 / 工号</label>
            <el-input v-model="form.id" placeholder="请输入学号或工号" size="large" />
          </div>

          <div class="form-group">
            <label>姓名</label>
            <el-input v-model="form.name" placeholder="请输入姓名" size="large" />
          </div>

          <div v-if="isStudent" class="form-group">
            <label>专业</label>
            <el-select v-model="form.major" placeholder="选择专业" size="large" style="width: 100%">
              <el-option v-for="m in majors" :key="m" :label="m" :value="m" />
            </el-select>
          </div>

          <div class="form-group">
            <label>密码</label>
            <el-input v-model="form.password" type="password" placeholder="至少 6 位"
                      size="large" show-password />
          </div>

          <div class="form-group">
            <label>确认密码</label>
            <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码"
                      size="large" show-password @keyup.enter="handleRegister" />
          </div>

          <el-button type="primary" size="large" round :loading="loading"
                     class="btn-submit" @click="handleRegister">
            注册
          </el-button>

          <div class="form-footer">
            <span>已有账号？</span>
            <router-link to="/login" class="link">去登录</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-alt);
  padding: var(--space-xl);
}

.register-container {
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
}

.form-side {
  flex: 1;
  padding: var(--space-3xl) var(--space-2xl);
  display: flex;
  align-items: center;
  overflow-y: auto;
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
  margin-bottom: var(--space-xl);
}

.form-group {
  margin-bottom: var(--space-md);
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
  margin-top: var(--space-lg);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.link {
  color: var(--color-primary);
  font-weight: 600;
  margin-left: var(--space-xs);
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
