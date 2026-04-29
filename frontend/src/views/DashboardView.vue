<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { DramaItem, StatsItem } from '@/types/api'
import { getRankings, getStats, triggerFetch, exportCsv } from '@/api'

const PLATFORM_NAMES: Record<string, string> = {
  dramabox: 'DramaBox',
  reelshort: 'ReelShort',
  shortmax: 'ShortMax',
  flextv: 'FlexTV',
  serealplus: 'Sereal+',
  netshort: 'NetShort',
  melolo: 'Melolo',
  goodshort: 'GoodShort',
  moboreels: 'MoboReels',
}

const LIKE_PLATFORMS = new Set(['flextv', 'serealplus', 'netshort'])

const loading = ref(false)
const tableData = ref<DramaItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const stats = ref<StatsItem[]>([])

const filterPlatform = ref('')
const filterRankType = ref('hot')
const filterTimePeriod = ref('today')

const isTriggering = ref(false)
const triggerLabel = ref('立即抓取')
const countdownText = ref('--:--')

let countdownInterval: ReturnType<typeof setInterval> | null = null
let triggerResetTimer: ReturnType<typeof setTimeout> | null = null
const FETCH_INTERVAL = 3 * 60

const playColumnLabel = computed(() => {
  const p = filterPlatform.value
  if (p === 'flextv') return '点赞数'
  if (p === 'serealplus' || p === 'netshort') return '点赞量'
  return '播放量'
})

const showMetricColumns = computed(() => filterPlatform.value !== 'melolo')

const platformStats = computed(() => {
  const map: Record<string, { count: number; last_updated: string | null }> = {}
  stats.value.forEach((s) => {
    const entry = map[s.platform]
    if (entry) {
      entry.count += s.count
    } else {
      map[s.platform] = { count: s.count, last_updated: s.last_updated }
    }
  })
  return Object.entries(map).map(([key, val]) => ({
    key,
    ...val,
    name: PLATFORM_NAMES[key] || key,
  }))
})

function formatMetric(value: number | null) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (!Number.isFinite(num) || num <= 0) return '—'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(num >= 10_000_000 ? 1 : 2).replace(/\.?0+$/, '') + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(num >= 10_000 ? 1 : 2).replace(/\.?0+$/, '') + 'K'
  return String(num)
}

function formatPlayNum(item: DramaItem) {
  const selectedPlatform = filterPlatform.value
  if (!selectedPlatform && LIKE_PLATFORMS.has(item.platform)) {
    return '—'
  }
  return formatMetric(item.play_num)
}

function getStatusType(score: number | null) {
  if (score === null || score === undefined) return 'info'
  if (score >= 8) return 'success'
  if (score >= 6) return 'warning'
  return 'info'
}

function parseTags(tags: string | null): string[] {
  if (!tags) return []
  return tags.split(',').map((t: string) => t.trim()).filter(Boolean)
}

function getScoreClass(score: number | null) {
  if (score === null || score === undefined) return ''
  if (score >= 8) return 'score-high'
  if (score >= 6) return 'score-mid'
  return 'score-low'
}

