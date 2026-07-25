import { api } from './client'

export interface BackupTask {
  id?: string
  name: string
  mode: string
  storage_type: string
  sync_strategy: string
  compression_level: number
  src_path: string
  dst_path: string
  password?: string
  enabled: boolean
  schedule_type: string
  schedule_value: string
  ignore_patterns: string[]
  host_id: string
}

export const backupApi = {
  // 备份任务 CRUD
  getTasks: () => api.get<BackupTask[]>('/api/backup/tasks'),
  createTask: (task: BackupTask) => api.post('/api/backup/tasks', task),
  updateTask: (id: string, task: BackupTask) => api.put(`/api/backup/tasks/${id}`, task),
  deleteTask: (id: string) => api.delete(`/api/backup/tasks/${id}`),
  runTask: (id: string) => api.post(`/api/backup/tasks/${id}/run`),

  // 备份历史
  getHistory: (taskId?: string, limit?: number) =>
    api.get('/api/backup/history', { params: { task_id: taskId, limit } }),

  // 还原
  restoreBackup: (historyId: number, clearDst?: boolean) =>
    api.post(`/api/backup/history/${historyId}/restore`, { params: { clear_dst: clearDst } }),

  // 路径浏览器
  browsePath: (path: string) => api.get('/api/backup/path-browser', { params: { path } }),
}
