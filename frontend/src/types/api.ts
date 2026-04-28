export interface DramaItem {
  id: number
  drama_name: string
  platform: string
  tags: string | null
  time_period: string
  rank_type: string
  rank_position: number
  score: number | null
  link: string | null
  cover_url: string | null
  play_num: number | null
  collect_num: number | null
  created_at: string
  updated_at: string | null
}

export interface StatsItem {
  platform: string
  rank_type: string
  time_period: string
  count: number
  last_updated: string | null
}

export interface PlatformInfo {
  key: string
  name: string
  base_url: string
}

export interface RankingQuery {
  platform?: string
  rank_type?: string
  time_period?: string
  limit?: number
  offset?: number
}

export interface RankingsResponse {
  items: DramaItem[]
  total: number
  limit: number
  offset: number
}
