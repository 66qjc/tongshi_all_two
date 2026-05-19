<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  email: '',
  subject: '',
  message: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请填写姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请填写邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  subject: [{ required: true, message: '请填写主题', trigger: 'blur' }],
  message: [{ required: true, message: '请填写留言内容', trigger: 'blur' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  ElMessage.success('留言已发送，我们会尽快回复！')
  form.name = ''
  form.email = ''
  form.subject = ''
  form.message = ''
}
</script>

<template>
  <div class="contact-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <h1>联系我们</h1>
          <p>有任何问题或建议，欢迎随时联系我们</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="contact-grid">
          <div class="contact-form-card">
            <h2>发送留言</h2>
            <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
              <el-form-item label="姓名" prop="name">
                <el-input v-model="form.name" placeholder="你的姓名" size="large" />
              </el-form-item>
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="form.email" placeholder="your@email.com" size="large" />
              </el-form-item>
              <el-form-item label="主题" prop="subject">
                <el-input v-model="form.subject" placeholder="留言主题" size="large" />
              </el-form-item>
              <el-form-item label="留言内容" prop="message">
                <el-input v-model="form.message" type="textarea" :rows="5" placeholder="请描述你的问题或建议..." size="large" />
              </el-form-item>
              <el-button type="primary" size="large" round @click="handleSubmit">
                提交留言
              </el-button>
            </el-form>
          </div>

          <div class="contact-info-card">
            <h2>其他联系方式</h2>
            <div class="info-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                      stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div>
                <h4>邮箱</h4>
                <p>ai-course@example.edu.cn</p>
              </div>
            </div>
            <div class="info-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 0115 0z"
                      stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div>
                <h4>地址</h4>
                <p>中国计量大学</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.contact-page {
  padding-top: 64px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-primary-glow);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-inner h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.hero-inner p {
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.content-section {
  padding: var(--space-3xl) 0;
}

.contact-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: var(--space-2xl);
}

.contact-form-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
}

.contact-form-card h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xl);
}

.contact-info-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
}

.contact-info-card h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xl);
}

.info-item {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
  color: var(--color-text-muted);
}

.info-item h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.info-item p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .contact-grid {
    grid-template-columns: 1fr;
  }
}
</style>
