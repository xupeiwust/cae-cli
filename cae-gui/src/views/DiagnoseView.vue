<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref, computed } from 'vue'
import type { DiagnosisIssue } from '@/types'

const isRunning = ref(false)

const issues = ref<DiagnosisIssue[]>([
  { id: '1', severity: 'error', category: '收敛', message: '求解未收敛：增量步缩减至最小步长仍不收敛', evidenceLine: 'beam.inp:45: *STATIC', evidenceScore: 0.95, suggestion: '减小初始增量步长或启用自动增量控制' },
  { id: '2', severity: 'warning', category: '材料', message: '材料参数可能不合理：弹性模量与泊松比组合异常', evidenceLine: 'beam.inp:12: *ELASTIC', evidenceScore: 0.72, suggestion: '检查材料参数是否正确' },
  { id: '3', severity: 'info', category: '网格', message: '网格长宽比偏大：部分单元超过 10:1', evidenceLine: 'beam.inp:8: *ELEMENT', evidenceScore: 0.58, suggestion: '建议对高长宽比区域细化网格' },
])

const filterSeverity = ref<string>('all')

const filteredIssues = computed(() => filterSeverity.value === 'all' ? issues.value : issues.value.filter((i) => i.severity === filterSeverity.value))
const severityCount = computed(() => ({ error: issues.value.filter((i) => i.severity === 'error').length, warning: issues.value.filter((i) => i.severity === 'warning').length, info: issues.value.filter((i) => i.severity === 'info').length }))

function runDiagnose() {
  isRunning.value = true
  setTimeout(() => { isRunning.value = false }, 2000)
}

