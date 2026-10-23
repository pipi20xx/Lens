/**
 * 代码仓库管理 API
 * 对应后端 app/modules/repo_manager（只调 git CLI，不碰远端 API 协议）
 */
import { api } from './client'

export interface RepoCounts {
  staged: number
  unstaged: number
  untracked: number
  conflict: number
}

export interface RepoSummary {
  path: string
  name: string
  ok: boolean
  branch: string
  detached: boolean
  upstream: string
  ahead: number
  behind: number
  counts: RepoCounts
  dirty: boolean
  pinned: boolean
  error?: string
}

export interface RepoFile {
  path: string
  orig_path: string
  xy: string
  kind: 'change' | 'rename' | 'conflict' | 'untracked'
  label: string
  staged: boolean
  unstaged: boolean
}

export interface RepoStatus {
  branch: {
    oid: string
    head: string
    upstream: string
    ahead: number
    behind: number
    detached: boolean
  }
  files: RepoFile[]
  counts: RepoCounts
}

export interface JobState {
  id: string
  kind: string
  status: 'running' | 'done' | 'failed'
  progress: number
  phase: string
  lines: string[]
  result: any
  error: string
}

export interface CommitItem {
  hash: string
  short: string
  author: string
  email: string
  date: string
  subject: string
  refs: string[]
}

export interface CommitFile {
  status: string
  path: string
  additions: number
  deletions: number
}

export interface CommitDetail {
  commit: Omit<CommitItem, 'refs'> & { body: string }
  files: CommitFile[]
}

export interface BranchItem {
  name: string
  current: boolean
  upstream: string
  date: string
}

export interface RemoteRepo {
  name: string
  full_name: string
  description: string
  private: boolean
  clone_url: string
  ssh_url: string
  updated: string
  default_branch: string
}

export interface IdentityProfile {
  id: string
  label: string
  provider: 'github' | 'gitea' | ''
  name: string
  email: string
}

export interface RepoIdentity {
  local: { name: string; email: string }
  resolved: { name: string; email: string }
  effective: { name: string; email: string }
  fallback: { name: string; email: string }
  source: 'repo' | 'git-global' | 'settings' | 'none'
  display: { name: string; email: string }
  identities: IdentityProfile[]
  message?: string
}

export interface RepoSettings {
  roots: string[]
  clone_dir: string
  pinned: string[]
  scan_depth: number
  author_name: string
  author_email: string
  identities: IdentityProfile[]
}

export interface BrowseEntry {
  name: string
  path: string
  is_git: boolean
  in_roots: boolean
}

export interface BrowseResult {
  path: string
  parent: string
  entries: BrowseEntry[]
  shortcuts: { label: string; path: string }[]
  is_git: boolean
  in_roots: boolean
}

export interface RepoEntry {
  name: string
  path: string
  type: 'dir' | 'file' | 'link'
  size: number
  mtime: number
}

export interface RepoDirListing {
  dir: string
  parent: string
  entries: RepoEntry[]
  truncated: boolean
}

export interface RepoFileContent {
  path: string
  size: number
  binary: boolean
  truncated: boolean
  content: string
  encoding: string
  eol: 'lf' | 'crlf' | 'cr' | ''
}

export interface RepoSearchFile {
  path: string
  name: string
}

export interface RepoSearchMatch {
  file: string
  line: number
  text: string
}

export interface RepoSearchResult {
  query: string
  files: RepoSearchFile[]
  matches: RepoSearchMatch[]
  truncated: boolean
}

const BASE = '/api/repo-manager'

