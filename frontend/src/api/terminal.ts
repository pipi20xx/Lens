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
  saveCommand: (data: any) =>
    data.id ? api.put(`/api/terminal/commands/${data.id}`, data) : api.post('/api/terminal/commands', data),
  createCommand: (data: any) => api.post('/api/terminal/commands', data),
  updateCommand: (id: number, data: any) => api.put(`/api/terminal/commands/${id}`, data),
  deleteCommand: (id: number) => api.delete(`/api/terminal/commands/${id}`),
  reorderCommands: (ids: number[]) => api.post('/api/terminal/commands/reorder', ids),

  // ========== 文件管理 ==========
  ls: (hostId: number | string, path: string) =>
    api.get(`/api/files/${hostId}/ls`, { params: { path } }),
  read: (hostId: number | string, path: string) =>
    api.get(`/api/files/${hostId}/read`, { params: { path } }),
  write: (hostId: number | string, path: string, content: string) =>
    api.post(`/api/files/${hostId}/write`, { path, content }),
  action: (hostId: number | string, action: string, path: string, target?: string) =>
    api.post(`/api/files/${hostId}/action`, { action, path, target }),
  chmod: (hostId: number | string, data: any) =>
    api.post(`/api/files/${hostId}/chmod`, data),
  upload: (hostId: number | string, path: string, files: File[]) => {
    const formData = new FormData()
    formData.append('path', path)
    files.forEach(file => formData.append('files', file))
    return api.post(`/api/files/${hostId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  downloadUrl: (hostId: number | string, path: string) =>
    `/api/files/${hostId}/download?path=${encodeURIComponent(path)}`,

  // ========== WebSocket 终端 ==========
  getWsUrl: (hostId: string | number) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const token = localStorage.getItem('lens_access_token') || ''
    return `${protocol}//${host}/api/terminal/ws/${hostId}?token=${encodeURIComponent(token)}`
  },
}
