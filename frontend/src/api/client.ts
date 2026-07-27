/**
 * Lens API 客户端
 * 基于 Fetch 封装，替代 Axios
 */

interface ApiOptions extends RequestInit {
  baseUrl?: string
  params?: Record<string, string | number | boolean | undefined | null | (string | number | boolean)[]>
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function apiFetch<T>(
  endpoint: string,
  options?: ApiOptions
): Promise<T> {
  const { baseUrl = API_BASE_URL, params, headers, body, method = 'GET', ...rest } = options || {}

  let url = `${baseUrl}${endpoint}`

  if (params) {
    const queryString = new URLSearchParams()
    for (const key in params) {
      const value = params[key]
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach((v) => queryString.append(key, String(v)))
        } else {
          queryString.append(key, String(value))
        }
      }
    }
    if (queryString.toString()) {
      url += (url.includes('?') ? '&' : '?') + queryString.toString()
    }
  }

  // blob 下载模式跳过 JSON 解析
  const isBlobRequest = (options as any)?.responseType === 'blob' || (rest as any)?.responseType === 'blob'

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  // 自动添加 Authorization 头
  const token = localStorage.getItem('lens_access_token')
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`
  }

  // FormData 时让浏览器设置 Content-Type
  if (body instanceof FormData) {
    delete defaultHeaders['Content-Type']
  }

  const config: RequestInit = {
    method,
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    ...rest,
  }

  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    if (body instanceof FormData) {
      config.body = body
    } else {
      config.body = JSON.stringify(body)
    }
  }

  try {
    const response = await fetch(url, config)

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('lens_access_token')
        localStorage.removeItem('lens_username')
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
      }

      let errorData: any = { message: `HTTP error! status: ${response.status}` }
      try {
        errorData = await response.json()
      } catch (e) {
        // 非 JSON 格式
      }
      throw new Error(errorData.detail || errorData.message || `API Error: ${response.status}`)
    }

    // blob 下载模式：直接返回 Blob
    if (isBlobRequest) {
      return (await response.blob()) as unknown as T
    }

    const text = await response.text()
    return text ? JSON.parse(text) : {} as T

  } catch (error) {
    console.error('API Fetch Error:', error)
    throw error
  }
}

// 封装常用 HTTP 方法
export const api = {
  get: <T>(endpoint: string, options?: ApiOptions) => apiFetch<T>(endpoint, { ...options, method: 'GET' }),
  post: <T>(endpoint: string, body?: any, options?: ApiOptions) => apiFetch<T>(endpoint, { ...options, method: 'POST', body }),
  put: <T>(endpoint: string, body?: any, options?: ApiOptions) => apiFetch<T>(endpoint, { ...options, method: 'PUT', body }),
  patch: <T>(endpoint: string, body?: any, options?: ApiOptions) => apiFetch<T>(endpoint, { ...options, method: 'PATCH', body }),
  delete: <T>(endpoint: string, bodyOrOptions?: any | ApiOptions, options?: ApiOptions) => {
    // 支持 api.delete(url, body, options) 和 api.delete(url, options) 两种调用方式
    if (bodyOrOptions && typeof bodyOrOptions === 'object' && ('method' in bodyOrOptions || 'params' in bodyOrOptions || 'headers' in bodyOrOptions)) {
      return apiFetch<T>(endpoint, { ...bodyOrOptions, method: 'DELETE' })
    }
    return apiFetch<T>(endpoint, { ...options, method: 'DELETE', body: bodyOrOptions })
  },
}

/**
 * 带认证的文件下载
 * 通过 apiFetch 发请求（自动携带 token），获取 Blob 后触发浏览器下载
 */
export async function downloadFile(
  endpoint: string,
  filename?: string
): Promise<void> {
  const blob = await api.get<Blob>(endpoint, { responseType: 'blob' } as any)

  // 尝试从 blob 类型推断文件名，或使用默认名
  const downloadName = filename || endpoint.split('/').pop() || 'download'
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = downloadName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