export const repoManagerApi = {
  listRepos: (force = false) =>
    api.get<{ repos: RepoSummary[]; roots: string[] }>(`${BASE}/repos`, { params: { force } }),

  status: (path: string) => api.get<RepoStatus>(`${BASE}/status`, { params: { path } }),

  stage: (path: string, action: 'stage' | 'unstage' | 'discard', paths: string[]) =>
    api.post<{ ok: boolean; count: number }>(`${BASE}/stage`, { path, action, paths }),

  commit: (path: string, message: string, amend = false) =>
    api.post<{ commit: string; summary: string }>(`${BASE}/commit`, { path, message, amend }),

  push: (path: string, setUpstream = false, force = false) =>
    api.post<{ ok: boolean; detail: string }>(`${BASE}/push`, {
      path,
      set_upstream: setUpstream,
      force,
    }),

  pull: (path: string, rebase = false) =>
    api.post<{ ok: boolean; detail: string }>(`${BASE}/pull`, { path, rebase }),

  fetch: (path: string) => api.post(`${BASE}/fetch`, { path }),

  fetchAll: () => api.post<{ job_id: string }>(`${BASE}/fetch-all`),

  diff: (path: string, file: string, staged = false, untracked = false) =>
    api.get<{ diff: string }>(`${BASE}/diff`, { params: { path, file, staged, untracked } }),

  branches: (path: string) =>
    api.get<{ branches: BranchItem[] }>(`${BASE}/branches`, { params: { path } }),

  createBranch: (path: string, name: string, checkout = true) =>
    api.post(`${BASE}/branch/create`, { path, name, checkout }),

  switchBranch: (path: string, name: string) =>
    api.post(`${BASE}/branch/switch`, { path, name }),

  deleteBranch: (path: string, name: string, force = false) =>
    api.post(`${BASE}/branch/delete`, { path, name, force }),

  log: (path: string, limit = 50) =>
    api.get<{ commits: CommitItem[] }>(`${BASE}/log`, { params: { path, limit } }),

  commitDetail: (path: string, rev: string) =>
    api.get<CommitDetail>(`${BASE}/commit`, { params: { path, rev } }),

  commitFileDiff: (path: string, rev: string, file: string) =>
    api.get<{ diff: string }>(`${BASE}/commit/diff`, { params: { path, rev, file } }),

  resolve: (path: string, file: string, strategy: 'ours' | 'theirs') =>
    api.post(`${BASE}/resolve`, { path, file, strategy }),

  clone: (url: string, name = '', provider = '', targetDir = '', identityId = '') =>
    api.post<{ job_id: string }>(`${BASE}/clone`, {
      url,
      name,
      provider,
      target_dir: targetDir,
      identity_id: identityId,
    }),

  job: (id: string) => api.get<JobState>(`${BASE}/jobs/${id}`),

  identity: (path: string) => api.get<RepoIdentity>(`${BASE}/identity`, { params: { path } }),

  applyIdentity: (path: string, payload: { identity_id?: string; name?: string; email?: string }) =>
    api.post<RepoIdentity>(`${BASE}/identity`, { path, ...payload }),

  browse: (path = '') => api.get<BrowseResult>(`${BASE}/browse`, { params: { path } }),

  listFiles: (path: string, dir = '') =>
    api.get<RepoDirListing>(`${BASE}/files`, { params: { path, dir } }),

  readFile: (path: string, file: string) =>
    api.get<RepoFileContent>(`${BASE}/files/content`, { params: { path, file } }),

  saveFile: (path: string, file: string, content: string, encoding = '', eol = '') =>
    api.put<{ path: string; size: number; mtime: number; encoding: string; eol: string }>(
      `${BASE}/files/content`,
      { path, file, content, encoding, eol }
    ),

  search: (
    path: string,
    q: string,
    opts: { case?: boolean; whole?: boolean; regex?: boolean } = {}
  ) =>
    api.get<RepoSearchResult>(`${BASE}/search`, {
      params: {
        path,
        q,
        case: opts.case ?? false,
        whole: opts.whole ?? false,
        regex: opts.regex ?? false,
      },
    }),

  replace: (
    path: string,
    payload: {
      query: string
      replacement: string
      case?: boolean
      whole?: boolean
      regex?: boolean
      file?: string
    }
  ) =>
    api.post<{
      files: number
      replacements: number
      details: { file: string; count: number }[]
      skipped: string[]
    }>(`${BASE}/replace`, { path, ...payload }),

  remoteRepos: (provider: 'gitea' | 'github') =>
    api.get<{ repos: RemoteRepo[] }>(`${BASE}/providers/${provider}/repos`),

  getSettings: () =>
    api.get<{ settings: RepoSettings; roots: string[] }>(`${BASE}/settings`),

  saveSettings: (patch: Partial<RepoSettings>) =>
    api.put<{ settings: RepoSettings }>(`${BASE}/settings`, patch),
}
