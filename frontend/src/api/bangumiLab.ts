import { api } from './client'

export const bangumiLabApi = {
  search: (keywords: string) =>
    api.get('/api/bangumi_lab/search', { params: { keywords } }),
  getSubject: (subjectId: number) =>
    api.get(`/api/bangumi_lab/subject/${subjectId}`),
  getDetail: (subjectId: number) =>
    api.get(`/api/bangumi_lab/subject/${subjectId}`),
  getSubjectCharacters: (subjectId: number) =>
    api.get(`/api/bangumi_lab/subject/${subjectId}/characters`),
  getEpisodes: (params: any) =>
    api.get('/api/bangumi_lab/episodes', { params }),
  linkToEmby: (bangumiId: number, embyId: string) =>
    api.post('/api/bangumi_lab/link-to-emby', { bangumi_id: bangumiId, emby_id: embyId }),
}
