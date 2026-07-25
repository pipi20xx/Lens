/**
 * 全局类型定义
 */

// 进度数据
export interface ProgressData {
  status: 'idle' | 'running' | 'scanning' | 'completed' | 'error'
  current: number
  total: number
  message: string
}

// 日志条目
export interface LogEntry {
  time: string
  level: string
  message: string
  raw: string
}

// API 通用响应
export interface ApiResponse<T = any> {
  data?: T
  message?: string
  detail?: string
}

// 登录参数
export interface LoginParams {
  username: string
  password: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
}

// Emby 用户
export interface EmbyUser {
  Name: string
  Id: string
  IsAdmin: boolean
  IsDisabled: boolean
  LastActivityDate?: string
  [key: string]: any
}

// Emby 媒体库
export interface EmbyLibrary {
  ItemId: string
  Name: string
  Type: string
  [key: string]: any
}

// Docker 容器
export interface DockerContainer {
  id: string
  name: string
  image: string
  status: string
  state: string
  ports?: any
  [key: string]: any
}

// 系统配置
export interface SystemConfig {
  [key: string]: any
}

// 导航菜单分组
export interface NavGroup {
  key: string
  label: string
  icon: string
  visible: boolean
  type: 'group' | 'item'
  items: NavItem[]
}

export interface NavItem {
  key: string
  label: string
  icon: string
  to: string
}
