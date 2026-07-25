import { api } from './client'

export const imageBuilderApi = {
  getBuilds: () => api.get('/api/image-builder/builds'),
  startBuild: (data: any) => api.post('/api/image-builder/build', data),
  getBuildLog: (id: string) => api.get(`/api/image-builder/builds/${id}/log`),
  cancelBuild: (id: string) => api.post(`/api/image-builder/builds/${id}/cancel`),
}
