import { api } from './client'

export const navigationApi = {
  // ========== 设置管理 ==========
  getSettings: () => api.get('/api/navigation/settings'),
  updateSettings: (settings: any) => api.put('/api/navigation/settings', settings),
  uploadBackground: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/navigation/upload-bg', formData)
  },
  saveRemoteBackground: (url: string) =>
    api.post('/api/navigation/save-remote-bg', { url }),
  uploadIcon: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/navigation/upload-icon', formData)
  },
  fetchIcon: (url: string) =>
    api.get('/api/navigation/fetch-icon', { params: { url } }),
  getBingWallpaper: (index?: number, mkt?: string, resolution?: string) =>
    api.get('/api/navigation/bing-wallpaper', { params: { index, mkt, resolution } }),

  // ========== 分类管理 ==========
  getCategories: () => api.get('/api/navigation/categories'),
  createCategory: (data: { name: string; icon?: string; order?: number }) =>
    api.post('/api/navigation/categories', data),
  updateCategory: (id: number, data: { name: string; icon?: string; order?: number }) =>
    api.put(`/api/navigation/categories/${id}`, data),
  deleteCategory: (id: number) => api.delete(`/api/navigation/categories/${id}`),
  reorderCategories: (orderedIds: number[]) =>
    api.post('/api/navigation/categories/reorder', orderedIds),

  // ========== 站点管理 ==========
  getSites: () => api.get('/api/navigation/'),
  createSite: (data: any) => api.post('/api/navigation/', data),
  updateSite: (id: number, data: any) => api.put(`/api/navigation/${id}`, data),
  deleteSite: (id: number) => api.delete(`/api/navigation/${id}`),
  reorderSites: (orderedIds: number[]) =>
    api.post('/api/navigation/reorder', orderedIds),

  // ========== 书签管理 ==========
  getBookmarks: (asTree?: boolean) =>
    api.get('/api/navigation/bookmarks', { params: { as_tree: asTree } }),
  createBookmark: (data: any) => api.post('/api/navigation/bookmarks', data),
  updateBookmark: (id: string, data: any) => api.put(`/api/navigation/bookmarks/${id}`, data),
  deleteBookmark: (id: string) => api.delete(`/api/navigation/bookmarks/${id}`),
  reorderBookmarks: (orderedIds: number[], parentId?: string) =>
    api.post('/api/navigation/bookmarks/reorder', { ordered_ids: orderedIds, parent_id: parentId }),
  importBookmarksHtml: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/navigation/bookmarks/import-html', formData)
  },

  // ========== 备份恢复 ==========
  exportNavigation: () => api.get('/api/navigation/export'),
  importNavigation: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/navigation/import', formData)
  },
}
