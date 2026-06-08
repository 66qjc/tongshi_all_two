import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const inbox = read('src/views/InboxView.vue')
const header = read('src/components/AppHeader.vue')
const popup = read('src/components/AnnouncementPopup.vue')
const eventUtil = read('src/utils/messageRefresh.ts')

assert.match(
  eventUtil,
  /const listener = \(\) => handler\(\)/,
  'Message refresh listeners should call handlers without forwarding DOM Event arguments.',
)

assert.match(
  inbox,
  /loadMessages/,
  'InboxView should centralize message list loading so it can be reused after mount.',
)
assert.match(
  inbox,
  /setInterval\([^,\n]*loadMessages[^,\n]*,\s*15_?000/,
  'InboxView should periodically refresh while the student stays on the inbox page.',
)
assert.match(
  inbox,
  /visibilitychange/,
  'InboxView should refresh when the tab becomes visible again.',
)
assert.match(
  inbox,
  /onMessageRefresh\([^)]*loadMessages/,
  'InboxView should listen for message refresh events from other message UI actions.',
)
assert.match(
  inbox,
  /emitMessageRefresh\(\)/,
  'InboxView should broadcast unread changes after successful read/completion actions.',
)

assert.match(
  header,
  /onMessageRefresh\([^)]*fetchUnreadCount/,
  'AppHeader should refresh the unread badge immediately when message state changes.',
)

assert.match(
  popup,
  /emitMessageRefresh\(\)/,
  'AnnouncementPopup should broadcast refresh after dismissing an unread message.',
)
