<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getDeletedResources,
  restoreDeletedResource,
  type DeletedResourceItem,
} from '@/api/admin'

const router = useRouter()

/** 与后端 soft_delete_policy 一致的中文资源类型与保留策略 */
const resourceOptions = [
  { label: '用户', value: 'users', retentionUnit: 'days' as const, retentionValue: 30 },
  { label: '课程', value: 'courses', retentionUnit: 'days' as const, retentionValue: 30 },
  { label: '班级', value: 'classes', retentionUnit: 'days' as const, retentionValue: 30 },
  { label: '作业', value: 'announcements', retentionUnit: 'days' as const, retentionValue: 30 },
  { label: '作品', value: 'projects', retentionUnit: 'months' as const, retentionValue: 6 },
  { label: '资料', value: 'materials', retentionUnit: 'months' as const, retentionValue: 6 },
  { label: '题目', value: 'questions', retentionUnit: 'months' as const, retentionValue: 6 },
]

const resourceType = ref('courses')
const loading = ref(false)
const items = ref<DeletedResourceItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

function currentResourceLabel() {
  return resourceOptions.find((item) => item.value === resourceType.value)?.label || resourceType.value
}

function pad2(value: number) {
  return String(value).padStart(2, '0')
}

/** 将删除时间解析为可计算的 Date；兼容后端北京时间 ISO */
function parseDeletedAt(value: string | null | undefined): Date | null {
  if (!value) return null
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function daysInMonth(year: number, monthIndex: number) {
  return new Date(year, monthIndex + 1, 0).getDate()
}

/**
 * 按北京日历计算保留截止时间：
 * - 用户/课程/班级/作业：删除后 30 天
 * - 资料/作品/题目：删除后 6 个自然月（日溢出取当月最后一天）
 */
function computeRetentionDeadline(deletedAt: string | null | undefined, type: string): string {
  const base = parseDeletedAt(deletedAt)
  if (!base) return '-'
  const policy = resourceOptions.find((item) => item.value === type)
  if (!policy) return '-'

  const year = base.getFullYear()
  const month = base.getMonth()
  const day = base.getDate()
  const hours = base.getHours()
  const minutes = base.getMinutes()
  const seconds = base.getSeconds()

  let deadline: Date
  if (policy.retentionUnit === 'days') {
    deadline = new Date(base.getTime())
    deadline.setDate(deadline.getDate() + policy.retentionValue)
  } else {
    const totalMonths = year * 12 + month + policy.retentionValue
    const nextYear = Math.floor(totalMonths / 12)
    const nextMonth = totalMonths % 12
    const safeDay = Math.min(day, daysInMonth(nextYear, nextMonth))
    deadline = new Date(nextYear, nextMonth, safeDay, hours, minutes, seconds)
  }

  return `${deadline.getFullYear()}-${pad2(deadline.getMonth() + 1)}-${pad2(deadline.getDate())} ${pad2(deadline.getHours())}:${pad2(deadline.getMinutes())}`
}

async function loadData() {
  loading.value = true
  try {
    const result = await getDeletedResources(resourceType.value, page.value, pageSize.value)
    items.value = result.items
    total.value = result.total
  } catch (error: any) {
    ElMessage.error(error?.message || '回收站数据加载失败')
  } finally {
    loading.value = false
  }
}

function handleResourceChange() {
  page.value = 1
  void loadData()
}

async function handleRestore(row: DeletedResourceItem) {
  try {
    await restoreDeletedResource(resourceType.value, row.id)
    ElMessage.success('已恢复该数据')
    await loadData()
  } catch (error: any) {
    // 业务错误通常已由 http 拦截器弹出后端中文消息；仅在拦截器未覆盖时兜底
    const message = error?.message || '恢复失败，请稍后重试'
    if (!message || message === 'Network Error') {
      ElMessage.error('恢复失败，请稍后重试')
    }
  }
}

function openAuditHistory(row: DeletedResourceItem) {
  void router.push({
    path: '/admin/audit-logs',
    query: { resource_type: resourceType.value, resource_id: String(row.id) },
  })
}

onMounted(loadData)
</script>

<template>
  <section class="admin-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">删除记录</p>
        <h1>数据回收站</h1>
        <p>查看并恢复已软删除的核心业务数据。保留期内仅支持恢复，到期后由系统自动清理。</p>
      </div>
      <el-select v-model="resourceType" style="width: 180px" @change="handleResourceChange">
        <el-option v-for="item in resourceOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="items" border empty-text="暂无已删除数据">
      <el-table-column prop="id" label="ID" width="110" />
      <el-table-column label="资源类型" width="100">
        <template #default>
          {{ currentResourceLabel() }}
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="deleted_by" label="删除人" width="120" />
      <el-table-column prop="deleted_at" label="删除时间" width="170" />
      <el-table-column label="保留截止时间" width="170">
        <template #default="{ row }">
          {{ computeRetentionDeadline(row.deleted_at, resourceType) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" plain @click="openAuditHistory(row)">操作历史</el-button>
          <el-button size="small" type="primary" plain @click="handleRestore(row)">恢复</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-row">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
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
.pager-row { display: flex; justify-content: flex-end; }
</style>
