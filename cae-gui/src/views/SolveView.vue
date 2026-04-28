<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { Icon } from '@iconify/vue'
import { ref } from 'vue'

const store = useAppStore()
const selectedInput = ref('')
const outputDir = ref('')
const solverType = ref('calculix')
const isRunning = ref(false)
const runLog = ref<string[]>([])
const progress = ref(0)

const solvers = [
  { id: 'calculix', name: 'CalculiX', desc: '结构/热力学 FEM' },
  { id: 'docker-calculix', name: 'Docker', desc: '容器化求解' },
]

const recentLogs = [
  { project: '悬臂梁示例', status: 'completed', time: '10:30', duration: '2m 15s' },
  { project: '热传导分析', status: 'failed', time: '09:15', duration: '0m 45s' },
]

function startSolve() {
  if (!selectedInput.value) return
  isRunning.value = true
  runLog.value = []
  progress.value = 0

  const mockLogs = [
    '> cae solve ' + selectedInput.value,
    'CalculiX ccx 2.21',
    '读取输入文件...',
    '模型: 1245 节点, 960 单元',
    '组装刚度矩阵...  100%',
    '求解线性方程组...',
    '  迭代 1: 残差 = 3.24e-02',
    '  迭代 2: 残差 = 4.51e-04',
    '  迭代 3: 残差 = 2.18e-06',
    '  迭代 4: 残差 = 8.77e-09',
    '✓ 收敛! 4 次迭代',
    '写入结果文件...',
    '✓ 完成!',
  ]

  let i = 0
  const interval = setInterval(() => {
    if (i < mockLogs.length) {
      runLog.value.push(mockLogs[i])
      progress.value = Math.round(((i + 1) / mockLogs.length) * 100)
      i++
    } else {
      isRunning.value = false
      clearInterval(interval)
    }
  }, 250)
}

