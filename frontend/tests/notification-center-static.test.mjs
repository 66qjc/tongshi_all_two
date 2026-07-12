import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(import.meta.dirname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const notificationApi = read('src/api/notification.ts')
assert.match(notificationApi, /export function getNotifications\(params\?:/, '\u901a\u77e5\u5217\u8868 API \u5e94\u652f\u6301\u5206\u7c7b\u548c\u672a\u8bfb\u7b5b\u9009\u53c2\u6570')
assert.match(notificationApi, /export function markAllNotificationsRead\(/, '\u901a\u77e5 API \u5e94\u63d0\u4f9b\u5168\u90e8\u5df2\u8bfb\u65b9\u6cd5')
assert.match(notificationApi, /\{ updated_count: number \}/, '\u901a\u77e5 API \u5168\u90e8\u5df2\u8bfb\u8fd4\u56de\u7c7b\u578b\u5e94\u4e0e\u540e\u7aef updated_count \u4fdd\u6301\u4e00\u81f4')
assert.match(notificationApi, /export function getNotificationPreferences\(/, '\u901a\u77e5 API \u5e94\u63d0\u4f9b\u504f\u597d\u8bfb\u53d6\u65b9\u6cd5')
assert.match(notificationApi, /export function updateNotificationPreferences\(/, '\u901a\u77e5 API \u5e94\u63d0\u4f9b\u504f\u597d\u66f4\u65b0\u65b9\u6cd5')

const router = read('src/router/index.ts')
assert.match(router, /path:\s*['"]\/student\/notifications['"]/, '\u8def\u7531\u5e94\u63d0\u4f9b /student/notifications \u901a\u77e5\u4e2d\u5fc3\u5165\u53e3')
assert.match(router, /\/student\/notifications/, '\u5b66\u751f\u4e1a\u52a1\u8def\u5f84\u767d\u540d\u5355\u5e94\u5305\u542b\u901a\u77e5\u4e2d\u5fc3')
assert.match(router, /path:\s*['"]\/student\/settings\/notifications['"]/, '\u8def\u7531\u5e94\u63d0\u4f9b\u901a\u77e5\u504f\u597d\u6df1\u94fe\u63a5')

const inbox = read('src/views/InboxView.vue')
assert.match(inbox, /getNotifications/, '\u6d88\u606f\u4e2d\u5fc3\u5e94\u52a0\u8f7d\u901a\u77e5\u5217\u8868')
assert.match(inbox, /markAllNotificationsRead/, '\u6d88\u606f\u4e2d\u5fc3\u5e94\u652f\u6301\u5168\u90e8\u6807\u8bb0\u5df2\u8bfb')
assert.match(inbox, /getNotificationPreferences/, '\u6d88\u606f\u4e2d\u5fc3\u5e94\u8bfb\u53d6\u901a\u77e5\u504f\u597d')
assert.match(inbox, /updateNotificationPreferences/, '\u6d88\u606f\u4e2d\u5fc3\u5e94\u4fdd\u5b58\u901a\u77e5\u504f\u597d')
assert.match(inbox, /route\.path === ['"]\/student\/settings\/notifications['"]/, '\u901a\u77e5\u504f\u597d\u6df1\u94fe\u63a5\u5e94\u81ea\u52a8\u6253\u5f00\u8bbe\u7f6e\u5f39\u7a97')
assert.match(inbox, /\u901a\u77e5\u504f\u597d/u, '\u6d88\u606f\u4e2d\u5fc3\u5e94\u63d0\u4f9b\u4e2d\u6587\u901a\u77e5\u504f\u597d\u5165\u53e3')
assert.match(inbox, /width="min\(420px, calc\(100vw - 32px\)\)"/, '\u901a\u77e5\u504f\u597d\u5f39\u7a97\u5bbd\u5ea6\u5e94\u53d7\u624b\u673a\u89c6\u53e3\u7ea6\u675f')
assert.match(inbox, /class="category-segmented"/, '\u901a\u77e5\u5206\u7c7b\u63a7\u4ef6\u5e94\u63d0\u4f9b\u72ec\u7acb\u7684\u7a84\u5c4f\u9002\u914d\u6837\u5f0f')
assert.match(inbox, /\.category-segmented\s*\{[\s\S]*?overflow-x:\s*auto/, '\u901a\u77e5\u5206\u7c7b\u63a7\u4ef6\u5728\u7a84\u5c4f\u4e0b\u5e94\u53ef\u6c34\u5e73\u6eda\u52a8')
const mojibakePattern = new RegExp('[\uFFFD]|\\?{3,}|\\u040e\\u045e|\\u045e|\\u040e')
assert.doesNotMatch(inbox, mojibakePattern, '\u6d88\u606f\u4e2d\u5fc3\u4e0d\u80fd\u5305\u542b\u4e71\u7801\u6587\u6848')

const appHeader = read('src/components/AppHeader.vue')
assert.match(appHeader, /getNotifications\(/, '\u9876\u90e8\u5bfc\u822a\u5e94\u8bfb\u53d6\u6700\u8fd1\u901a\u77e5')
assert.match(appHeader, /recentNotifications/, '\u9876\u90e8\u5bfc\u822a\u5e94\u7ef4\u62a4\u6700\u8fd1\u901a\u77e5\u5217\u8868')
assert.match(appHeader, /notification-dropdown/, '\u9876\u90e8\u901a\u77e5\u94c3\u94db\u5e94\u63d0\u4f9b\u6700\u8fd1\u901a\u77e5\u4e0b\u62c9')
assert.match(appHeader, /\u6700\u8fd1\u901a\u77e5/u, '\u9876\u90e8\u901a\u77e5\u4e0b\u62c9\u5e94\u4f7f\u7528\u4e2d\u6587\u6807\u9898')
assert.match(appHeader, /\u67e5\u770b\u5168\u90e8/u, '\u9876\u90e8\u901a\u77e5\u4e0b\u62c9\u5e94\u63d0\u4f9b\u67e5\u770b\u5168\u90e8\u5165\u53e3')

console.log('\u901a\u77e5\u4e2d\u5fc3\u9759\u6001\u68c0\u67e5\u901a\u8fc7')
