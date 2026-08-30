import { api } from './client'

export const pgsqlApi = {
  // ========== 主机管理 ==========
  getHosts: () => api.get('/api/pgsql/hosts'),
  addHost: (host: any, name: string) =>
    api.post('/api/pgsql/hosts', host, { params: { name } }),
  updateHost: (id: string, host: any, name: string) =>
    api.put(`/api/pgsql/hosts/${id}`, host, { params: { name } }),
  deleteHost: (id: string) => api.delete(`/api/pgsql/hosts/${id}`),
  testConnection: (config: any) => api.post('/api/pgsql/test', config),

  // ========== 数据库操作 ==========
  getDatabases: (config: any) => api.post('/api/pgsql/databases', config),
  createDatabase: (config: any, req: { dbname: string; owner?: string }) =>
    api.post('/api/pgsql/databases/create', { config, req }),
  updateDatabase: (dbname: string, config: any, req: { owner?: string; description?: string }) =>
    api.patch(`/api/pgsql/databases/${dbname}`, { config, req }),
  dropDatabase: (dbname: string, config: any) =>
    api.delete(`/api/pgsql/databases/${dbname}`, { data: config }),

  // ========== 用户/角色操作 ==========
  getUsers: (config: any) => api.post('/api/pgsql/users', config),
  createUser: (config: any, req: any) =>
    api.post('/api/pgsql/users/create', { config, req }),
  updateUser: (username: string, config: any, req: any) =>
    api.patch(`/api/pgsql/users/${username}`, { config, req }),
  dropUser: (username: string, config: any) =>
    api.delete(`/api/pgsql/users/${username}`, { data: config }),

  // ========== 数据/表操作 ==========
  getTables: (config: any) => api.post('/api/pgsql/tables', config),
  getTableData: (config: any, params: { table_name: string; page: number; page_size: number }) =>
    api.post('/api/pgsql/data', { config, params }),
  dropTable: (tableName: string, config: any, cascade: boolean = false) =>
    api.delete(`/api/pgsql/tables/${encodeURIComponent(tableName)}${cascade ? '?cascade=true' : ''}`, { data: config }),
  truncateTable: (tableName: string, config: any) =>
    api.post(`/api/pgsql/tables/${encodeURIComponent(tableName)}/truncate`, config),

  // ========== 备份管理 ==========
  getBackups: () => api.get('/api/pgsql/backups'),
  createBackup: (config: any, req: { dbname: string }) =>
    api.post('/api/pgsql/backups/create', { config, req }),
  restoreBackup: (filename: string, config: any, dbname: string) =>
    api.post(`/api/pgsql/backups/restore/${filename}`, config, { params: { dbname } }),
  deleteBackup: (filename: string) => api.delete(`/api/pgsql/backups/${filename}`),
}
