<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, GridComponent])

const activeTab = ref('contour')

const mdSurface = '#1D1B20'
const mdOnSurfaceVariant = '#CAC4D0'
const mdPrimary = '#D0BCFF'
const mdOutline = '#938F99'

const stressOption = {
  backgroundColor: 'transparent',
  grid: { top: 20, right: 16, bottom: 28, left: 50 },
  xAxis: { type: 'category', data: ['1', '5', '10', '15', '20', '25', '30'], axisLine: { lineStyle: { color: '#49454F' } }, axisLabel: { color: mdOnSurfaceVariant, fontSize: 10 } },
  yAxis: { type: 'value', name: 'MPa', nameTextStyle: { color: mdOnSurfaceVariant, fontSize: 10 }, axisLine: { lineStyle: { color: '#49454F' } }, axisLabel: { color: mdOnSurfaceVariant, fontSize: 10 }, splitLine: { lineStyle: { color: '#49454F' } } },
  tooltip: { trigger: 'axis', backgroundColor: '#2B2930', borderColor: '#49454F', textStyle: { color: '#E6E0E9', fontSize: 11 } },
  series: [
    { name: 'Von Mises', type: 'line', smooth: true, data: [0, 45, 90, 134, 179, 201, 210], lineStyle: { color: mdPrimary, width: 2 }, itemStyle: { color: mdPrimary }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(208,188,255,0.25)' }, { offset: 1, color: 'rgba(208,188,255,0)' }] } } },
    { name: '位移', type: 'line', smooth: true, data: [0, 0.12, 0.28, 0.45, 0.68, 0.89, 1.02], lineStyle: { color: '#EFB8C8', width: 2 }, itemStyle: { color: '#EFB8C8' } },
  ],
}

const convergenceOption = {
  backgroundColor: 'transparent',
  grid: { top: 20, right: 16, bottom: 28, left: 55 },
  xAxis: { type: 'category', data: ['1', '2', '3', '4', '5', '6', '7', '8'], axisLine: { lineStyle: { color: '#49454F' } }, axisLabel: { color: mdOnSurfaceVariant, fontSize: 10 }, name: '迭代', nameTextStyle: { color: mdOnSurfaceVariant, fontSize: 10 } },
  yAxis: { type: 'log', name: '残差', nameTextStyle: { color: mdOnSurfaceVariant, fontSize: 10 }, axisLine: { lineStyle: { color: '#49454F' } }, axisLabel: { color: mdOnSurfaceVariant, fontSize: 10 }, splitLine: { lineStyle: { color: '#49454F' } } },
  tooltip: { trigger: 'axis', backgroundColor: '#2B2930', borderColor: '#49454F', textStyle: { color: '#E6E0E9', fontSize: 11 } },
  series: [
    { name: '力残差', type: 'line', data: [3.2e-2, 4.5e-4, 2.2e-6, 8.8e-9, 3.1e-11, 1.2e-13, 5e-15, 5e-15], lineStyle: { color: '#E8C47C', width: 2 }, itemStyle: { color: '#E8C47C' } },
    { name: '位移残差', type: 'line', data: [1.1e-1, 2.3e-3, 8.7e-5, 1.4e-7, 6.2e-10, 2.8e-12, 1e-14, 1e-14], lineStyle: { color: '#A8DAB5', width: 2 }, itemStyle: { color: '#A8DAB5' } },
  ],
}

const resultFiles = [
  { name: 'beam.frd', type: 'FRD', size: '2.4 MB', icon: 'carbon:document-blank', color: 'success' },
  { name: 'beam.dat', type: 'DAT', size: '156 KB', icon: 'carbon:document', color: 'warning' },
  { name: 'beam.vtu', type: 'VTU', size: '3.1 MB', icon: 'carbon:chart-3d', color: 'primary' },
]

const stats = [
  { label: '最大位移', value: '1.02', unit: 'mm', node: '节点 30' },
  { label: '最大应力', value: '210', unit: 'MPa', node: '节点 25' },
  { label: '最小位移', value: '0', unit: 'mm', node: '节点 1' },
  { label: '收敛迭代', value: '4', unit: '次', node: '残差 8.77e-09' },
]
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">beam.inp · 悬臂梁示例</div>
      <div class="flex items-center gap-1">
        <button
          v-for="tab in [{ key: 'contour', label: '曲线' }, { key: 'convergence', label: '收敛' }, { key: 'files', label: '文件' }]"
          :key="tab.key"
          :class="activeTab === tab.key ? 'md-chip-active' : 'md-chip'"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="flex-1 grid grid-cols-5 gap-4 min-h-0">
      <div class="col-span-3 md-card p-4 flex flex-col">
        <div class="flex items-center justify-between mb-3 flex-shrink-0">
          <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">{{ activeTab === 'contour' ? '应力 / 位移曲线' : '收敛曲线' }}</div>
          <div class="flex items-center gap-4 text-[12px]" style="color: var(--md-on-surface-variant)">
            <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 rounded" style="background: var(--md-primary)"></span>Von Mises</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 rounded" style="background: var(--md-tertiary)"></span>位移</span>
          </div>
        </div>
        <div class="flex-1 min-h-0">
          <v-chart :option="activeTab === 'contour' ? stressOption : convergenceOption" autoresize style="height: 100%" />
        </div>
      </div>

      <div class="col-span-2 flex flex-col gap-4">
        <div class="md-card p-4 flex-1">
          <div class="text-[14px] font-semibold mb-3" style="color: var(--md-on-surface)">关键指标</div>
          <div class="grid grid-cols-2 gap-3 flex-1">
            <div v-for="stat in stats" :key="stat.label" class="p-3 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="text-[11px]" style="color: var(--md-on-surface-variant)">{{ stat.label }}</div>
              <div class="flex items-baseline gap-1 mt-1.5">
                <span class="text-[20px] font-bold" style="color: var(--md-primary)">{{ stat.value }}</span>
                <span class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ stat.unit }}</span>
              </div>
              <div class="text-[11px] mt-1" style="color: var(--md-outline)">{{ stat.node }}</div>
            </div>
          </div>
        </div>

        <div class="md-card p-4">
          <div class="text-[14px] font-semibold mb-3" style="color: var(--md-on-surface)">结果文件</div>
          <div class="space-y-2">
            <div v-for="file in resultFiles" :key="file.name" class="flex items-center justify-between p-3 rounded-[12px] cursor-pointer transition-all" style="background: var(--md-surface-container-high)">
              <div class="flex items-center gap-3">
                <div class="w-[36px] h-[36px] rounded-[10px] flex items-center justify-center" style="background: var(--md-secondary-container)">
                  <Icon :icon="file.icon" class="text-base" style="color: var(--md-on-primary-container)" />
                </div>
                <div>
                  <div class="text-[13px] font-medium" style="color: var(--md-on-surface)">{{ file.name }}</div>
                  <div class="text-[11px]" style="color: var(--md-on-surface-variant)">{{ file.type }} · {{ file.size }}</div>
                </div>
              </div>
              <Icon icon="carbon:download" class="text-lg" style="color: var(--md-outline)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
