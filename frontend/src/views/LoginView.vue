<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { forgotPassword as apiForgotPassword } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  id: '',
  password: '',
})
const loading = ref(false)

// 忘记密码弹窗
const showForgotDialog = ref(false)
const forgotForm = reactive({ id: '', newPassword: '', confirmPassword: '' })
const forgotLoading = ref(false)

// 首次登录强制改密弹窗
const showChangePasswordDialog = ref(false)
const changeForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const changeLoading = ref(false)

const rules = {
  id: [{ required: true, message: '请输入学号或工号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function navigateByRole() {
  const role = authStore.user?.role
  if (role === 'admin') {
    await router.replace('/admin/teachers')
  } else if (role === 'teacher') {
    await router.replace('/teacher')
  } else {
    await router.replace('/')
  }
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
    if (authStore.user?.needs_password_change) {
      // 弹出强制改密弹窗，不跳转
      showChangePasswordDialog.value = true
    } else {
      ElMessage.success(`欢迎回来，${authStore.user!.name}`)
      await navigateByRole()
    }
  } else {
    ElMessageBox.alert('密码错误，请重试', '登录失败', {
      confirmButtonText: '确定',
      type: 'error',
    })
  }
}

async function handleForgotPassword() {
  if (!forgotForm.id.trim()) {
    ElMessage.warning('请输入学号或工号')
    return
  }
  if (!forgotForm.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  const pwdReg = /^(?=.*[A-Za-z])(?=.*\d).{6,}$/
  if (!pwdReg.test(forgotForm.newPassword)) {
    ElMessage.warning('密码至少 6 位，且必须包含字母和数字')
    return
  }
  if (forgotForm.newPassword !== forgotForm.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  forgotLoading.value = true
  try {
    await apiForgotPassword({ id: forgotForm.id.trim(), new_password: forgotForm.newPassword })
    ElMessage.success('密码重置成功，请用新密码登录')
    showForgotDialog.value = false
    forgotForm.id = ''
    forgotForm.newPassword = ''
    forgotForm.confirmPassword = ''
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '重置失败，请检查学号是否正确')
  } finally {
    forgotLoading.value = false
  }
}

async function handleFirstLoginChange() {
  if (!changeForm.oldPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  const pwdReg = /^(?=.*[A-Za-z])(?=.*\d).{6,}$/
  if (!pwdReg.test(changeForm.newPassword)) {
    ElMessage.warning('新密码至少 6 位，且必须包含字母和数字')
    return
  }
  if (changeForm.newPassword !== changeForm.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  changeLoading.value = true
  const ok = await authStore.changePassword(changeForm.oldPassword, changeForm.newPassword)
  changeLoading.value = false
  if (ok) {
    ElMessage.success('密码修改成功')
    showChangePasswordDialog.value = false
    await navigateByRole()
  } else {
    ElMessage.error('修改失败，请检查当前密码是否正确')
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
            <a class="link" style="cursor:pointer" @click="showForgotDialog = true">忘记密码？</a>
          </div>

          <p class="admin-hint">教师账号请联系系统管理员分配</p>
        </div>
      </div>
    </div>
  </div>

  <!-- 忘记密码弹窗 -->
  <el-dialog v-model="showForgotDialog" title="重置密码" width="400px" :close-on-click-modal="false">
    <div class="form-group">
      <label>学号 / 工号</label>
      <el-input v-model="forgotForm.id" placeholder="请输入学号或工号" size="large" />
    </div>
    <div class="form-group">
      <label>新密码</label>
      <el-input v-model="forgotForm.newPassword" type="password" placeholder="至少 6 位，包含字母和数字" size="large" show-password />
    </div>
    <div class="form-group">
      <label>确认密码</label>
      <el-input v-model="forgotForm.confirmPassword" type="password" placeholder="再次输入新密码" size="large" show-password />
    </div>
    <template #footer>
      <el-button @click="showForgotDialog = false">取消</el-button>
      <el-button type="primary" :loading="forgotLoading" @click="handleForgotPassword">重置密码</el-button>
    </template>
  </el-dialog>

  <!-- 首次登录强制改密弹窗 -->
  <el-dialog
    v-model="showChangePasswordDialog"
    title="首次登录，请修改密码"
    width="400px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <p style="color:#666;margin-bottom:16px;font-size:0.9rem;">为了账号安全，请修改初始密码后再使用。</p>
    <div class="form-group">
      <label>当前密码</label>
      <el-input v-model="changeForm.oldPassword" type="password" size="large" show-password />
    </div>
    <div class="form-group">
      <label>新密码</label>
      <el-input v-model="changeForm.newPassword" type="password" placeholder="至少 6 位，包含字母和数字" size="large" show-password />
    </div>
    <div class="form-group">
      <label>确认密码</label>
      <el-input v-model="changeForm.confirmPassword" type="password" placeholder="再次输入新密码" size="large" show-password />
    </div>
    <template #footer>
      <el-button type="primary" :loading="changeLoading" @click="handleFirstLoginChange">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: var(--space-xl);
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 880px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.brand-side {
  flex: 1;
  background: var(--gradient-hero);
  padding: var(--space-4xl) var(--space-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.brand-content {
  text-align: center;
  color: white;
}

.brand-logo {
  margin-bottom: var(--space-xl);
}

.brand-content h1 {
  font-family: var(--font-serif);
  font-size: 1.7rem;
  font-weight: 900;
  margin-bottom: var(--space-sm);
  letter-spacing: 0.1em;
}

.brand-content p {
  font-size: 0.88rem;
  opacity: 0.65;
  margin-bottom: var(--space-2xl);
}

.brand-modules {
  display: flex;
  gap: var(--space-md);
  justify-content: center;
}

.bm {
  font-size: 0.78rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.25rem 0.7rem;
  border-radius: var(--radius-sm);
  letter-spacing: 0.05em;
}

.form-side {
  flex: 1;
  padding: var(--space-4xl) var(--space-2xl);
  display: flex;
  align-items: center;
}

.form-content {
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
}

.form-content h2 {
  font-family: var(--font-serif);
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.05em;
}

.form-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2xl);
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0.03em;
}

.btn-submit {
  width: 100%;
  margin-top: var(--space-sm);
  font-weight: 600;
}

.admin-hint {
  text-align: center;
  margin-top: var(--space-lg);
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.form-footer {
  text-align: right;
  margin-top: var(--space-sm);
  margin-bottom: var(--space-xs);
  font-size: 0.78rem;
}

.link {
  color: var(--color-primary);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
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
