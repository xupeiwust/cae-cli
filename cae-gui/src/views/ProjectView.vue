<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import type { Project } from '@/types'
import VtkViewer from '@/components/VtkViewer.vue'

const store = useAppStore()
const router = useRouter()

function openProject(project: Project) {
  store.setActiveProject(project)
}

const projectStats = {
  '1': { nodes: 1245, elements: 960, lastTime: '2m 15s', status: 'done' as const, issues: 0 },
  '2': { nodes: 3200, elements: 2100, lastTime: '--', status: 'idle' as const, issues: 2 },
}

function goToSolve() {
  router.push('/solve')
}
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">
        {{ store.recentProjects.length }} 个仿真项目
      </div>
      <button class="md-btn-filled" @click="goToSolve()">
        <Icon icon="carbon:add" class="text-base" />
        新建项目
      </button>
    </div>

    <div class="flex-1 grid grid-cols-2 gap-4 min-h-0">
      <div
        v-for="project in store.recentProjects"
        :key="project.id"
        class="md-card p-4 flex flex-col cursor-pointer transition-all"
        :style="store.activeProject?.id === project.id ? 'outline: 2px solid var(--md-primary); outline-offset: -2px' : ''"
        @click="openProject(project)"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-3">
            <div
              class="w-[40px] h-[40px] rounded-[12px] flex items-center justify-center"
              :style="(projectStats as any)[project.id]?.status === 'done'
                ? 'background: var(--md-primary-container); color: var(--md-on-primary-container)'
                : 'background: var(--md-surface-container-highest); color: var(--md-on-surface-variant)'"
            >
              <Icon :icon="(projectStats as any)[project.id]?.status === 'done' ? 'carbon:checkmark-filled' : 'carbon:folder'" class="text-lg" />
            </div>
            <div>
              <div class="text-[14px] font-semibold" style="color: var(--md-on-surface)">{{ project.name }}</div>
              <div class="text-[12px] mt-0.5" style="color: var(--md-on-surface-variant)">{{ project.path }}</div>
            </div>
          </div>
          <span
            class="text-[11px] px-3 py-1 rounded-full font-medium"
            :style="(projectStats as any)[project.id]?.status === 'done'
              ? 'background: rgba(168, 218, 181, 0.15); color: var(--md-success)'
              : 'background: var(--md-surface-container-highest); color: var(--md-on-surface-variant)'"
          >
            {{ (projectStats as any)[project.id]?.status === 'done' ? '完成' : '空闲' }}
          </span>
        </div>

        <div class="flex-1 min-h-0 rounded-[12px] overflow-hidden">
          <VtkViewer class="w-full h-full" />
        </div>

        <div class="flex items-center justify-between mt-3 pt-3" style="border-top: 1px solid var(--md-outline-variant)">
          <div class="flex items-center gap-3">
            <span class="text-[12px]" style="color: var(--md-on-surface-variant)">
              <span class="font-semibold" style="color: var(--md-on-surface)">{{ projectStats[project.id as keyof typeof projectStats]?.nodes?.toLocaleString() || '-' }}</span> 节点
            </span>
            <span class="text-[12px]" style="color: var(--md-on-surface-variant)">
              <span class="font-semibold" style="color: var(--md-on-surface)">{{ projectStats[project.id as keyof typeof projectStats]?.elements?.toLocaleString() || '-' }}</span> 单元
            </span>
            <span class="text-[12px]" style="color: var(--md-on-surface-variant)">
              <span class="font-semibold" style="color: var(--md-primary)">{{ projectStats[project.id as keyof typeof projectStats]?.lastTime || '--' }}</span>
            </span>
          </div>
          <button class="md-btn-tonal" style="padding: 6px 16px; font-size: 12px; border-radius: 16px" @click.stop="router.push('/solve')">
            打开
          </button>
        </div>
      </div>

      <div
        class="md-card flex items-center justify-center cursor-pointer transition-all"
        style="border: 2px dashed var(--md-outline-variant)"
        @click="goToSolve()"
      >
        <div class="text-center">
          <div
            class="w-[56px] h-[56px] rounded-[16px] flex items-center justify-center mx-auto mb-3"
            style="background: var(--md-surface-container-highest)"
          >
            <Icon icon="carbon:add-alt" class="text-2xl" style="color: var(--md-on-surface-variant)" />
          </div>
          <div class="text-[14px] font-medium" style="color: var(--md-on-surface-variant)">新建或打开 INP 文件</div>
          <div class="text-[12px] mt-1" style="color: var(--md-outline)">支持 .inp 格式</div>
        </div>
      </div>
    </div>
  </div>
</template>
