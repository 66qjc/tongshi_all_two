<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDeletedResources,
  purgeDeletedResource,
  restoreDeletedResource,
  type DeletedResourceItem,
} from '@/api/admin'

const router = useRouter()
const resourceOptions = [
  { label: '用户', value: 'users' },
  { label: '课程', value: 'courses' },
  { label: '班级', value: 'classes' },
  { label: '公告', value: 'announcements' },
  { label: '作品', value: 'projects' },
  { label: '资料', value: 'materials' },
  { label: '题目', value: 'questions' },
]

const resourceType = ref('courses')
const loading = ref(false)
const items = ref<DeletedResourceItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

async function loadData() {
  loading.value = true
  try {
    const result = await getDeletedResources(resourceType.value, page.value, pageSize.value)
    items.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('回收站数据加载失败')
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
    let payload: { target_course_id?: number } | undefined
    // 资料课程已物理清理后 course_id 为空，恢复前必须选择目标课程
    if (resourceType.value === 'materials' && (row.needs_target_course || row.course_id == null)) {
      const { value } = await ElMessageBox.prompt(
        '原课程已清理，请输入要恢复到的活跃课程 ID',
        '选择恢复课程',
        {
          confirmButtonText: '恢复',
          cancelButtonText: '取消',
          inputPattern: /^\d+$/,
          inputErrorMessage: '请输入有效的课程 ID',
        },
      )
      payload = { target_course_id: Number(value) }
    }
    await restoreDeletedResource(resourceType.value, row.id, payload)
    ElMessage.success('已恢复该数据')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('恢复失败，请稍后重试')
  }
}

async function handlePurge(row: DeletedResourceItem) {
  try {
    await ElMessageBox.confirm(
      `彻底删除“${row.name || row.id}”后将无法恢复，是否继续？`,
      '彻底删除确认',
      { confirmButtonText: '彻底删除', cancelButtonText: '取消', type: 'warning' },
    )
    await purgeDeletedResource(resourceType.value, row.id)
    ElMessage.success('已彻底删除')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('彻底删除失败')
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
        <p>查看、恢复或彻底删除已软删除的核心业务数据。</p>
      </div>
      <el-select v-model="resourceType" style="width: 180px" @change="handleResourceChange">
        <el-option v-for="item in resourceOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="items" border empty-text="暂无已删除数据">
      <el-table-column prop="id" label="ID" width="100" />
      <el-table-column prop="name" label="名称" min-width="220" show-overflow-tooltip />
      <el-table-column prop="deleted_by" label="删除人" width="140" />
      <el-table-column prop="deleted_at" label="删除时间" width="180" />
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" plain @click="openAuditHistory(row)">操作历史</el-button>
          <el-button size="small" type="primary" plain @click="handleRestore(row)">恢复</el-button>
          <el-button size="small" type="danger" plain @click="handlePurge(row)">彻底删除</el-button>
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
