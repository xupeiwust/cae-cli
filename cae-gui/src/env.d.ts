/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module '@kitware/vtk.js/*' {
  const mod: any
  export default mod
}

interface Window {
  __TAURI_INTERNALS__: unknown
}
