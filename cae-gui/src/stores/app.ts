import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Project, SolveTask, DiagnosisResult } from '@/types'

export const useAppStore = defineStore('app', () => {
  const projects = ref<Project[]>([
    {
      id: '1',
      name: '悬臂梁示例',
      path: 'examples/beam.inp',
      status: 'done',
      lastModified: '2026-04-26 10:30',
    },
    {
      id: '2',
      name: '热传导分析',
      path: 'examples/heat.inp',
      status: 'idle',
      lastModified: '2026-04-25 16:00',
    },
  ])

  const solveTasks = ref<SolveTask[]>([
    {
      id: '1',
      projectName: '悬臂梁示例',
      inputFile: 'examples/beam.inp',
      outputDir: 'output/beam',
      status: 'completed',
      progress: 100,
      startTime: '2026-04-26 10:30:00',
      endTime: '2026-04-26 10:32:15',
    },
  ])

  const diagnosisResult = ref<DiagnosisResult | null>(null)

  const activeProject = ref<Project | null>(projects.value[0] ?? null)

  const sidebarCollapsed = ref(false)

  const currentSolve = computed(() =>
    solveTasks.value.find((t) => t.status === 'running'),
  )

  const recentProjects = computed(() =>
    [...projects.value].sort(
      (a, b) =>
        new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime(),
    ),
  )

  function setActiveProject(project: Project) {
    activeProject.value = project
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function addProject(project: Project) {
    projects.value.push(project)
  }

  function addSolveTask(task: SolveTask) {
    solveTasks.value.push(task)
  }

  function updateSolveTask(id: string, updates: Partial<SolveTask>) {
    const task = solveTasks.value.find((t) => t.id === id)
    if (task) {
      Object.assign(task, updates)
    }
  }

  function setDiagnosisResult(result: DiagnosisResult) {
    diagnosisResult.value = result
  }

  return {
    projects,
    solveTasks,
    diagnosisResult,
    activeProject,
    sidebarCollapsed,
    currentSolve,
    recentProjects,
    setActiveProject,
    toggleSidebar,
    addProject,
    addSolveTask,
    updateSolveTask,
    setDiagnosisResult,
  }
})
