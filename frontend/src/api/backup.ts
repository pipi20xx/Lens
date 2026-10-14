import { api } from './client'

export interface BackupTask {
  id?: string
  name: string
  mode: string // '7z', 'tar', 'sync', 'pgsql', 'gitea'
  storage_type: string // 'ssd', 'hdd', 'cloud'
  sync_strategy: string // 'mirror', 'incremental'
  compression_level: number
  src_path: string
  dst_path: string
  password?: string
  enabled: boolean
  schedule_type: string // 'cron', 'interval'
  schedule_value: string
  ignore_patterns: string[]
  host_id: string
  // PostgreSQL 支持
  pgsql_host_id?: string
  db_names?: string[]
  // Gitea 仓库归档支持（连接信息复用系统设置里的 Gitea 配置）
  gitea_repos?: string[] // 仓库 full_name；留空 = 备份全部可见仓库
  gitea_format?: string // 'tar.gz' | 'zip'
  gitea_ref?: string // 留空 = 各仓库自己的默认分支
}

export interface GiteaRepo {
  full_name: string
  name: string
  owner: string
  private: boolean
  default_branch: string
  size_kb: number // Gitea 的 size 字段单位是 KiB
  updated_at?: string
  description?: string
}

export interface BackupHistory {
  id: number
  task_id: string
  task_name: string
  start_time: string
  end_time?: string
  status: string
  mode: string
  size: number
  message?: string
  output_path?: string
}

export interface PathBrowserItem {
  name: string
  is_dir: boolean
  path: string
  size: number
}

export const backupApi = {
  // ========== 备份任务 ==========
  getTasks: () => api.get<BackupTask[]>('/api/backup/tasks'),

  saveTask: (task: BackupTask) => {
    if (task.id) {
      return api.put(`/api/backup/tasks/${task.id}`, task)
    } else {
      return api.post('/api/backup/tasks', task)
    }
  },

  deleteTask: (id: string) => api.delete(`/api/backup/tasks/${id}`),

  runTask: (id: string) => api.post(`/api/backup/tasks/${id}/run`),

  // ========== 备份历史 ==========
  getHistory: (taskId?: string) =>
    api.get<BackupHistory[]>('/api/backup/history', { params: { task_id: taskId } }),

  // 还原备份
  restoreBackup: (historyId: number, clearDst: boolean = false) =>
    api.post(`/api/backup/history/${historyId}/restore`, null, { params: { clear_dst: clearDst } }),

  // ========== 路径浏览器 ==========
  browsePath: (path: string) =>
    api.get<{ current_path: string; items: PathBrowserItem[] }>('/api/backup/path-browser', { params: { path } }),

  // ========== Gitea 仓库（复用系统设置里的 Gitea 连接配置）==========
  listGiteaRepos: () => api.get<GiteaRepo[]>('/api/backup/gitea/repos'),
}
