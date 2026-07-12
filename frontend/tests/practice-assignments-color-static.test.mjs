import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const assignments = readFileSync(resolve(root, 'src/views/PracticeAssignments.vue'), 'utf8')

assertPracticeAssignmentColorSystem()

function assertPracticeAssignmentColorSystem() {
  const requiredTokens = [
    '--assignment-paper',
    '--assignment-panel',
    '--assignment-ink',
    '--assignment-lake',
    '--assignment-pending',
    '--assignment-done',
    '--assignment-expired',
  ]

  for (const token of requiredTokens) {
    if (!assignments.includes(token)) {
      throw new Error(`个人任务页应定义颜色变量 ${token}`)
    }
  }

  if (!/oklch\(/.test(assignments)) {
    throw new Error('个人任务页颜色应使用 OKLCH 色彩定义，避免默认红黄绿标签')
  }

  if (!/\.status-tag\.pending[\s\S]*var\(--assignment-pending\)/.test(assignments)) {
    throw new Error('未完成状态应使用新的暖黄任务色')
  }

  if (!/\.status-tag\.done[\s\S]*var\(--assignment-done\)/.test(assignments)) {
    throw new Error('已完成状态应使用新的墨绿任务色')
  }

  if (!/\.status-tag\.expired[\s\S]*var\(--assignment-expired\)/.test(assignments)) {
    throw new Error('已过期状态应使用新的藕红任务色')
  }

  if (/#10b981|#f59e0b|#ef4444|rgba\(16,\s*185,\s*129|rgba\(245,\s*158,\s*11|rgba\(239,\s*68,\s*68/.test(assignments)) {
    throw new Error('个人任务页不应继续使用默认红黄绿状态色')
  }
}

console.log('practice assignments color static checks passed')
