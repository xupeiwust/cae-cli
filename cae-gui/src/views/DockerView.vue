<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref } from 'vue'

const dockerAvailable = ref(true)
const wslDocker = ref(true)
const isChecking = ref(false)

const images = ref([
  { alias: 'calculix-parallelworks', solver: 'CalculiX', status: 'pulled', size: '1.2 GB' },
  { alias: 'code-aster', solver: 'Code_Aster', status: 'available', size: '2.8 GB' },
  { alias: 'openfoam-lite', solver: 'OpenFOAM', status: 'available', size: '850 MB' },
  { alias: 'elmer', solver: 'Elmer', status: 'available', size: '640 MB' },
])

const solvers = ['CalculiX', 'Code_Aster', 'OpenFOAM', 'Elmer', 'SU2']

function checkStatus() {
  isChecking.value = true
  setTimeout(() => { isChecking.value = false }, 1500)
}

function pullImage(alias: string) {
  const img = images.value.find((i) => i.alias === alias)
  if (img) img.status = 'pulling'
  setTimeout(() => { if (img) img.status = 'pulled' }, 3000)
}
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ dockerAvailable ? '运行中 · WSL2' : '未连接' }}</div>
      <button class="md-btn-outlined" @click="checkStatus">
        <Icon :icon="isChecking ? 'carbon:progress-bar' : 'carbon:renew'" :class="isChecking ? 'animate-pulse' : ''" class="text-base" />
        {{ isChecking ? '检查中...' : '刷新状态' }}
      </button>
    </div>

    <div class="flex-1 grid grid-cols-5 gap-4 min-h-0">
      <div class="col-span-2 md-card p-4 flex flex-col gap-3">
        <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">引擎状态</div>

        <div class="flex items-center justify-between p-4 rounded-[12px]"
          :style="dockerAvailable ? 'background: rgba(168,218,181,0.08)' : 'background: rgba(242,184,181,0.08)'">
          <div class="flex items-center gap-3">
            <Icon :icon="dockerAvailable ? 'carbon:checkmark-filled' : 'carbon:close-filled'" class="text-2xl"
              :style="dockerAvailable ? 'color: var(--md-success)' : 'color: var(--md-error)'" />
            <div>
              <div class="text-[14px] font-semibold" :style="dockerAvailable ? 'color: var(--md-success)' : 'color: var(--md-error)'">{{ dockerAvailable ? 'Docker 可用' : 'Docker 不可用' }}</div>
              <div class="text-[12px] mt-0.5" style="color: var(--md-on-surface-variant)">{{ wslDocker ? 'WSL2 Docker 后端' : '原生 Docker' }}</div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 rounded-[12px] text-center" style="background: var(--md-surface-container-high)">
            <div class="text-[11px]" style="color: var(--md-on-surface-variant)">引擎</div>
            <div class="text-[14px] font-semibold mt-0.5" style="color: var(--md-on-surface)">{{ wslDocker ? 'WSL2' : 'Native' }}</div>
          </div>
          <div class="p-3 rounded-[12px] text-center" style="background: var(--md-surface-container-high)">
            <div class="text-[11px]" style="color: var(--md-on-surface-variant)">版本</div>
            <div class="text-[14px] font-mono mt-0.5" style="color: var(--md-on-surface)">24.0.7</div>
          </div>
        </div>

        <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">快速操作</div>
        <div class="space-y-2 flex-1">
          <button v-for="op in [{ icon: 'carbon:catalog', label: '求解器目录' }, { icon: 'carbon:recommend', label: '推荐求解器' }, { icon: 'carbon:folder-open', label: '路径转换' }]" :key="op.label"
            class="w-full flex items-center gap-3 p-3 rounded-[12px] text-[13px] transition-all"
            style="background: var(--md-surface-container-high); color: var(--md-on-surface)">
            <Icon :icon="op.icon" class="text-lg" style="color: var(--md-primary)" />
            {{ op.label }}
          </button>
        </div>
      </div>

      <div class="col-span-3 md-card p-4 flex flex-col">
        <div class="flex items-center justify-between mb-3 flex-shrink-0">
          <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">镜像管理</div>
          <span class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ images.filter(i => i.status === 'pulled').length }}/{{ images.length }} 已拉取</span>
        </div>
        <div class="grid grid-cols-2 gap-3 flex-1 min-h-0">
          <div v-for="img in images" :key="img.alias" class="p-3 rounded-[12px] flex items-center justify-between transition-all" style="background: var(--md-surface-container-high)">
            <div class="flex items-center gap-3">
              <div class="w-2.5 h-2.5 rounded-full flex-shrink-0"
                :style="img.status === 'pulled' ? 'background: var(--md-success)' : img.status === 'pulling' ? 'background: var(--md-warning)' : 'background: var(--md-outline-variant)'" />
              <div>
                <div class="text-[13px] font-medium" style="color: var(--md-on-surface)">{{ img.alias }}</div>
                <div class="text-[11px] mt-0.5" style="color: var(--md-on-surface-variant)">{{ img.solver }} · {{ img.size }}</div>
              </div>
            </div>
            <button v-if="img.status !== 'pulling'"
              :class="img.status === 'pulled' ? 'md-chip-active' : 'md-chip'"
              style="padding: 4px 12px; font-size: 11px"
              @click="img.status !== 'pulled' && pullImage(img.alias)">
              {{ img.status === 'pulled' ? '已拉取' : '拉取' }}
            </button>
            <span v-else class="flex items-center gap-1 text-[11px]" style="color: var(--md-warning)">
              <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background: var(--md-warning)" />拉取中
            </span>
          </div>
        </div>

        <div class="mt-3 pt-3" style="border-top: 1px solid var(--md-outline-variant)">
          <div class="text-[14px] font-semibold mb-3" style="color: var(--md-on-surface)">可用求解器</div>
          <div class="flex gap-2 flex-wrap">
            <span v-for="solver in solvers" :key="solver" class="md-chip" style="padding: 4px 14px; font-size: 11px">
              {{ solver }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
