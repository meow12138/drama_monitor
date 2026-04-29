<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { CrossRankingItem, PlatformSummaryItem } from '@/types/api'
import { getCompare } from '@/api'

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent])

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

const PLATFORM_COLORS: Record<string, string> = {
  dramabox: '#409EFF',
  reelshort: '#67C23A',
  shortmax: '#E6A23C',
  flextv: '#F56C6C',
  serealplus: '#909399',
  netshort: '#00BCD4',
  melolo: '#9C27B0',
  goodshort: '#FF9800',
  moboreels: '#795548',
}

const filterRankType = ref('hot')
const filterTimePeriod = ref('today')
const filterTopN = ref(20)
const loading = ref(false)

const crossRanking = ref<CrossRankingItem[]>([])
const platformSummary = ref<PlatformSummaryItem[]>([])

function formatNum(value: number): string {
  if (value >= 1_000_000) {
    const v = value / 1_000_000
    return (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, '') + 'M'
  }
  if (value >= 1_000) {
    const v = value / 1_000
    return (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, '') + 'K'
  }
  return String(value)
}

async function loadData() {
  loading.value = true
  try {
    const res = await getCompare({
      rank_type: filterRankType.value,
      time_period: filterTimePeriod.value,
      top_n: filterTopN.value,
    })
    crossRanking.value = res.cross_ranking
    platformSummary.value = res.platform_summary
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const crossRankingOption = computed(() => {
  const items = [...crossRanking.value].reverse()
  if (!items.length) return {}

  const platforms = [...new Set(items.map((d) => d.platform))]
  const seriesMap: Record<string, { name: string; type: string; stack: string; data: (number | null)[]; itemStyle: { color: string }; barMaxWidth: number }> = {}
  platforms.forEach((p) => {
    seriesMap[p] = {
      name: PLATFORM_NAMES[p] || p,
      type: 'bar',
      stack: 'total',
      data: items.map(() => null),
      itemStyle: { color: PLATFORM_COLORS[p] || '#999' },
      barMaxWidth: 24,
    }
  })
  items.forEach((item, idx) => {
    const series = seriesMap[item.platform]
    if (series) series.data[idx] = item.play_num
  })

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any) {
        const item = Array.isArray(params) ? params.find((p: any) => p.value != null) : params
        if (!item) return ''
        return `<b>${item.name}</b><br/>${item.seriesName}: ${formatNum(item.value)}`
      },
    },
    legend: { show: platforms.length > 1, top: 0 },
    grid: { left: 20, right: 40, top: platforms.length > 1 ? 36 : 16, bottom: 10, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => formatNum(v) },
    },
    yAxis: {
      type: 'category',
      data: items.map(
        (d) => d.drama_name.length > 18 ? d.drama_name.slice(0, 18) + '…' : d.drama_name,
      ),
      axisLabel: { width: 160, overflow: 'truncate', fontSize: 12 },
    },
    series: Object.values(seriesMap),
  }
})

const platformSummaryOption = computed(() => {
  const items = platformSummary.value
  if (!items.length) return {}

  const names = items.map((d) => PLATFORM_NAMES[d.platform] || d.platform)
  const colors = items.map((d) => PLATFORM_COLORS[d.platform] || '#999')

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any) {
        if (!Array.isArray(params) || !params.length) return ''
        let html = `<b>${params[0].name}</b>`
        params.forEach((p: any) => {
          if (p.value != null) {
            html += `<br/>${p.marker} ${p.seriesName}: ${formatNum(p.value)}`
          }
        })
        return html
      },
    },
    legend: { top: 0 },
    grid: { left: 20, right: 20, top: 40, bottom: 10, containLabel: true },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: names.length > 5 ? 20 : 0 },
    },
    yAxis: [
      {
        type: 'value',
        name: '总播放量',
        axisLabel: { formatter: (v: number) => formatNum(v) },
      },
      {
        type: 'value',
        name: '平均播放量',
        axisLabel: { formatter: (v: number) => formatNum(v) },
      },
    ],
    series: [
      {
        name: '总播放量',
        type: 'bar',
        yAxisIndex: 0,
        data: items.map((d, i) => ({ value: d.total_play, itemStyle: { color: colors[i] } })),
        barMaxWidth: 40,
      },
      {
        name: '平均播放量',
        type: 'bar',
        yAxisIndex: 1,
        data: items.map((d) => d.avg_play),
        barMaxWidth: 40,
        itemStyle: { color: '#00BF8A', opacity: 0.6 },
      },
    ],
  }
})

watch([filterRankType, filterTimePeriod, filterTopN], () => loadData())
onMounted(() => loadData())
</script>

<template>
  <div class="compare-page" v-loading="loading">
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/' }">监控首页</el-breadcrumb-item>
      <el-breadcrumb-item>跨平台对比</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">榜单类型</span>
          <el-select v-model="filterRankType" style="width: 140px">
            <el-option label="近期热剧榜" value="hot" />
            <el-option label="新剧飙升榜" value="rising" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">时间周期</span>
          <el-select v-model="filterTimePeriod" style="width: 120px">
            <el-option label="今日" value="today" />
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">Top N</span>
          <el-select v-model="filterTopN" style="width: 100px">
            <el-option :label="10" :value="10" />
            <el-option :label="20" :value="20" />
            <el-option :label="30" :value="30" />
            <el-option :label="50" :value="50" />
          </el-select>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="chart-card">
      <template #header>
        <span class="chart-title">跨平台爆款总榜</span>
        <span class="chart-sub">各平台热剧按播放量统一排名</span>
      </template>
      <div v-if="crossRanking.length" class="chart-wrap" :style="{ height: Math.max(300, crossRanking.length * 32 + 60) + 'px' }">
        <v-chart :option="crossRankingOption" autoresize />
      </div>
      <el-empty v-else description="暂无播放量数据" />
    </el-card>

    <el-card shadow="never" class="chart-card">
      <template #header>
        <span class="chart-title">平台整体热度对比</span>
        <span class="chart-sub">各平台总播放量与平均播放量</span>
      </template>
      <div v-if="platformSummary.length" class="chart-wrap" style="height: 400px">
        <v-chart :option="platformSummaryOption" autoresize />
      </div>
      <el-empty v-else description="暂无播放量数据" />
    </el-card>
  </div>
</template>

<style scoped>
.compare-page {
  font-size: 13px;
}

.breadcrumb {
  margin-bottom: 16px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: var(--zw-text-secondary);
  white-space: nowrap;
}

.chart-card {
  margin-bottom: 16px;
}

.chart-card :deep(.el-card__header) {
  padding: 14px 20px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--zw-text);
}

.chart-sub {
  font-size: 12px;
  color: var(--zw-text-secondary);
}

.chart-wrap {
  width: 100%;
}
</style>
