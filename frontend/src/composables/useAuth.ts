/**
 * 认证 composable
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { useNotification } from '@/composables/useNotification'
import { useSystemStore } from '@/stores'
import type { LoginParams } from '@/types'

export function useAuth() {
  const router = useRouter()
  const loading = ref(false)

  const formValue = reactive<LoginParams>({
    username: '',
    password: '',
  })

  const handleLogin = async () => {
    if (!formValue.username || !formValue.password) {
      throw new Error('请填写完整信息')
    }

    loading.value = true
    try {
      const res = await authApi.login(formValue)
      localStorage.setItem('lens_access_token', res.access_token)
      localStorage.setItem('lens_username', res.username || formValue.username)

      // SPA 内登录不刷新页面，需同步登录状态并立即建立 WS 连接，
      // 否则右上角连接状态会一直显示"断开"直到手动刷新
      const systemStore = useSystemStore()
      systemStore.isLoggedIn = true
      systemStore.connect()

      router.push('/')
      if (res.is_default_password) {
        const { warning } = useNotification()
        warning('当前仍在使用默认密码 admin123，请前往「设置」尽快修改', undefined)
      }
      return { status: 'success' }
    } catch (err: any) {
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    formValue,
    loading,
    handleLogin,
  }
}
