const MESSAGE_REFRESH_EVENT = 'student-message-refresh'

export function emitMessageRefresh() {
  window.dispatchEvent(new Event(MESSAGE_REFRESH_EVENT))
}

export function onMessageRefresh(handler: () => void) {
  const listener = () => handler()
  window.addEventListener(MESSAGE_REFRESH_EVENT, listener)
  return () => window.removeEventListener(MESSAGE_REFRESH_EVENT, listener)
}
