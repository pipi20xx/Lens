import { api } from './client'

export const dockerApi = {
  // ========== 主机管理 ==========
  getHosts: () => api.get('/api/docker/hosts'),
  addHost: (data: any) => api.post('/api/docker/hosts', data),
  updateHost: (id: string, data: any) => api.put(`/api/docker/hosts/${id}`, data),
  deleteHost: (id: string) => api.delete(`/api/docker/hosts/${id}`),
  testConnection: (hostId: string) => api.post(`/api/docker/${hostId}/test`),

  // ========== 容器管理 ==========
  getContainers: (hostId: string, details?: boolean) =>
    api.get(`/api/docker/${hostId}/containers`, { params: { details } }),
  getContainerStats: (hostId: string) =>
    api.get(`/api/docker/${hostId}/containers/stats`),
  containerAction: (hostId: string, containerId: string, action: string) =>
    api.post(`/api/docker/${hostId}/containers/${containerId}/action`, { action }),
  getContainerLogs: (hostId: string, containerId: string, tail?: number) =>
    api.get(`/api/docker/${hostId}/containers/${containerId}/logs`, { params: { tail } }),

  // ========== Compose 项目 ==========
  getComposeProjects: (hostId: string) =>
    api.get(`/api/docker/compose/${hostId}/projects`),
  getComposeProject: (hostId: string, name: string) =>
    api.get(`/api/docker/compose/${hostId}/projects/${name}`),
  createComposeProject: (hostId: string, data: any) =>
    api.post(`/api/docker/compose/${hostId}/projects`, data),
  composeProjectAction: (hostId: string, name: string, action: string) =>
    api.post(`/api/docker/compose/${hostId}/projects/${name}/action`, { action }),
  composeBulkAction: (hostId: string, data: any) =>
    api.post(`/api/docker/compose/${hostId}/projects/bulk-action`, data),
  composeChmod: (hostId: string, data: any) =>
    api.post(`/api/docker/compose/${hostId}/chmod`, data),
  deleteComposeProject: (hostId: string, name: string) =>
    api.delete(`/api/docker/compose/${hostId}/projects/${name}`),
  createComposeBackupTask: (hostId: string, name: string, data?: any) =>
    api.post(`/api/docker/compose/${hostId}/projects/${name}/create-backup-task`, data),
  createFolderBackup: (hostId: string, data: any) =>
    api.post(`/api/docker/compose/${hostId}/create-folder-backup`, data),
  composeLs: (hostId: string) =>
    api.get(`/api/docker/compose/${hostId}/ls`),

  // ========== 镜像更新检测 ==========
  checkImageUpdate: (hostId: string, image: string) =>
    api.get(`/api/docker/${hostId}/check-image-update`, { params: { image } }),

  // ========== 清理操作 ==========
  pruneImages: (hostId: string, dangling?: boolean, allUnused?: boolean) =>
    api.post(`/api/docker/${hostId}/prune-images`, { dangling, all_unused: allUnused }),
  pruneCache: (hostId: string) =>
    api.post(`/api/docker/${hostId}/prune-cache`),
  pruneContainers: (hostId: string) =>
    api.post(`/api/docker/${hostId}/prune-containers`),
  pruneAll: (hostId: string, options: {
    images_dangling?: boolean
    images_unused?: boolean
    build_cache?: boolean
    containers?: boolean
    networks?: boolean
  }) => api.post(`/api/docker/${hostId}/prune`, options),

  // ========== 系统信息 & 环境安装 ==========
  getSystemInfo: (hostId: string) =>
    api.get(`/api/docker/${hostId}/system-info`),
  installEnv: (hostId: string, useMirror?: boolean, proxy?: string) =>
    api.post(`/api/docker/${hostId}/install-env`, { use_mirror: useMirror, proxy }),
  serviceAction: (hostId: string, action: string) =>
    api.post(`/api/docker/${hostId}/service-action`, { action }),

  // ========== Daemon 配置 ==========
  getDaemonConfig: (hostId: string) =>
    api.get(`/api/docker/${hostId}/daemon-config`),
  saveDaemonConfig: (hostId: string, config: any, restart?: boolean) =>
    api.post(`/api/docker/${hostId}/daemon-config`, { config, restart }),
  getDaemonConfigRaw: (hostId: string) =>
    api.get(`/api/docker/${hostId}/daemon-config/raw`),
  saveDaemonConfigRaw: (hostId: string, content: string, restart?: boolean) =>
    api.post(`/api/docker/${hostId}/daemon-config/raw`, { content, restart }),

  // ========== 容器设置 & 自动更新 ==========
  getContainerSettings: () =>
    api.get('/api/docker/container-settings'),
  saveContainerSettings: (containerName: string, settings: any) =>
    api.post(`/api/docker/container-settings/${containerName}`, settings),
  getAutoUpdateSettings: () =>
    api.get('/api/docker/auto-update/settings'),
  saveAutoUpdateSettings: (data: { enabled: boolean; type: string; value: string }) =>
    api.post('/api/docker/auto-update/settings', data),
}
