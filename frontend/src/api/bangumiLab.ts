import { api } from './client'

export const bangumiLabApi = {
  search: (keyword: string) =>
    api.get('/api/bangumi_lab/search', { params: { keyword } }),
  getSubject: (subjectId: number) =>
    api.get(`/api/bangumi_lab/subject/${subjectId}`),
  getSubjectCharacters: (subjectId: number) =>
    api.get(`/api/bangumi_lab/subject/${subjectId}/characters`),
  getEpisodes: (params: any) =>
    api.get('/api/bangumi_lab/episodes', { params }),
}
