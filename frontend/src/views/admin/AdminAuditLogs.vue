<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { downloadAuditLogs, getAuditLogs, type AuditLogItem } from '@/api/admin'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const exporting = ref(false)
const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const filters = reactive({
  user_id: '',
  action: '',
  resource_type: '',
  resource_id: '',
  status: '',
  date_range: [] as string[],
  page: 1,
  page_size: 20,
})

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
]

function buildQuery() {
  return {
    user_id: filters.user_id || undefined,
    action: filters.action || undefined,
    resource_type: filters.resource_type || undefined,
    resource_id: filters.resource_id || undefined,
    status: filters.status || undefined,
    start_date: filters.date_range[0] || undefined,
    end_date: filters.date_range[1] || undefined,
    page: filters.page,
    page_size: filters.page_size,
  }
}

async function loadData() {
  loading.value = true
  try {
    const result = await getAuditLogs(buildQuery())
    logs.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('审计日志加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  filters.page = 1
  void syncQueryToUrl()
  void loadData()
}

function handleReset() {
  filters.user_id = ''
  filters.action = ''
  filters.resource_type = ''
  filters.resource_id = ''
  filters.status = ''
  filters.date_range = []
  filters.page = 1
  void router.replace({ query: {} })
  void loadData()
}

function syncQueryToUrl() {
  return router.replace({
    query: {
      user_id: filters.user_id || undefined,
      action: filters.action || undefined,
      resource_type: filters.resource_type || undefined,
      resource_id: filters.resource_id || undefined,
      status: filters.status || undefined,
    },
  })
}

function hydrateFiltersFromRoute() {
  filters.user_id = String(route.query.user_id || '')
  filters.action = String(route.query.action || '')
  filters.resource_type = String(route.query.resource_type || '')
  filters.resource_id = String(route.query.resource_id || '')
  filters.status = String(route.query.status || '')
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await downloadAuditLogs(buildQuery())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '审计日志.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('审计日志导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  hydrateFiltersFromRoute()
  void loadData()
})
</script>

<template>
  <section class="admin-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">操作记录</p>
        <h1>审计日志</h1>
        <p>追踪删除、恢复、导出等关键后台操作，也可按资源类型和资源 ID 查看单个资源操作历史。</p>
      </div>
      <el-button type="primary" :loading="exporting" @click="handleExport">导出 Excel</el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="操作人">
          <el-input v-model="filters.user_id" placeholder="学号/工号" clearable />
        </el-form-item>
        <el-form-item label="动作">
          <el-input v-model="filters.action" placeholder="如 course.delete" clearable />
        </el-form-item>
        <el-form-item label="资源类型">
          <el-input v-model="filters.resource_type" placeholder="如 courses" clearable />
        </el-form-item>
        <el-form-item label="资源ID">
          <el-input v-model="filters.resource_id" placeholder="支持数字ID或学号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.date_range"
            type="datetimerange"
            value-format="YYYY-MM-DDTHH:mm:ss"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table v-loading="loading" :data="logs" border empty-text="暂无审计日志">
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column prop="user_id" label="操作人" width="130" />
      <el-table-column prop="action" label="动作" width="170" />
      <el-table-column prop="resource_type" label="资源类型" width="130" />
      <el-table-column prop="resource_id" label="资源ID" width="130" />
      <el-table-column prop="resource_name" label="资源名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="error_message" label="错误信息" min-width="160" show-overflow-tooltip />
    </el-table>

    <div class="pager-row">
      <el-pagination
        v-model:current-page="filters.page"
        :page-size="filters.page_size"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="loadData"
      />
    </div>
  </section>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 18px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.page-header h1 { margin: 0; font-size: 1.5rem; color: var(--color-text); }
.page-header p { margin: 6px 0 0; color: var(--color-text-secondary); }
.eyebrow { margin: 0 0 4px !important; font-size: 0.78rem; font-weight: 800; color: var(--color-primary); text-transform: uppercase; }
.filter-card { border-color: var(--color-border); }
.pager-row { display: flex; justify-content: flex-end; }
</style>
