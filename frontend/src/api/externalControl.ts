import { api } from './client'

export const externalControlApi = {
  // 控制规则
  getRules: () => api.get('/api/external-control/rules'),
  createRule: (data: any) => api.post('/api/external-control/rules', data),
  updateRule: (id: string, data: any) => api.put(`/api/external-control/rules/${id}`, data),
  deleteRule: (id: string) => api.delete(`/api/external-control/rules/${id}`),

  // 执行日志
  getLogs: () => api.get('/api/external-control/logs'),
}
