/**
 * 识别词生成器 API
 * 后端路由: /api/recognition-words/*
 */
import { api } from './client'

export interface AnchorRow {
  filename: string
  anchor: string
  valid: boolean
  rule: string
}

export interface GenerateResult {
  rules_text: string
  rows: AnchorRow[]
  warnings: string[]
  hint: string
}

export interface GeneratePayload {
  filenames: string[]
  tmdbid: string
  mtype: string
  season: string
  loose: boolean
  boundary: boolean
  keep_group: boolean
  date_comment: boolean
  /** 手动锚点（与 filenames 一一对应）；不传则后端自动提取 */
  anchors?: string[]
}

export const recognitionWordsApi = {
  generate: (payload: GeneratePayload) =>
    api.post<GenerateResult>('/api/recognition-words/generate', payload),
}
