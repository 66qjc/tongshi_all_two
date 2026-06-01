<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getWrongQuestions, getLikedProjects, type WrongQuestion, type LikedProject } from '@/api/profile'
import { resolveFileUrl } from '@/utils/url'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const activeTab = ref('password')

// 修改密码
const pwdForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })
const pwdLoading = ref(false)

async function handleChangePassword() {
  if (!pwdForm.value.oldPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  const pwdReg = /^(?=.*[A-Za-z])(?=.*\d).{6,}$/
  if (!pwdReg.test(pwdForm.value.newPassword)) {
    ElMessage.warning('新密码至少 6 位，且必须包含字母和数字')
    return
  }
  if (pwdForm.value.newPassword !== pwdForm.value.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  pwdLoading.value = true
  const ok = await authStore.changePassword(pwdForm.value.oldPassword, pwdForm.value.newPassword)
  pwdLoading.value = false
  if (ok) {
    ElMessage.success('密码修改成功')
    pwdForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } else {
    ElMessage.error('修改失败，请检查当前密码是否正确')
  }
}

// 错题本
const wrongQuestions = ref<WrongQuestion[]>([])
const wrongLoading = ref(false)
const wrongError = ref('')

async function loadWrongQuestions() {
  wrongLoading.value = true
  wrongError.value = ''
  try {
    wrongQuestions.value = await getWrongQuestions()
  } catch {
    wrongError.value = '加载失败，请稍后重试'
  } finally {
    wrongLoading.value = false
  }
}

// 收藏作品
const likedProjects = ref<LikedProject[]>([])
const likedLoading = ref(false)
const likedError = ref('')

async function loadLikedProjects() {
  likedLoading.value = true
  likedError.value = ''
  try {
    likedProjects.value = await getLikedProjects()
  } catch {
    likedError.value = '加载失败，请稍后重试'
  } finally {
    likedLoading.value = false
  }
}

function handleTabChange(name: string) {
  if (name === 'wrong-questions' && wrongQuestions.value.length === 0 && !wrongLoading.value) {
    loadWrongQuestions()
  }
  if (name === 'liked-projects' && likedProjects.value.length === 0 && !likedLoading.value) {
    loadLikedProjects()
  }
}
</script>

<template>
  <div class="profile-page">
    <div class="page-header">
      <h1>个人中心</h1>
      <p class="subtitle">{{ authStore.user?.name }}，欢迎回来</p>
    </div>

    <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
      <!-- Tab 1：修改密码 -->
      <el-tab-pane label="修改密码" name="password">
        <div class="tab-content">
          <div class="form-section">
            <div class="form-item">
              <label>当前密码</label>
              <el-input
                v-model="pwdForm.oldPassword"
                type="password"
                placeholder="请输入当前密码"
                show-password
                style="max-width: 360px"
              />
            </div>
            <div class="form-item">
              <label>新密码</label>
              <el-input
                v-model="pwdForm.newPassword"
                type="password"
                placeholder="至少 6 位，包含字母和数字"
                show-password
                style="max-width: 360px"
              />
            </div>
            <div class="form-item">
              <label>确认新密码</label>
              <el-input
                v-model="pwdForm.confirmPassword"
                type="password"
                placeholder="再次输入新密码"
                show-password
                style="max-width: 360px"
              />
            </div>
            <div class="form-item">
              <el-button type="primary" :loading="pwdLoading" @click="handleChangePassword">
                保存修改
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2：错题本 -->
      <el-tab-pane label="错题本" name="wrong-questions">
        <div class="tab-content">
          <div v-if="wrongLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <div v-else-if="wrongError" class="error-state">{{ wrongError }}</div>
          <div v-else-if="wrongQuestions.length === 0" class="empty-state">
            <p>暂无错题，继续保持！</p>
          </div>
          <div v-else class="wrong-list">
            <el-collapse>
              <el-collapse-item
                v-for="(q, index) in wrongQuestions"
                :key="q.question_id"
                :name="q.question_id"
              >
                <template #title>
                  <span class="question-title">{{ index + 1 }}. {{ q.stem }}</span>
                </template>
                <div class="question-detail">
                  <div class="options-list">
                    <div
                      v-for="(opt, i) in q.options"
                      :key="i"
                      class="option-item"
                      :class="{
                        'option-correct': String.fromCharCode(65 + i) === q.answer,
                        'option-wrong': String.fromCharCode(65 + i) === q.user_answer && q.user_answer !== q.answer,
                      }"
                    >
                      {{ String.fromCharCode(65 + i) }}. {{ opt }}
                    </div>
                  </div>
                  <div class="answer-row">
                    <span class="label">我的答案：</span>
                    <span class="wrong-answer">{{ q.user_answer }}</span>
                    <span class="label" style="margin-left:16px">正确答案：</span>
                    <span class="correct-answer">{{ q.answer }}</span>
                  </div>
                  <div v-if="q.explanation" class="explanation">
                    <span class="label">解析：</span>{{ q.explanation }}
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3：收藏作品 -->
      <el-tab-pane label="收藏作品" name="liked-projects">
        <div class="tab-content">
          <div v-if="likedLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <div v-else-if="likedError" class="error-state">{{ likedError }}</div>
          <div v-else-if="likedProjects.length === 0" class="empty-state">
            <p>暂无收藏作品</p>
            <p class="hint">去作品展区发现感兴趣的作品吧</p>
          </div>
          <div v-else class="project-grid">
            <div
              v-for="project in likedProjects"
              :key="project.id"
              class="project-card"
              @click="router.push(`/create/project/${project.id}`)"
            >
              <div class="card-cover">
                <img
                  v-if="project.image_url || (project.images && project.images.length)"
                  :src="resolveFileUrl(project.image_url || project.images[0]?.image_url)"
                  :alt="project.title"
                />
                <div v-else class="cover-placeholder">暂无封面</div>
              </div>
              <div class="card-info">
                <div class="card-title">{{ project.title }}</div>
                <div class="card-meta">
                  <span>{{ project.author_name }}</span>
                  <span class="likes">♥ {{ project.likes }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 1.6rem;
  font-weight: 600;
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
  color: var(--color-text-primary, #1a1a1a);
  margin: 0 0 4px;
}

.subtitle {
  color: var(--color-text-muted, #888);
  font-size: 0.9rem;
  margin: 0;
}

.tab-content {
  padding: 24px 8px;
  min-height: 300px;
}

/* 修改密码表单 */
.form-section {
  max-width: 480px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 20px;
}

.form-item label {
  font-size: 0.9rem;
  color: var(--color-text-secondary, #555);
  font-weight: 500;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 48px 0;
  color: var(--color-text-muted, #aaa);
}

.empty-state p {
  margin: 4px 0;
}

.empty-state .hint {
  font-size: 0.85rem;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 48px 0;
  color: var(--color-text-muted, #aaa);
}

/* 错题本 */
.wrong-list {
  width: 100%;
}

.question-title {
  font-size: 0.95rem;
  line-height: 1.5;
}

.question-detail {
  padding: 12px 16px;
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
}

.options-list {
  margin-bottom: 12px;
}

.option-item {
  padding: 4px 8px;
  margin: 2px 0;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.option-correct {
  background: #f0fdf4;
  color: #16a34a;
  font-weight: 500;
}

.option-wrong {
  background: #fef2f2;
  color: #dc2626;
}

.answer-row {
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.label {
  color: var(--color-text-secondary);
}

.wrong-answer {
  color: #dc2626;
  font-weight: 600;
}

.correct-answer {
  color: #16a34a;
  font-weight: 600;
}

.explanation {
  font-size: 0.88rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  border-top: 1px solid var(--color-border);
  padding-top: 8px;
  margin-top: 8px;
}

/* 收藏作品网格 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

@media (max-width: 768px) {
  .project-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .project-grid {
    grid-template-columns: 1fr;
  }
}

.project-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}

.project-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-cover {
  width: 100%;
  height: 160px;
  overflow: hidden;
  background: var(--color-bg-alt);
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.card-info {
  padding: 10px 12px;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.likes {
  color: #e05d5d;
}
</style>
