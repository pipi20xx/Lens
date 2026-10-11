/**
 * 番剧分季拆分 API
 * 后端路由: /api/cure-splitter/*
 * 集成配置（TMDB/TVDB/Bangumi Key、代理、Gitea、SYTMDB）在「设置 → 第三方 API 集成」维护
 */
import { api } from './client'

export interface LogEntry {
  time: string
  level: string
  message: string
}

export interface TaskStatus {
  task_id: string
  status: 'running' | 'done' | 'failed'
  logs: LogEntry[]
  error?: string | null
}

export interface DefinitionRow {
  season_number: number
  name: string
  episode_count: number
  include_desc: string
}

export interface SeasonRow {
  season_number: number
  name: string
  episode_count: number
  air_date: string
}

export interface EpisodeRow {
  season: number
  episode: number
  org_season: number
  org_episode: number | null
  type: string
  air_date: string
  name: string
}

export interface SplitResult {
  tmdb_id: number
  title: string
  reference: string
  split_done: boolean
  definition_rows: DefinitionRow[]
  season_rows: SeasonRow[]
  episode_rows: EpisodeRow[]
  render_words: string
  group_json: { description: string; groups: any[]; id: string } | null
  mapping_json: Record<string, Record<string, { season: number; episode: number }>> | null
  logic_json: any
}

export interface SplitRunPayload {
  tmdb_id: number
  language: string
  source: string
  use_source: boolean
  priority: string
  force_reference: boolean
}

export interface GiteaEntry {
  path: string
  type: 'file' | 'dir'
}

export interface GiteaPushResult {
  action: 'replaced' | 'appended' | 'conflict'
  info?: string
  commit?: string
  message?: string
}

export const cureSplitterApi = {
  /** 开始拆分（后台任务），返回 task_id */
  startSplit: (payload: SplitRunPayload) =>
    api.post<{ task_id: string }>('/api/cure-splitter/split', payload),

  /** 轮询任务状态与日志 */
  taskStatus: (taskId: string) =>
    api.get<TaskStatus>(`/api/cure-splitter/tasks/${taskId}`),

  /** 获取拆分结果 */
  taskResult: (taskId: string) =>
    api.get<SplitResult>(`/api/cure-splitter/tasks/${taskId}/result`),

  /** 列出仓库目录内容（含子目录，目录在前），供逐级浏览选择渲染词文件 */
  listGiteaFiles: (dirPath = '', provider: 'gitea' | 'github' = 'gitea') =>
    api.post<{ files: GiteaEntry[] }>('/api/cure-splitter/gitea/list-dir', {
      dir_path: dirPath,
      provider,
    }),

  /** 推送渲染词到仓库；content 可传手动编辑后的文本（空则用任务生成结果）；
   *  action=conflict 表示命中手动区块，需确认后带 force_manual 重推 */
  pushToGitea: (payload: {
    task_id: string
    file_path?: string
    force_manual?: boolean
    content?: string
    provider?: 'gitea' | 'github'
  }) =>
    api.post<GiteaPushResult>('/api/cure-splitter/gitea/push', payload),

  /** 剧集组覆盖写入 SYTMDB */
  writeToSytmdb: (taskId: string) =>
    api.post<{ ok: boolean; message: string; groups: number; tmdb_id: number }>(
      '/api/cure-splitter/sytmdb/write', { task_id: taskId },
    ),
}
