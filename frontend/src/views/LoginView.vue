<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  getForgotPasswordQuestions,
  resetPasswordWithAnswers,
  submitPasswordResetRequest,
} from '@/api/auth'
import type { SecurityQuestionItem } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  id: '',
  password: '',
})
const loading = ref(false)

// 忘记密码弹窗 — 两步流程
const showForgotDialog = ref(false)
const forgotStep = ref(1)           // 1: 输入学号, 2: 自助重置(有密保) / 人工申请(无密保)
const forgotId = ref('')
const forgotLoading = ref(false)
const forgotQuestions = ref<SecurityQuestionItem[]>([])
const forgotAnswers = ref<Record<number, string>>({})
const forgotNewPassword = ref('')
const forgotConfirmPassword = ref('')
const forgotMessage = ref('')

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
    ElMessageBox.alert('账号或密码错误，请重试', '登录失败', {
      confirmButtonText: '确定',
      type: 'error',
    })
  }
}

// ── 忘记密码流程 ──────────────────────────────────────────────────────

function resetForgotState() {
  forgotStep.value = 1
  forgotId.value = ''
  forgotQuestions.value = []
  forgotAnswers.value = {}
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
  forgotMessage.value = ''
}

function openForgotDialog() {
  resetForgotState()
  showForgotDialog.value = true
}

async function handleForgotNext() {
  if (!forgotId.value.trim()) {
    ElMessage.warning('请输入学号或工号')
    return
  }
  forgotLoading.value = true
  try {
    const questions = await getForgotPasswordQuestions(forgotId.value.trim())
    if (questions.length === 0) {
      // 无密保问题，显示人工申请表单
      forgotStep.value = 3
    } else {
      forgotQuestions.value = questions
      forgotStep.value = 2
    }
  } catch {
    // 学号不存在等错误由拦截器显示
  } finally {
    forgotLoading.value = false
  }
}

async function handleForgotReset() {
  const pwdReg = /^(?=.*[A-Za-z])(?=.*\d).{6,}$/
  if (!pwdReg.test(forgotNewPassword.value)) {
    ElMessage.warning('新密码至少 6 位，且必须包含字母和数字')
    return
  }
  if (forgotNewPassword.value !== forgotConfirmPassword.value) {
    ElMessage.warning('两次密码不一致')
    return
  }
  const answers = forgotQuestions.value.map(q => ({
    question_id: q.id,
    answer: forgotAnswers.value[q.id] || '',
  }))
  forgotLoading.value = true
  try {
    await resetPasswordWithAnswers({
      user_id: forgotId.value.trim(),
      answers,
      new_password: forgotNewPassword.value,
    })
    ElMessage.success('密码重置成功，请用新密码登录')
    showForgotDialog.value = false
  } catch (err: any) {
    // 超限时提供转人工入口
    if (err?.message?.includes('超限') || err?.message?.includes('429')) {
      ElMessageBox.confirm('密保验证次数超限，是否转人工重置？', '验证失败', {
        confirmButtonText: '申请人工重置',
        cancelButtonText: '稍后再试',
        type: 'warning',
      }).then(() => {
        forgotStep.value = 3
        forgotMessage.value = ''
      }).catch(() => {})
    }
    // 其他错误由拦截器显示
  } finally {
    forgotLoading.value = false
  }
}

