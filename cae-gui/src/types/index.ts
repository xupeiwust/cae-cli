export interface Project {
  id: string
  name: string
  path: string
  status: 'idle' | 'solving' | 'done' | 'error'
  lastModified: string
}

export interface SolveTask {
  id: string
  projectName: string
  inputFile: string
  outputDir: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  startTime?: string
  endTime?: string
  log?: string[]
}

export interface DiagnosisIssue {
  id: string
  severity: 'error' | 'warning' | 'info'
  category: string
  message: string
  evidenceLine?: string
  evidenceScore?: number
  suggestion?: string
}

export interface DiagnosisResult {
  issues: DiagnosisIssue[]
  summary: string
  timestamp: string
}

export interface ViewerResult {
  name: string
  type: 'frd' | 'dat' | 'vtu'
  path: string
  size: number
}

export interface SidebarItem {
  key: string
  label: string
  icon: string
  route: string
}
