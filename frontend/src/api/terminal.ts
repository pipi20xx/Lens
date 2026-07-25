import { api } from './client'

export interface TerminalHost {
  id: number
  name: string
  host: string
  port: number
  username: string
  auth_type: string
  password?: string
  private_key?: string
}

export const terminalApi = {
  // ========== 主机管理 ==========
  getHosts: () => api.get<TerminalHost[]>('/api/terminal/hosts'),
  createHost: (data: any) => api.post('/api/terminal/hosts', data),
  updateHost: (id: number, data: any) => api.put(`/api/terminal/hosts/${id}`, data),
  deleteHost: (id: number) => api.delete(`/api/terminal/hosts/${id}`),

  // ========== 快速命令 ==========
  getCommands: () => api.get('/api/terminal/commands'),
  createCommand: (data: any) => api.post('/api/terminal/commands', data),
  updateCommand: (id: number, data: any) => api.put(`/api/terminal/commands/${id}`, data),
  deleteCommand: (id: number) => api.delete(`/api/terminal/commands/${id}`),
  reorderCommands: (ids: number[]) => api.post('/api/terminal/commands/reorder', ids),

  // ========== WebSocket 终端 ==========
  // 获取 WebSocket 连接 URL (需在前端 new WebSocket(url) 使用)
  getWsUrl: (hostId: string | number) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const token = localStorage.getItem('lens_access_token') || ''
    return `${protocol}//${host}/api/terminal/ws/${hostId}?token=${encodeURIComponent(token)}`
  },
}
