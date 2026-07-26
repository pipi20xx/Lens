import { api } from './client'

export const configApi = {
  // 获取当前激活服务器配置及全局设置 (后端路由: /api/server/current)
  // 返回: config.json 全部内容 + session_never_expire
  getCurrent: () => api.get('/api/server/current'),

  // 保存全局配置/服务器配置 (后端路由: /api/server/save)
  // 此接口同时处理: 1) Emby服务器的新增/更新 2) 全局配置字段(如proxy/tmdb_api_key等)的更新
  saveGlobal: (data: any) => api.post('/api/server/save', data),

  // 获取数据库系统配置 (后端路由: /api/system/config)
  // 返回: api_token, auth_enabled, audit_enabled, ai_* 等
  getSystemConfig: () => api.get('/api/system/config'),

  // 批量更新数据库系统配置 (后端路由: /api/system/config)
  saveSystemConfig: (configs: Array<{ key: string; value: any; description?: string }>) =>
    api.post('/api/system/config', { configs }),

  // 导出 config.json (后端路由: /api/system/config/export)
  exportConfig: () => api.get('/api/system/config/export'),

  // 导入 config.json (后端路由: /api/system/config/import)
  importConfig: (formData: FormData) => api.post('/api/system/config/import', formData),
}
