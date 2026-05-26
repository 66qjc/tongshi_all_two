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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '../api/admin'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ old_password: '', new_password: '', confirm_password: '' })
const loading = ref(false)

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
    await changePassword({
      old_password: form.value.old_password,
      new_password: form.value.new_password,
    })
    ElMessage.success('密码修改成功，即将跳转...')
    // 更新 store 中的 needs_password_change 状态
    if (authStore.user) {
      authStore.user.needs_password_change = false
      localStorage.setItem('auth_user', JSON.stringify(authStore.user))
    }
    // 根据角色跳转
    setTimeout(() => {
      const role = authStore.user?.role
      if (role === 'admin') router.push('/admin/teachers')
      else if (role === 'teacher') router.push('/teacher')
      else router.push('/')
    }, 1200)
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
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text, #303133);
}
</style>
