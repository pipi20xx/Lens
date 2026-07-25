import { api } from './client'

export const imageBuilderApi = {
  // ========== 项目管理 ==========
  getProjects: () => api.get('/api/image-builder/projects'),
  getProject: (id: string) => api.get(`/api/image-builder/projects/${id}`),
  addProject: (data: any) => api.post('/api/image-builder/projects', data),
  updateProject: (id: string, data: any) => api.put(`/api/image-builder/projects/${id}`, data),
  deleteProject: (id: string) => api.delete(`/api/image-builder/projects/${id}`),

  // ========== 镜像仓库 ==========
  getRegistries: () => api.get('/api/image-builder/registries'),
  addRegistry: (data: any) => api.post('/api/image-builder/registries', data),
  updateRegistry: (id: string, data: any) => api.put(`/api/image-builder/registries/${id}`, data),
  deleteRegistry: (id: string) => api.delete(`/api/image-builder/registries/${id}`),
  testRegistry: (id: string) => api.post(`/api/image-builder/registries/${id}/test`),

  // ========== 凭证管理 ==========
  getCredentials: () => api.get('/api/image-builder/credentials'),
  addCredential: (data: any) => api.post('/api/image-builder/credentials', data),
  updateCredential: (id: string, data: any) => api.put(`/api/image-builder/credentials/${id}`, data),
  deleteCredential: (id: string) => api.delete(`/api/image-builder/credentials/${id}`),

  // ========== 代理管理 ==========
  getProxies: () => api.get('/api/image-builder/proxies'),
  addProxy: (data: any) => api.post('/api/image-builder/proxies', data),
  updateProxy: (id: string, data: any) => api.put(`/api/image-builder/proxies/${id}`, data),
  deleteProxy: (id: string) => api.delete(`/api/image-builder/proxies/${id}`),

  // ========== 构建任务 ==========
  buildProject: (id: string, tag: string) =>
    api.post(`/api/image-builder/projects/${id}/build`, { tag }),
  getTaskLogs: (projectId: string) =>
    api.get(`/api/image-builder/projects/${projectId}/tasks`),
  getTaskLogContent: (taskId: string) =>
    api.get(`/api/image-builder/tasks/${taskId}/log`),
  deleteTaskLog: (taskId: string) =>
    api.delete(`/api/image-builder/tasks/${taskId}`),
  clearAllTasks: () => api.delete('/api/image-builder/tasks'),

  // ========== 环境管理 ==========
  getSystemInfo: (hostId: string) =>
    api.get('/api/image-builder/system-info', { params: { host_id: hostId } }),
  setupEnv: (hostId: string, proxyId?: string) =>
    api.post('/api/image-builder/setup-env', { host_id: hostId, proxy_id: proxyId }),
}
