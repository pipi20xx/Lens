/**
 * 确认对话框 composable（单例模式）
 */
import { ref } from 'vue'

interface ConfirmOptions {
  title: string
  content: string
  confirmText?: string
  cancelText?: string
  confirmColor?: string
}

const show = ref(false)
const options = ref<ConfirmOptions>({
  title: '',
  content: '',
  confirmText: '确认',
  cancelText: '取消',
  confirmColor: 'primary',
})

let resolvePromise: ((value: boolean) => void) | null = null

export function useConfirm() {
  function confirm(opts: ConfirmOptions): Promise<boolean> {
    options.value = {
      confirmText: '确认',
      cancelText: '取消',
      confirmColor: 'primary',
      ...opts,
    }
    show.value = true
    return new Promise((resolve) => {
      resolvePromise = resolve
    })
  }

  function onConfirm() {
    show.value = false
    resolvePromise?.(true)
    resolvePromise = null
  }

  function onCancel() {
    show.value = false
    resolvePromise?.(false)
    resolvePromise = null
  }

  return { show, options, confirm, onConfirm, onCancel }
}