function stopSolve() {
  isRunning.value = false
  runLog.value.push('> 求解已手动中断')
}
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">运行有限元仿真</div>
      <div class="flex items-center gap-3">
        <div v-if="isRunning" class="flex items-center gap-1.5 text-[12px]" style="color: var(--md-warning)">
          <span class="w-2 h-2 rounded-full animate-pulse" style="background: var(--md-warning)" />
          运行中
        </div>
        <button
          :disabled="!selectedInput || isRunning"
          class="md-btn-filled"
          :style="isRunning ? 'background: var(--md-error-container); color: var(--md-error)' : !selectedInput ? 'background: var(--md-surface-container-highest); color: var(--md-outline); cursor: not-allowed' : ''"
          @click="isRunning ? stopSolve() : startSolve()"
        >
          <Icon :icon="isRunning ? 'carbon:stop-filled' : 'carbon:play-filled'" class="text-base" />
          {{ isRunning ? '中断' : '开始求解' }}
        </button>
      </div>
    </div>

    <div class="flex-1 grid grid-cols-5 gap-4 min-h-0">
      <div class="col-span-2 md-card p-4 flex flex-col gap-3">
        <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">配置</div>

        <div class="space-y-3 flex-1">
          <div>
            <div class="text-[12px] mb-1.5 font-medium" style="color: var(--md-on-surface-variant)">输入文件</div>
            <div class="flex gap-2">
              <input v-model="selectedInput" type="text" placeholder="examples/beam.inp"
                class="flex-1 rounded-[12px] px-4 py-2.5 text-[13px] outline-none transition-all"
                style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)"
              />
              <button class="md-btn-outlined" style="padding: 8px 12px; border-radius: 12px">
                <Icon icon="carbon:folder-open" class="text-base" />
              </button>
            </div>
          </div>

          <div>
            <div class="text-[12px] mb-1.5 font-medium" style="color: var(--md-on-surface-variant)">输出目录</div>
            <input v-model="outputDir" type="text" placeholder="output/beam"
              class="w-full rounded-[12px] px-4 py-2.5 text-[13px] outline-none transition-all"
              style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)"
            />
          </div>

          <div>
            <div class="text-[12px] mb-2 font-medium" style="color: var(--md-on-surface-variant)">求解器</div>
            <div class="space-y-2">
              <label
                v-for="solver in solvers"
                :key="solver.id"
                class="flex items-center gap-3 p-3 rounded-[12px] cursor-pointer transition-all"
                :style="solverType === solver.id
                  ? 'background: var(--md-secondary-container); color: var(--md-on-primary-container)'
                  : 'background: var(--md-surface-container-highest); color: var(--md-on-surface-variant)'"
              >
                <input v-model="solverType" type="radio" :value="solver.id" class="hidden" />
                <div
                  class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
                  :style="solverType === solver.id ? 'border-color: var(--md-primary)' : 'border-color: var(--md-outline)'"
                >
                  <div v-if="solverType === solver.id" class="w-2.5 h-2.5 rounded-full" style="background: var(--md-primary)" />
                </div>
                <div>
                  <div class="text-[13px] font-medium">{{ solver.name }}</div>
                  <div class="text-[11px] mt-0.5" style="color: var(--md-on-surface-variant)">{{ solver.desc }}</div>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="col-span-3 md-card p-4 flex flex-col">
        <div class="flex items-center justify-between mb-3 flex-shrink-0">
          <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">运行日志</div>
          <div class="flex items-center gap-4 text-[12px]" style="color: var(--md-on-surface-variant)">
            <span>迭代 <span class="font-semibold" style="color: var(--md-primary)">4</span>/10</span>
            <span>残差 <span class="font-mono" style="color: var(--md-primary)">8.77e-09</span></span>
          </div>
        </div>

        <div v-if="progress > 0" class="mb-3 flex-shrink-0">
          <div class="flex justify-between text-[12px] mb-1.5">
            <span style="color: var(--md-on-surface-variant)">{{ progress }}%</span>
            <span :style="isRunning ? 'color: var(--md-warning)' : 'color: var(--md-success)'">{{ isRunning ? '求解中' : '完成' }}</span>
          </div>
          <div class="h-1 rounded-full overflow-hidden" style="background: var(--md-surface-container-highest)">
            <div
              class="h-full rounded-full transition-all duration-300"
              :style="{ width: progress + '%', background: isRunning ? 'var(--md-primary)' : 'var(--md-success)' }"
            />
          </div>
        </div>

        <div class="flex-1 rounded-[12px] p-3 font-mono text-[12px] overflow-y-auto min-h-0" style="background: var(--md-surface-container-lowest)">
          <div v-if="runLog.length === 0" class="h-full flex items-center justify-center" style="color: var(--md-outline)">
            等待开始求解...
          </div>
          <div v-for="(line, i) in runLog" :key="i" :class="['leading-relaxed',
            line.startsWith('>') ? '' :
            line.includes('✓') ? '' :
            line.includes('残差') ? '' : ''
          ]" :style="line.startsWith('>') ? 'color: var(--md-primary)' : line.includes('✓') ? 'color: var(--md-success)' : line.includes('残差') ? 'color: var(--md-primary)' : 'color: var(--md-on-surface-variant)'">
            {{ line }}
          </div>
          <span v-if="isRunning" class="inline-block w-1.5 h-3.5 animate-pulse" style="background: var(--md-primary)" />
        </div>
      </div>
    </div>

    <div class="flex-shrink-0 md-card p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">求解历史</div>
        <span class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ store.solveTasks.length }} 条记录</span>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <div v-for="log in recentLogs" :key="log.project" class="p-3 rounded-[12px]" style="background: var(--md-surface-container-high)">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full" :style="log.status === 'completed' ? 'background: var(--md-success)' : 'background: var(--md-error)'" />
              <span class="text-[13px] font-medium" style="color: var(--md-on-surface)">{{ log.project }}</span>
            </div>
            <span class="text-[11px]" style="color: var(--md-on-surface-variant)">{{ log.time }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[11px] px-2 py-0.5 rounded-full font-medium"
              :style="log.status === 'completed' ? 'background: rgba(168,218,181,0.15); color: var(--md-success)' : 'background: rgba(242,184,181,0.15); color: var(--md-error)'">
              {{ log.status === 'completed' ? '完成' : '失败' }}
            </span>
            <span class="text-[11px]" style="color: var(--md-on-surface-variant)">{{ log.duration }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
