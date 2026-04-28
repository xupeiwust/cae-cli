<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref } from 'vue'

const activeSection = ref('general')

const settings = ref({
  solverPath: '',
  defaultSolver: 'calculix',
  aiModel: 'deepseek-r1:1.5b',
  language: 'zh-CN',
  autoCheckUpdates: true,
})

const sections = [
  { key: 'general', label: '通用', icon: 'carbon:settings-adjust' },
  { key: 'solver', label: '求解器', icon: 'carbon:machine-learning-model' },
  { key: 'ai', label: 'AI', icon: 'carbon:watson-health-ai-status' },
  { key: 'about', label: '关于', icon: 'carbon:information' },
]
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="text-[12px]" style="color: var(--md-on-surface-variant)">{{ sections.find(s => s.key === activeSection)?.label }}</div>
    </div>

    <div class="flex-1 grid grid-cols-5 gap-4 min-h-0">
      <div class="col-span-1 md-card p-2 flex flex-col gap-0.5">
        <button
          v-for="section in sections"
          :key="section.key"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-[14px] text-[14px] font-medium transition-all"
          :style="activeSection === section.key
            ? 'background: var(--md-secondary-container); color: var(--md-on-primary-container)'
            : 'color: var(--md-on-surface-variant)'"
          @click="activeSection = section.key"
        >
          <Icon :icon="section.icon" class="text-lg" />
          {{ section.label }}
        </button>
      </div>

      <div class="col-span-4 md-card p-5 flex flex-col">
        <div v-if="activeSection === 'general'" class="flex-1 flex flex-col gap-4">
          <div class="text-[16px] font-semibold" style="color: var(--md-on-surface)">通用设置</div>
          <div class="space-y-2">
            <div class="flex items-center justify-between p-4 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div>
                <div class="text-[14px] font-medium" style="color: var(--md-on-surface)">界面语言</div>
                <div class="text-[12px] mt-0.5" style="color: var(--md-on-surface-variant)">选择显示语言</div>
              </div>
              <select v-model="settings.language"
                class="rounded-[12px] px-4 py-2 text-[13px] outline-none cursor-pointer"
                style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)">
                <option value="zh-CN">简体中文</option>
                <option value="en">English</option>
              </select>
            </div>
            <div class="flex items-center justify-between p-4 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div>
                <div class="text-[14px] font-medium" style="color: var(--md-on-surface)">自动检查更新</div>
                <div class="text-[12px] mt-0.5" style="color: var(--md-on-surface-variant)">启动时自动检查新版本</div>
              </div>
              <div
                :class="settings.autoCheckUpdates ? 'md-switch-active' : 'md-switch'"
                @click="settings.autoCheckUpdates = !settings.autoCheckUpdates"
              >
                <div class="md-switch-thumb" />
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeSection === 'solver'" class="flex-1 flex flex-col gap-4">
          <div class="text-[16px] font-semibold" style="color: var(--md-on-surface)">求解器配置</div>
          <div class="space-y-2">
            <div class="p-4 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="text-[12px] mb-2 font-medium" style="color: var(--md-on-surface-variant)">求解器路径</div>
              <div class="flex gap-2">
                <input v-model="settings.solverPath" type="text" placeholder="自动检测"
                  class="flex-1 rounded-[12px] px-4 py-2.5 text-[13px] outline-none"
                  style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)"
                />
                <button class="md-btn-outlined" style="padding: 8px 12px; border-radius: 12px">
                  <Icon icon="carbon:folder-open" class="text-base" />
                </button>
              </div>
            </div>
            <div class="flex items-center justify-between p-4 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="text-[14px] font-medium" style="color: var(--md-on-surface)">默认求解器</div>
              <select v-model="settings.defaultSolver"
                class="rounded-[12px] px-4 py-2 text-[13px] outline-none cursor-pointer"
                style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)">
                <option value="calculix">CalculiX</option>
                <option value="docker-calculix">Docker CalculiX</option>
              </select>
            </div>
            <div class="flex items-center gap-3 p-4 rounded-[12px]" style="background: rgba(168,218,181,0.08)">
              <Icon icon="carbon:checkmark-filled" class="text-xl" style="color: var(--md-success)" />
              <div>
                <div class="text-[13px] font-medium" style="color: var(--md-success)">CalculiX 已安装</div>
                <div class="text-[11px] mt-0.5" style="color: var(--md-on-surface-variant)">ccx 2.21</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeSection === 'ai'" class="flex-1 flex flex-col gap-4">
          <div class="text-[16px] font-semibold" style="color: var(--md-on-surface)">AI 模型</div>
          <div class="space-y-2">
            <div class="flex items-center justify-between p-4 rounded-[12px]" style="background: var(--md-surface-container-high)">
              <div class="text-[14px] font-medium" style="color: var(--md-on-surface)">活跃模型</div>
              <select v-model="settings.aiModel"
                class="rounded-[12px] px-4 py-2 text-[13px] outline-none cursor-pointer"
                style="background: var(--md-surface-container-highest); color: var(--md-on-surface); border: 1px solid var(--md-outline-variant)">
                <option value="deepseek-r1:1.5b">deepseek-r1:1.5b</option>
              </select>
            </div>
            <div class="flex items-start gap-3 p-4 rounded-[12px]" style="background: rgba(232,196,124,0.08)">
              <Icon icon="carbon:warning-filled" class="text-xl mt-0.5" style="color: var(--md-warning)" />
              <div>
                <div class="text-[13px] font-medium" style="color: var(--md-warning)">AI 功能未安装</div>
                <div class="text-[11px] mt-0.5 font-mono" style="color: var(--md-on-surface-variant)">pip install "cae-cxx[ai]"</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeSection === 'about'" class="flex-1 flex flex-col gap-4">
          <div class="text-[16px] font-semibold" style="color: var(--md-on-surface)">关于</div>
          <div class="flex items-center gap-4 p-5 rounded-[16px]" style="background: var(--md-primary-container)">
            <div class="w-[56px] h-[56px] rounded-[16px] flex items-center justify-center" style="background: var(--md-primary)">
              <Icon icon="carbon:machine-learning-model" class="text-2xl" style="color: var(--md-on-primary)" />
            </div>
            <div>
              <div class="text-[18px] font-bold" style="color: var(--md-on-primary-container)">CAE 工具箱</div>
              <div class="text-[12px] mt-0.5" style="color: var(--md-on-primary-container); opacity: 0.7">v1.5.0 · MIT License</div>
              <div class="text-[11px] mt-1" style="color: var(--md-on-primary-container); opacity: 0.5">基于 cae-cxx 构建</div>
            </div>
          </div>
          <div class="grid grid-cols-4 gap-3">
            <div v-for="tech in [{ icon: 'carbon:logo-python', label: '后端', value: 'Python', color: 'var(--md-primary)' }, { icon: 'carbon:logo-vue', label: '前端', value: 'Vue3', color: 'var(--md-success)' }, { icon: 'carbon:chip', label: '框架', value: 'Tauri', color: 'var(--md-warning)' }, { icon: 'carbon:model', label: '求解器', value: 'CalculiX', color: 'var(--md-tertiary)' }]"
              :key="tech.label" class="p-4 rounded-[12px] text-center" style="background: var(--md-surface-container-high)">
              <Icon :icon="tech.icon" class="text-xl mx-auto mb-1.5" :style="`color: ${tech.color}`" />
              <div class="text-[11px]" style="color: var(--md-on-surface-variant)">{{ tech.label }}</div>
              <div class="text-[13px] font-medium mt-0.5" style="color: var(--md-on-surface)">{{ tech.value }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
