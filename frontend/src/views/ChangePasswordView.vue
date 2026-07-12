<template>
  <div class="change-password-container">
    <el-card class="change-password-card">
      <template #header>
        <div class="card-header">
          <span>修改登录密码</span>
        </div>
      </template>
      <el-alert
        title="首次登录需要修改密码，修改后方可正常使用系统"
        type="warning"
        :closable="false"
        style="margin-bottom: 24px"
      />
      <el-form :model="form" label-width="100px" style="max-width: 400px">
        <el-form-item label="当前密码">
          <el-input
            v-model="form.old_password"
            type="password"
            show-password
            placeholder="请输入当前密码（初始密码为 123456）"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="form.new_password"
            type="password"
            show-password
            placeholder="至少6位，包含字母和数字"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="form.confirm_password"
            type="password"
            show-password
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            确认修改
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 密保问题设置弹窗（密码修改成功后弹出） -->
    <el-dialog
      v-model="showSecurityDialog"
      title="设置密保问题"
      width="480px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <p style="color:#666;margin-bottom:16px;font-size:0.85rem;">
        为了账号安全，建议设置密保问题，方便后续自助找回密码。您可以稍后在"个人中心"中补设。
      </p>
      <div v-for="(item, index) in securityQuestions" :key="index" class="form-group">
        <label>问题 {{ index + 1 }}</label>
        <div style="display:flex;gap:8px">
          <el-input v-model="item.question" placeholder="自定义问题，如：你最喜欢的动物？" />
          <el-input v-model="item.answer" placeholder="答案" style="width:140px;flex-shrink:0" />
          <el-button v-if="securityQuestions.length > 1" :icon="'Delete'" circle size="small" @click="removeQuestion(index)" />
        </div>
      </div>
      <el-button v-if="securityQuestions.length < 3" type="primary" link @click="addQuestion" style="margin-top:8px">
        + 添加问题（{{ securityQuestions.length }}/3）
      </el-button>
      <template #footer>
        <el-button @click="skipSecurityQuestions">跳过</el-button>
        <el-button type="primary" :loading="securityLoading" @click="saveSecurityQuestions">保存并进入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { updateSecurityQuestions } from '@/api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ old_password: '', new_password: '', confirm_password: '' })
const loading = ref(false)

const showSecurityDialog = ref(false)
const securityLoading = ref(false)
const securityQuestions = ref([{ question: '', answer: '' }])

function addQuestion() {
  if (securityQuestions.value.length < 3) {
    securityQuestions.value.push({ question: '', answer: '' })
  }
}

function removeQuestion(index: number) {
  securityQuestions.value.splice(index, 1)
}

function navigateAfterChange() {
  const role = authStore.user?.role
  if (role === 'admin') router.push('/admin/teachers')
  else if (role === 'teacher') router.push('/teacher')
  else router.push('/')
}

async function saveSecurityQuestions() {
  const valid = securityQuestions.value.filter(q => q.question.trim() && q.answer.trim())
  securityLoading.value = true
  try {
    if (valid.length > 0) {
      await updateSecurityQuestions({ questions: valid.map(q => ({ question: q.question.trim(), answer: q.answer.trim() })) })
    }
    showSecurityDialog.value = false
    navigateAfterChange()
  } catch {
    // 拦截器已显示错误
  } finally {
    securityLoading.value = false
  }
}

function skipSecurityQuestions() {
  showSecurityDialog.value = false
  navigateAfterChange()
}

const handleSubmit = async () => {
  if (!form.value.old_password || !form.value.new_password || !form.value.confirm_password) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (form.value.new_password !== form.value.confirm_password) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (form.value.new_password.length < 6) {
    ElMessage.error('新密码至少6位')
    return
  }
  loading.value = true
  try {
    const changed = await authStore.changePassword(
      form.value.old_password,
      form.value.new_password,
    )
    if (!changed) {
      ElMessage.error('修改失败，请检查旧密码是否正确')
      return
    }
    // 弹出密保问题设置弹窗
    showSecurityDialog.value = true
  } catch (err: any) {
    ElMessage.error(err?.message || '修改失败，请检查旧密码是否正确')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-alt, #f5f5f5);
}

.change-password-card {
  width: 500px;
}

.card-header {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text, #303133);
  text-wrap: balance;
}

.form-group {
  margin-bottom: var(--space-md);
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}
</style>
