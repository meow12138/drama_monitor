import type { DramaItem, PlatformInfo, RankingsResponse, StatsItem } from '@/types/api'

const BASE_URL = ''

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, options)
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `请求失败: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function getRankings(params: {
  platform?: string
  rank_type?: string
  time_period?: string
  limit?: number
  offset?: number
}): Promise<RankingsResponse> {
  const qs = new URLSearchParams()
  if (params.platform) qs.set('platform', params.platform)
  if (params.rank_type) qs.set('rank_type', params.rank_type)
  if (params.time_period) qs.set('time_period', params.time_period)
  qs.set('limit', String(params.limit ?? 50))
  qs.set('offset', String(params.offset ?? 0))
  return request<RankingsResponse>(`/api/rankings?${qs}`)
}

export function getStats(): Promise<StatsItem[]> {
  return request<StatsItem[]>('/api/stats')
}

export function getPlatforms(): Promise<PlatformInfo[]> {
  return request<PlatformInfo[]>('/api/platforms')
}

export function triggerFetch(): Promise<{ status: string; fetched_items: number }> {
  return request<{ status: string; fetched_items: number }>('/api/trigger', {
    method: 'POST',
  })
}

export function getSchedulerStatus(): Promise<{ status: string; scheduler: any }> {
  return request('/health')
}

export function exportCsv(params: {
  platform?: string
  rank_type?: string
  time_period?: string
}): string {
  const qs = new URLSearchParams()
  if (params.platform) qs.set('platform', params.platform)
  if (params.rank_type) qs.set('rank_type', params.rank_type)
  if (params.time_period) qs.set('time_period', params.time_period)
  return `/api/export/csv?${qs}`
}
