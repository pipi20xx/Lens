import { api } from './client'

export const pgsqlApi = {
  getStatus: () => api.get('/api/pgsql/status'),
  getDatabases: () => api.get('/api/pgsql/databases'),
  getTables: (db: string) => api.get(`/api/pgsql/databases/${db}/tables`),
  executeQuery: (query: string, db?: string) => api.post('/api/pgsql/query', { query, db }),
  getBackups: () => api.get('/api/pgsql/backups'),
  createBackup: (data: any) => api.post('/api/pgsql/backups', data),
  restoreBackup: (id: string) => api.post(`/api/pgsql/backups/${id}/restore`),
}