async function handleForgotRequest() {
  if (!forgotMessage.value.trim()) {
    ElMessage.warning('请填写申请说明')
    return
  }
  forgotLoading.value = true
  try {
    await submitPasswordResetRequest({
      user_id: forgotId.value.trim(),
      message: forgotMessage.value.trim(),
    })
    ElMessage.success('申请已提交，请等待教师或管理员审核')
    showForgotDialog.value = false
  } catch {
    // 拦截器已显示错误
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
          <div class="brand-logo brand-logo-mark">
            <img
              src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
              alt="AI 通识课平台标识"
              width="48"
              height="48"
              class="brand-logo-image"
            />
          </div>
          <h1>学 · 思 · 践 · 悟</h1>
          <p>AI 通识课教学平台</p>
          <div class="brand-modules">
            <span class="bm" style="color: white">学 · 探</span>
            <span class="bm" style="color: white">思 · 习</span>
            <span class="bm" style="color: white">践 · 创</span>
            <span class="bm" style="color: white">悟 · 动</span>
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
                      size="large" show-password @keyup.enter.prevent="handleLogin" />
          </div>

          <el-button type="primary" size="large" round native-type="button" :loading="loading"
                     class="btn-submit" @click="handleLogin">
            登录
          </el-button>

          <div class="form-footer">
            <a class="link" style="cursor:pointer" @click="openForgotDialog">忘记密码？</a>
          </div>

          <p class="admin-hint">教师账号请联系系统管理员分配</p>
        </div>
      </div>
    </div>
  </div>

  <!-- 忘记密码弹窗 — 多步骤 -->
  <el-dialog v-model="showForgotDialog" title="找回密码" width="420px" :close-on-click-modal="false" @close="resetForgotState">
    <!-- Step 1: 输入学号 -->
    <div v-if="forgotStep === 1">
      <div class="form-group">
        <label>学号 / 工号</label>
        <el-input v-model="forgotId" placeholder="请输入学号或工号" size="large" @keyup.enter="handleForgotNext" />
      </div>
    </div>

    <!-- Step 2: 回答密保问题 -->
    <div v-else-if="forgotStep === 2">
      <p style="color:#666;margin-bottom:4px;font-size:0.85rem;">请回答以下密保问题以验证身份</p>
      <div v-for="q in forgotQuestions" :key="q.id" class="form-group">
        <label>{{ q.question }}</label>
        <el-input v-model="forgotAnswers[q.id]" placeholder="请输入答案" size="large" />
      </div>
      <div class="form-group">
        <label>新密码</label>
        <el-input v-model="forgotNewPassword" type="password" placeholder="至少 6 位，包含字母和数字" size="large" show-password />
      </div>
      <div class="form-group">
        <label>确认密码</label>
        <el-input v-model="forgotConfirmPassword" type="password" placeholder="再次输入新密码" size="large" show-password @keyup.enter="handleForgotReset" />
      </div>
    </div>

    <!-- Step 3: 人工申请 -->
    <div v-else-if="forgotStep === 3">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
        <template #title>
          该账号未设置密保问题，请提交人工重置申请
        </template>
      </el-alert>
      <div class="form-group">
        <label>申请说明</label>
        <el-input
          v-model="forgotMessage"
          type="textarea"
          :rows="3"
          placeholder="请描述您的情况，如：我是XX班的张三，忘记密码了，学号2025001…"
          maxlength="500"
          show-word-limit
        />
      </div>
    </div>

    <template #footer>
      <template v-if="forgotStep === 1">
        <el-button @click="showForgotDialog = false">取消</el-button>
        <el-button type="primary" :loading="forgotLoading" @click="handleForgotNext">下一步</el-button>
      </template>
      <template v-else-if="forgotStep === 2">
        <el-button @click="resetForgotState">返回</el-button>
        <el-button type="primary" :loading="forgotLoading" @click="handleForgotReset">重置密码</el-button>
      </template>
      <template v-else-if="forgotStep === 3">
        <el-button @click="resetForgotState">返回</el-button>
        <el-button type="primary" :loading="forgotLoading" @click="handleForgotRequest">提交申请</el-button>
      </template>
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
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-xl);
}

.brand-logo-mark {
  align-items: center;
  width: 72px;
  height: 72px;
  margin: 0 auto var(--space-xl);
  background: rgba(255, 253, 248, 0.92);
  border: 1px solid rgba(255, 253, 248, 0.28);
  border-radius: var(--radius-lg);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.22);
}

.brand-logo-image {
  display: block;
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.brand-content h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  margin-bottom: var(--space-sm);
  letter-spacing: 0;
  text-wrap: balance;
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
  letter-spacing: 0.02em;
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
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0;
  text-wrap: balance;
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
