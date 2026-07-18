import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (p) => readFileSync(resolve(root, p), 'utf8')

const api = read('src/api/project.ts')
const router = read('src/router/index.ts')
const detail = read('src/views/ProjectDetailView.vue')

assert.match(api, /export function deleteMyProject/)
assert.match(api, /export function guestLikeProject/)
assert.match(api, /guest-like/)
assert.match(router, /path: '\/create'[\s\S]*public:\s*true/)
assert.match(router, /path: '\/create\/project\/:id'[\s\S]*public:\s*true/)
assert.match(detail, /deleteMyProject/)
assert.match(detail, /确认删除/)
assert.match(detail, /guestLikeProject|guest_liked_/)
