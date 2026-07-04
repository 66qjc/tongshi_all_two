<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminPasswordResetRequests,
  adminApprovePasswordResetRequest,
  adminRejectPasswordResetRequest,
  type PasswordResetRequest,
} from '@/api/admin'

const requests = ref<PasswordResetRequest[]>([])
const loading = ref(false)
const statusFilter = ref('pending')

async function loadRequests() {
  loading.value = true
  try {
    requests.value = await getAdminPasswordResetRequests(statusFilter.value)
  } catch {
    requests.value = []
  } finally {
    loading.value = false
  }
}

function switchFilter(status: string) {
  statusFilter.value = status
  loadRequests()
}

async function handleApprove(requestId: number) {
  try {
    const result = await adminApprovePasswordResetRequest(requestId)
    ElMessageBox.alert(
      `临时密码：<b>${result.temp_password}</b><br/>请告知学生，首次登录后需修改密码。`,
      '密码已重置',
      { dangerouslyUseHTMLString: true, confirmButtonText: '复制并关闭', type: 'success' }
    ).then(() => {
      navigator.clipboard.writeText(result.temp_password)
    })
    await loadRequests()
  } catch {}
}

async function handleReject(requestId: number) {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因（可选）', '驳回申请', {
      inputType: 'textarea',
      confirmButtonText: '确认驳回',
    })
    reason = String(result.value || '').trim()
  } catch { return }
  try {
    await adminRejectPasswordResetRequest(requestId, reason)
    ElMessage.success('已驳回')
    await loadRequests()
  } catch {}
}

function copyTempPassword(pwd: string) {
  navigator.clipboard.writeText(pwd)
  ElMessage.success('已复制临时密码')
}

onMounted(() => loadRequests())
</script>

<template>
  <div class="admin-reset-page">
    <div class="page-header">
      <h2>🔑 密码重置管理</h2>
      <p class="page-desc">处理学生的密码重置申请</p>
    </div>

    <el-radio-group v-model="statusFilter" size="small" @change="(v: string) => switchFilter(v)" style="margin-bottom:16px">
      <el-radio-button value="pending">待处理</el-radio-button>
      <el-radio-button value="approved">已通过</el-radio-button>
      <el-radio-button value="rejected">已驳回</el-radio-button>
    </el-radio-group>

    <el-table :data="requests" v-loading="loading" empty-text="暂无相关记录" stripe border>
      <el-table-column prop="user_name" label="学生" width="110" />
      <el-table-column prop="user_id" label="学号" width="110" />
      <el-table-column prop="message" label="留言" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'pending'" type="warning" size="small">待处理</el-tag>
          <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已通过</el-tag>
          <el-tag v-else type="info" size="small">已驳回</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="临时密码" width="150">
        <template #default="{ row }">
          <template v-if="row.status === 'approved' && row.temp_password">
            <code>{{ row.temp_password }}</code>
            <el-button link type="primary" size="small" @click="copyTempPassword(row.temp_password)">复制</el-button>
          </template>
          <span v-else style="color:#999">-</span>
        </template>
      </el-table-column>
      <el-table-column label="处理人" width="100">
        <template #default="{ row }">
          {{ row.resolved_by_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="申请时间" width="170">
        <template #default="{ row }">
          {{ row.created_at ? new Date(row.created_at).toLocaleString() : '' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="success" size="small" @click="handleApprove(row.id)">重置</el-button>
            <el-button type="danger" size="small" @click="handleReject(row.id)">驳回</el-button>
          </template>
          <span v-else style="color:#999;font-size:0.8rem">
            {{ row.resolved_at ? new Date(row.resolved_at).toLocaleString().split(' ')[0] : '' }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.admin-reset-page {
  max-width: 1100px;
}

.page-header {
  margin-bottom: var(--space-xl);
}

.page-header h2 {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.page-desc {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

code {
  background: var(--color-bg-alt);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.82rem;
}
</style>
