/**
 * 认证 composable
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
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
      router.push('/')
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