const severityColors: Record<string, { bg: string; text: string; icon: string }> = {
  error: { bg: 'rgba(242,184,181,0.12)', text: 'var(--md-error)', icon: 'carbon:error-filled' },
  warning: { bg: 'rgba(232,196,124,0.12)', text: 'var(--md-warning)', icon: 'carbon:warning-filled' },
  info: { bg: 'rgba(208,188,255,0.12)', text: 'var(--md-primary)', icon: 'carbon:information-filled' },
}
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ issues.length }} 个问题 · beam.inp</div>
      <div class="flex items-center gap-3">
        <div class="flex gap-1">
          <button
            v-for="f in [{ key: 'all', label: '全部' }, { key: 'error', label: '错误' }, { key: 'warning', label: '警告' }, { key: 'info', label: '建议' }]"
            :key="f.key"
            :class="filterSeverity === f.key ? 'md-chip-active' : 'md-chip'"
            @click="filterSeverity = f.key"
          >
            {{ f.label }}
          </button>
        </div>
        <button
          :class="isRunning ? 'md-btn-outlined' : 'md-btn-filled'"
          :disabled="isRunning"
          @click="runDiagnose"
          :style="isRunning ? 'opacity: 0.6; cursor: not-allowed' : ''"
        >
          <Icon :icon="isRunning ? 'carbon:progress-bar' : 'carbon:stethoscope'" :class="isRunning ? 'animate-pulse' : ''" class="text-base" />
          {{ isRunning ? '诊断中...' : '开始诊断' }}
        </button>
      </div>
    </div>

    <div class="flex-1 grid grid-cols-5 gap-4 min-h-0">
      <div class="col-span-3 md-card p-4 flex flex-col min-h-0">
        <div class="flex items-center justify-between mb-3 flex-shrink-0">
          <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">诊断详情</div>
          <span class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ filteredIssues.length }} 条</span>
        </div>
        <div class="flex-1 space-y-3 overflow-y-auto min-h-0">
          <div v-for="issue in filteredIssues" :key="issue.id" class="p-3 rounded-[12px]" :style="`background: ${severityColors[issue.severity].bg}`">
            <div class="flex items-start gap-3">
              <div class="w-[36px] h-[36px] rounded-[10px] flex items-center justify-center flex-shrink-0" :style="`background: ${severityColors[issue.severity].bg}`">
                <Icon :icon="severityColors[issue.severity].icon" class="text-lg" :style="`color: ${severityColors[issue.severity].text}`" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-[11px] px-2 py-0.5 rounded-full font-medium" :style="`background: ${severityColors[issue.severity].bg}; color: ${severityColors[issue.severity].text}`">{{ issue.category }}</span>
                  <span class="text-[11px]" style="color: var(--md-outline)">置信度 {{ (issue.evidenceScore! * 100).toFixed(0) }}%</span>
                </div>
                <div class="text-[13px] leading-relaxed" style="color: var(--md-on-surface)">{{ issue.message }}</div>
                <div v-if="issue.evidenceLine" class="mt-2 rounded-[8px] px-3 py-1.5 font-mono text-[11px]" style="background: var(--md-surface-container-lowest); color: var(--md-on-surface-variant)">{{ issue.evidenceLine }}</div>
                <div v-if="issue.suggestion" class="mt-2 flex items-start gap-1.5 text-[12px]" style="color: var(--md-on-surface-variant)">
                  <Icon icon="carbon:lightbulb" class="text-sm mt-0.5 flex-shrink-0" style="color: var(--md-warning)" />
                  {{ issue.suggestion }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-span-2 flex flex-col gap-4">
        <div class="md-card p-4 flex-1">
          <div class="text-[14px] font-semibold mb-3" style="color: var(--md-on-surface)">问题统计</div>
          <div class="space-y-3">
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: rgba(242,184,181,0.08)">
              <div class="flex items-center gap-2.5">
                <Icon icon="carbon:error-filled" class="text-xl" style="color: var(--md-error)" />
                <span class="text-[13px] font-medium" style="color: var(--md-on-surface)">错误</span>
              </div>
              <span class="text-[24px] font-bold" style="color: var(--md-error)">{{ severityCount.error }}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: rgba(232,196,124,0.08)">
              <div class="flex items-center gap-2.5">
                <Icon icon="carbon:warning-filled" class="text-xl" style="color: var(--md-warning)" />
                <span class="text-[13px] font-medium" style="color: var(--md-on-surface)">警告</span>
              </div>
              <span class="text-[24px] font-bold" style="color: var(--md-warning)">{{ severityCount.warning }}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: rgba(208,188,255,0.08)">
              <div class="flex items-center gap-2.5">
                <Icon icon="carbon:information-filled" class="text-xl" style="color: var(--md-primary)" />
                <span class="text-[13px] font-medium" style="color: var(--md-on-surface)">建议</span>
              </div>
              <span class="text-[24px] font-bold" style="color: var(--md-primary)">{{ severityCount.info }}</span>
            </div>
          </div>
        </div>

        <div class="md-card p-4">
          <div class="text-[14px] font-semibold mb-3" style="color: var(--md-on-surface)">诊断级别</div>
          <div class="space-y-2">
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-[8px] flex items-center justify-center" style="background: rgba(168,218,181,0.15)">
                  <span class="text-[10px] font-bold" style="color: var(--md-success)">L1</span>
                </div>
                <span class="text-[13px]" style="color: var(--md-on-surface)">规则检测</span>
              </div>
              <span class="text-[12px] font-mono" style="color: var(--md-success)">527 规则</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-[8px] flex items-center justify-center" style="background: rgba(208,188,255,0.15)">
                  <span class="text-[10px] font-bold" style="color: var(--md-primary)">L2</span>
                </div>
                <span class="text-[13px]" style="color: var(--md-on-surface)">参考案例</span>
              </div>
              <span class="text-[12px] font-mono" style="color: var(--md-primary)">638 案例</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-[8px] flex items-center justify-center" style="background: rgba(232,196,124,0.15)">
                  <span class="text-[10px] font-bold" style="color: var(--md-warning)">L3</span>
                </div>
                <span class="text-[13px]" style="color: var(--md-on-surface)">AI 深度分析</span>
              </div>
              <span class="text-[12px]" style="color: var(--md-warning)">可选</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