async function loadData() {
  loading.value = true
  try {
    const res = await getRankings({
      platform: filterPlatform.value || undefined,
      rank_type: filterRankType.value,
      time_period: filterTimePeriod.value,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
    tableData.value = res.items
    total.value = res.total
  } catch (err: any) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getStats()
  } catch (e) {
    console.error(e)
  }
}

async function onTriggerFetch() {
  if (isTriggering.value) return
  isTriggering.value = true
  triggerLabel.value = '抓取中...'
  if (triggerResetTimer) clearTimeout(triggerResetTimer)
  try {
    const data = await triggerFetch()
    await loadData()
    triggerLabel.value = `已抓取 ${data.fetched_items} 条`
  } catch (err: any) {
    triggerLabel.value = '抓取失败'
  } finally {
    isTriggering.value = false
    triggerResetTimer = setTimeout(() => {
      triggerLabel.value = '立即抓取'
    }, 2500)
  }
}

function onExportCsv() {
  const url = exportCsv({
    platform: filterPlatform.value || undefined,
    rank_type: filterRankType.value,
    time_period: filterTimePeriod.value,
  })
  window.open(url, '_blank')
}

function onPageChange(page: number) {
  currentPage.value = page
  loadData()
}

function startCountdown() {
  let remaining = FETCH_INTERVAL
  if (countdownInterval) clearInterval(countdownInterval)
  countdownInterval = setInterval(() => {
    remaining--
    if (remaining <= 0) {
      remaining = FETCH_INTERVAL
      loadData()
      loadStats()
    }
    const mins = Math.floor(remaining / 60)
    const secs = remaining % 60
    countdownText.value = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }, 1000)
}

function onFilterChange() {
  currentPage.value = 1
  loadData()
}

onMounted(() => {
  loadData()
  loadStats()
  startCountdown()
})

onUnmounted(() => {
  if (countdownInterval) clearInterval(countdownInterval)
  if (triggerResetTimer) clearTimeout(triggerResetTimer)
})
</script>

<template>
  <div>
    <!-- Breadcrumb -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/' }">监控首页</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- Filter Card -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-grid">
        <div class="filter-row-item">
          <span class="filter-label">平台</span>
          <el-select v-model="filterPlatform" placeholder="全部平台" clearable @change="onFilterChange">
            <el-option label="全部平台" value="" />
            <el-option label="DramaBox" value="dramabox" />
            <el-option label="ReelShort" value="reelshort" />
            <el-option label="ShortMax" value="shortmax" />
            <el-option label="FlexTV" value="flextv" />
            <el-option label="Sereal+" value="serealplus" />
            <el-option label="NetShort" value="netshort" />
            <el-option label="Melolo" value="melolo" />
            <el-option label="GoodShort" value="goodshort" />
            <el-option label="MoboReels" value="moboreels" />
          </el-select>
        </div>
        <div class="filter-row-item">
          <span class="filter-label">榜单类型</span>
          <el-select v-model="filterRankType" placeholder="请选择" @change="onFilterChange">
            <el-option label="近期热剧榜" value="hot" />
            <el-option label="新剧飙升榜" value="rising" />
          </el-select>
        </div>
        <div class="filter-row-item">
          <span class="filter-label">时间周期</span>
          <el-select v-model="filterTimePeriod" placeholder="请选择" @change="onFilterChange">
            <el-option label="今日" value="today" />
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
          </el-select>
        </div>
        <div class="filter-row-item">
          <span class="filter-label">搜索</span>
          <el-input placeholder="书名/作者（预留）" disabled />
        </div>
      </div>
      <div class="filter-actions">
        <el-button type="primary" :loading="isTriggering" @click="onTriggerFetch">
          <el-icon class="btn-icon"><Lightning /></el-icon>
          {{ triggerLabel }}
        </el-button>
        <el-button @click="loadData">
          <el-icon class="btn-icon"><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="onExportCsv">
          <el-icon class="btn-icon"><Download /></el-icon>
          导出CSV
        </el-button>
        <span class="countdown">下次更新: <span class="countdown-num">{{ countdownText }}</span></span>
      </div>
    </el-card>

    <!-- Table Card -->
    <el-card shadow="never" class="table-card">
      <div class="table-wrapper">
        <el-table
          :data="tableData"
          v-loading="loading"
          style="width: 100%"
          :header-cell-style="{
            background: 'rgb(242,243,245)',
            color: '#323335',
            fontWeight: '600',
            fontSize: '13px',
          }"
          class="zw-table"
        >
          <el-table-column prop="rank_position" label="排名" width="80" align="center">
            <template #default="{ row }">
              <span
                class="rank-badge"
                :class="{ 'rank-top': row.rank_position <= 3 }"
              >
                {{ row.rank_position }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="短剧名称" min-width="200">
            <template #default="{ row }">
              <div class="drama-name-cell">
                <img v-if="row.cover_url" :src="row.cover_url" class="drama-cover" alt="" />
                <div v-else class="drama-cover placeholder">无图</div>
                <span class="drama-name">{{ row.drama_name }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="platform" label="平台" width="110" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="light">{{ PLATFORM_NAMES[row.platform] || row.platform }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="标签" min-width="140">
            <template #default="{ row }">
              <span v-if="row.tags" class="tag-list">
                <el-tag
                  v-for="tag in parseTags(row.tags)"
                  :key="tag"
                  size="small"
                  effect="plain"
                  class="tag-item"
                >
                  {{ tag }}
                </el-tag>
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <el-table-column prop="score" label="评分" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.score !== null && row.score !== undefined" :class="['score-text', getScoreClass(row.score)]">
                {{ row.score.toFixed(1) }}
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <el-table-column v-if="showMetricColumns" :label="playColumnLabel" width="100" align="right">
            <template #default="{ row }">
              <span class="cell-num">{{ formatPlayNum(row) }}</span>
            </template>
          </el-table-column>

          <el-table-column v-if="showMetricColumns" prop="collect_num" label="收藏量" width="100" align="right">
            <template #default="{ row }">
              <span class="cell-num">{{ formatMetric(row.collect_num) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="链接" width="80" align="center">
            <template #default="{ row }">
              <a v-if="row.link" :href="row.link" target="_blank" class="link-btn">查看 →</a>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <el-table-column prop="updated_at" label="更新时间" width="160" align="center">
            <template #default="{ row }">
              {{ row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : '—' }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        :background="true"
        layout="prev, pager, next"
        @current-change="onPageChange"
      />

      <el-empty v-if="!loading && tableData.length === 0" description="暂无数据" />
    </el-card>
  </div>
</template>

<style scoped>
.breadcrumb {
  margin-bottom: 16px;
  font-size: 13px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  margin-bottom: 16px;
}

.stat-label {
  font-size: 13px;
  color: var(--zw-text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--zw-text);
}

.stat-time {
  font-size: 12px;
  color: var(--zw-text-secondary);
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px 16px;
  margin-bottom: 10px;
}

.filter-row-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.filter-label {
  font-size: 13px;
  color: var(--zw-text);
  white-space: nowrap;
  flex-shrink: 0;
  width: 4.5em;
}

.filter-row-item :deep(.el-select),
.filter-row-item :deep(.el-input) {
  flex: 1;
  min-width: 0;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: calc(4.5em + 8px);
}

.btn-icon {
  margin-right: 4px;
}

.countdown {
  margin-left: auto;
  font-size: 13px;
  color: var(--zw-text-secondary);
}

.countdown-num {
  font-family: monospace;
  font-weight: 500;
  color: var(--zw-primary);
}

.table-card {
  margin-bottom: 16px;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.zw-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.zw-table :deep(.el-table__row) {
  transition: background-color 0.15s;
}

.zw-table :deep(.el-table__row:hover > td) {
  background-color: #f5f7fa !important;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 600;
  color: var(--zw-text);
  background: #f0f2f5;
}

.rank-badge.rank-top {
  background: #fee2e2;
  color: #ef4444;
}

.drama-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drama-cover {
  width: 36px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.drama-cover.placeholder {
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--zw-text-secondary);
}

.drama-name {
  font-weight: 500;
  color: var(--zw-text);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-item {
  margin: 0;
}

.score-text {
  font-weight: 700;
}

.score-high {
  color: #f53f3f;
}

.score-mid {
  color: #ff7d00;
}

.score-low {
  color: var(--zw-text-secondary);
}

.cell-num {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.link-btn {
  color: var(--el-color-primary);
  font-size: 12px;
  text-decoration: none;
}

.link-btn:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 1200px) {
  .filter-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .filter-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
  .filter-actions {
    padding-left: 0;
    flex-wrap: wrap;
  }
  .countdown {
    width: 100%;
    margin-left: 0;
    margin-top: 8px;
  }
}
</style>
