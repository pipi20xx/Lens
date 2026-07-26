import { api } from './client'

export const bookmarksApi = {
  /** 获取书签列表 (as_tree=true 返回树形结构) */
  list: (asTree = true) => api.get('/api/bookmarks/', { params: { as_tree: asTree } }),
  getBookmarks: (asTree = true) => api.get('/api/bookmarks/', { params: { as_tree: asTree } }),

  /** 创建书签/文件夹 */
  create: (data: any) => api.post('/api/bookmarks/', data),
  createBookmark: (data: any) => api.post('/api/bookmarks/', data),

  /** 更新书签 */
  update: (id: string, data: any) => api.put(`/api/bookmarks/${id}`, data),
  updateBookmark: (id: string, data: any) => api.put(`/api/bookmarks/${id}`, data),

  /** 删除书签 */
  delete: (id: string) => api.delete(`/api/bookmarks/${id}`),
  deleteBookmark: (id: string) => api.delete(`/api/bookmarks/${id}`),

  /** 清空所有书签 */
  deleteAll: () => api.delete('/api/bookmarks/'),
  clearBookmarks: () => api.delete('/api/bookmarks/'),

  /** 重复检测 */
  getDuplicates: () => api.get('/api/bookmarks/duplicates'),
  findDuplicates: () => api.get('/api/bookmarks/duplicates'),

  /** 批量健康检查 */
  checkHealth: (urls: string[]) => api.post('/api/bookmarks/check-health', { urls }),

  /** 导出书签 HTML */
  export: () => api.get('/api/bookmarks/export', { responseType: 'blob' }),
  exportBookmarks: () => {
    const link = document.createElement('a')
    link.href = '/api/bookmarks/export'
    link.setAttribute('download', '')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  },

  /** 重新排序 */
  reorder: (orderedIds: string[], parentId: string | null = undefined) =>
    api.post('/api/bookmarks/reorder', { ordered_ids: orderedIds, parent_id: parentId }),
  reorderBookmarks: (orderedIds: string[], parentId: string | null = undefined) =>
    api.post('/api/bookmarks/reorder', { ordered_ids: orderedIds, parent_id: parentId }),

  /** AI 自动整理 (SSE 流式) */
  aiAutoOrganize: (data: any) => api.post('/api/bookmarks/ai-auto-organize', data),

  /** 导入 HTML 书签文件 */
  importHtml: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/bookmarks/import-html', formData)
  },

  /** 获取网站图标 */
  fetchIcon: (url: string) => api.get('/api/navigation/fetch-icon', { params: { url } }),
}
