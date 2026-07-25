import { api } from './client'

export const filesApi = {
  // 列出目录
  ls: (hostId: number | string, path: string) =>
    api.get(`/api/files/${hostId}/ls`, { params: { path } }),

  // 读取文件
  read: (hostId: number | string, path: string) =>
    api.get(`/api/files/${hostId}/read`, { params: { path } }),

  // 写入文件
  write: (hostId: number | string, path: string, content: string) =>
    api.post(`/api/files/${hostId}/write`, { path, content }),

  // 文件操作 (rename/copy/move/delete 等)
  action: (hostId: number | string, action: string, path: string, target?: string) =>
    api.post(`/api/files/${hostId}/action`, { action, path, target }),

  // 修改权限
  chmod: (hostId: number | string, data: any) =>
    api.post(`/api/files/${hostId}/chmod`, data),

  // 上传文件
  upload: (hostId: number | string, path: string, files: File[]) => {
    const formData = new FormData()
    formData.append('path', path)
    files.forEach(file => formData.append('files', file))
    return api.post(`/api/files/${hostId}/upload`, formData)
  },

  // 下载 URL (直接用浏览器下载)
  downloadUrl: (hostId: number | string, path: string) =>
    `/api/files/${hostId}/download?path=${encodeURIComponent(path)}`,
}
