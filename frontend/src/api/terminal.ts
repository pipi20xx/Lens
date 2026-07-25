import { api } from './client'

export const terminalApi = {
  createSession: (data: any) => api.post('/api/terminal/sessions', data),
  getSessions: () => api.get('/api/terminal/sessions'),
  deleteSession: (id: string) => api.delete(`/api/terminal/sessions/${id}`),
}
