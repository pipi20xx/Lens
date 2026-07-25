import { api } from './client'

export const dockerApi = {
  getContainers: () => api.get('/api/docker/containers'),
  getContainer: (id: string) => api.get(`/api/docker/containers/${id}`),
  startContainer: (id: string) => api.post(`/api/docker/containers/${id}/start`),
  stopContainer: (id: string) => api.post(`/api/docker/containers/${id}/stop`),
  restartContainer: (id: string) => api.post(`/api/docker/containers/${id}/restart`),
  removeContainer: (id: string) => api.delete(`/api/docker/containers/${id}`),
  getImages: () => api.get('/api/docker/images'),
  getImageBuildHistory: () => api.get('/api/image-builder/builds'),
  startBuild: (data: any) => api.post('/api/image-builder/build', data),
}
