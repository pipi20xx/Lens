/**
 * 剪贴板复制 composable
 *
 * navigator.clipboard 在非安全上下文（HTTP 非 localhost）下不可用，
 * 因此提供 execCommand('copy') 作为 fallback。
 */
import { useNotification } from './useNotification'

export function useClipboard() {
  const { success, error: showError } = useNotification()

  async function copy(text: string, hint = '已复制到剪贴板'): Promise<boolean> {
    if (!text) {
      showError('没有可复制的内容')
      return false
    }

    // 优先使用 Clipboard API（安全上下文）
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text)
        success(hint)
        return true
      } catch {
        // 权限被拒绝，降级到 execCommand
      }
    }

    // Fallback: 临时 textarea + execCommand('copy')
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '0'
      textarea.setAttribute('readonly', '')
      document.body.appendChild(textarea)

      const selected = document.getSelection()?.rangeCount
        ? document.getSelection()!.getRangeAt(0)
        : null

      textarea.select()
      textarea.setSelectionRange(0, textarea.value.length)

      const ok = document.execCommand('copy')
      document.body.removeChild(textarea)

      if (selected && document.getSelection()) {
        document.getSelection()!.removeAllRanges()
        document.getSelection()!.addRange(selected)
      }

      if (ok) {
        success(hint)
        return true
      }
      showError('复制失败，请手动选取')
      return false
    } catch {
      showError('复制失败，请手动选取')
      return false
    }
  }

  return { copy }
}
