<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { Icon } from '@iconify/vue'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

const navItems = [
  { key: 'project', label: '项目', icon: 'carbon:folder', route: '/project' },
  { key: 'solve', label: '求解', icon: 'carbon:play-filled', route: '/solve' },
  { key: 'viewer', label: '结果', icon: 'carbon:chart-line-data', route: '/viewer' },
  { key: 'diagnose', label: '诊断', icon: 'carbon:stethoscope', route: '/diagnose' },
  { key: 'docker', label: 'Docker', icon: 'carbon:container-software', route: '/docker' },
  { key: 'settings', label: '设置', icon: 'carbon:settings', route: '/settings' },
]

const activeKey = computed(() => {
  const item = navItems.find((i) => route.path.startsWith(i.route))
  return item?.key ?? 'project'
})

function navigate(route: string) {
  router.push(route)
}
</script>

<template>
  <div class="flex h-full" style="background: var(--md-surface)">
    <aside class="w-[80px] flex flex-col items-center py-3 gap-1" style="background: var(--md-surface-container-low)">
      <div
        class="w-[48px] h-[48px] rounded-[16px] flex items-center justify-center mb-4 cursor-pointer"
        style="background: var(--md-primary-container)"
        @click="store.toggleSidebar()"
      >
        <Icon icon="carbon:machine-learning-model" class="text-xl" style="color: var(--md-on-primary-container)" />
      </div>

      <nav class="flex-1 flex flex-col items-center gap-1 w-full px-2">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="w-full flex flex-col items-center gap-0.5 py-2.5 rounded-[16px] transition-all duration-200"
          :style="activeKey === item.key
            ? 'background: var(--md-secondary-container); color: var(--md-on-primary-container)'
            : 'background: transparent; color: var(--md-on-surface-variant)'"
          @click="navigate(item.route)"
        >
          <Icon :icon="item.icon" class="text-[20px]" />
          <span class="text-[11px] font-medium">{{ item.label }}</span>
        </button>
      </nav>

      <div class="flex flex-col items-center gap-1 mt-2">
        <div
          class="w-2.5 h-2.5 rounded-full"
          :style="store.activeProject?.status === 'done'
            ? 'background: var(--md-success)'
            : store.activeProject?.status === 'solving'
            ? 'background: var(--md-warning)'
            : store.activeProject?.status === 'error'
            ? 'background: var(--md-error)'
            : 'background: var(--md-outline-variant)'"
        />
      </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden">
      <header
        class="h-[48px] flex items-center justify-between px-5 flex-shrink-0"
        style="background: var(--md-surface)"
        data-tauri-drag-region
      >
        <div class="text-[16px] font-semibold" style="color: var(--md-on-surface)" data-tauri-drag-region>
          {{ navItems.find((i) => i.key === activeKey)?.label }}
        </div>
        <div class="flex items-center gap-2">
          <span v-if="store.activeProject" class="text-[12px]" style="color: var(--md-on-surface-variant)">
            {{ store.activeProject.name }}
          </span>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto p-4">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>
