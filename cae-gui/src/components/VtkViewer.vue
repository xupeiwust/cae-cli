<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { Icon } from '@iconify/vue'

import vtkGenericRenderWindow from '@kitware/vtk.js/Rendering/Misc/GenericRenderWindow'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'
import vtkRenderWindow from '@kitware/vtk.js/Rendering/Core/RenderWindow'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource'
import vtkCubeSource from '@kitware/vtk.js/Filters/Sources/CubeSource'
import vtkAxesActor from '@kitware/vtk.js/Rendering/Core/AxesActor'
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget'

interface Props {
  polydata?: { points: number[][]; cells: number[][] }
}

const props = defineProps<Props>()

const containerRef = ref<HTMLDivElement | null>(null)
const isLoading = ref(true)
const errorMsg = ref<string | null>(null)

let fullScreenRenderer: any = null
let renderer: any = null
let renderWindow: any = null
let orientationWidget: any = null

function initVtk() {
  if (!containerRef.value) return

  try {
    isLoading.value = true

    fullScreenRenderer = vtkGenericRenderWindow.newInstance({
      background: [0.08, 0.08, 0.1, 1],
    })
    fullScreenRenderer.setContainer(containerRef.value)

    renderWindow = fullScreenRenderer.getRenderWindow()
    renderer = fullScreenRenderer.getRenderer()

    renderer.setBackground(0.08, 0.08, 0.1)

    if (props.polydata) {
      loadPolyData(props.polydata)
    } else {
      loadDemoMesh()
    }

    const axes = vtkAxesActor.newInstance()
    orientationWidget = vtkOrientationMarkerWidget.newInstance({
      interactor: renderWindow.getInteractor(),
    })
    orientationWidget.setEnabled(true)
    orientationWidget.setViewportCorner(
      vtkOrientationMarkerWidget.Corners.BOTTOM_LEFT,
    )
    orientationWidget.setViewportSize(0.15)
    orientationWidget.setMinPixelSize(60)
    orientationWidget.setMaxPixelSize(120)
    orientationWidget.setActor(axes)

    renderer.resetCamera()
    renderWindow.render()

    isLoading.value = false
  } catch (e) {
    isLoading.value = false
    errorMsg.value = e instanceof Error ? e.message : '3D init failed'
  }
}

function loadDemoMesh() {
  const cube = vtkCubeSource.newInstance({
    xLength: 2.0,
    yLength: 1.4,
    zLength: 0.8,
  })

  const surfaceActor = vtkActor.newInstance()
  const surfaceMapper = vtkMapper.newInstance()
  surfaceMapper.setInputConnection(cube.getOutputPort())
  surfaceActor.setMapper(surfaceMapper)
  surfaceActor.getProperty().setColor(0.35, 0.65, 0.95)
  surfaceActor.getProperty().setOpacity(0.88)
  surfaceActor.getProperty().setEdgeColor(0.3, 0.5, 0.7)
  surfaceActor.getProperty().setLineWidth(0.8)
  surfaceActor.getProperty().setRepresentationToSurface()
  renderer.addActor(surfaceActor)

  const sphere = vtkSphereSource.newInstance({
    radius: 0.5,
    phiResolution: 20,
    thetaResolution: 20,
    center: [1.2, 0.2, 0],
  })

  const sphereActor = vtkActor.newInstance()
  const sphereMapper = vtkMapper.newInstance()
  sphereMapper.setInputConnection(sphere.getOutputPort())
  sphereActor.setMapper(sphereMapper)
  sphereActor.getProperty().setColor(0.95, 0.55, 0.3)
  sphereActor.getProperty().setOpacity(0.9)
  sphereActor.getProperty().setEdgeColor(0.7, 0.4, 0.25)
  sphereActor.getProperty().setLineWidth(0.5)
  renderer.addActor(sphereActor)

  const wireframeActor = vtkActor.newInstance()
  const wireframeMapper = vtkMapper.newInstance()
  wireframeMapper.setInputConnection(cube.getOutputPort())
  wireframeActor.setMapper(wireframeMapper)
  wireframeActor.getProperty().setRepresentationToWireframe()
  wireframeActor.getProperty().setColor(0.25, 0.45, 0.65)
  wireframeActor.getProperty().setLineWidth(0.6)
  wireframeActor.getProperty().setOpacity(0.5)
  renderer.addActor(wireframeActor)
}

function loadPolyData(data: { points: number[][]; cells: number[][] }) {
  const actor = vtkActor.newInstance()
  const mapper = vtkMapper.newInstance()
  actor.setMapper(mapper)
  actor.getProperty().setEdgeColor(0.4, 0.4, 0.5)
  actor.getProperty().setLineWidth(0.5)
  actor.getProperty().setOpacity(0.95)
  renderer.addActor(actor)
}

function resetCamera() {
  if (renderer) {
    renderer.resetCamera()
    renderWindow.render()
  }
}

function zoomIn() {
  if (renderer) {
    const cam = renderer.getActiveCamera()
    cam.zoom(1.3)
    renderWindow.render()
  }
}

function zoomOut() {
  if (renderer) {
    const cam = renderer.getActiveCamera()
    cam.zoom(0.7)
    renderWindow.render()
  }
}

onMounted(() => {
  initVtk()
})

onBeforeUnmount(() => {
  if (orientationWidget) {
    orientationWidget.setEnabled(false)
    orientationWidget.delete()
  }
  if (fullScreenRenderer) {
    fullScreenRenderer.delete()
  }
})
</script>

<template>
  <div class="relative w-full h-full rounded-lg overflow-hidden group">
    <div
      class="absolute inset-0 z-0"
      style="background: radial-gradient(ellipse at center, #1e1e2a 0%, #111116 70%, #0a0a0e 100%)"
    />

    <div ref="containerRef" class="relative z-10 w-full h-full" />

    <div
      class="absolute top-2 right-2 z-20 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
    >
      <button
        class="vtk-ctrl-btn"
        title="Zoom In"
        @click="zoomIn"
      >
        <Icon icon="carbon:zoom-in" class="text-xs" />
      </button>
      <button
        class="vtk-ctrl-btn"
        title="Zoom Out"
        @click="zoomOut"
      >
        <Icon icon="carbon:zoom-out" class="text-xs" />
      </button>
      <button
        class="vtk-ctrl-btn"
        title="Reset View"
        @click="resetCamera"
      >
        <Icon icon="carbon:restore" class="text-xs" />
      </button>
    </div>

    <div
      v-if="!isLoading && !errorMsg"
      class="absolute bottom-2 left-2 z-20 flex items-center gap-1.5 text-[9px] text-white/20 pointer-events-none"
    >
      <Icon icon="carbon:3d-mpr-toggle" class="text-[10px]" />
      <span>3D</span>
    </div>

    <div
      v-if="isLoading"
      class="absolute inset-0 z-30 flex flex-col items-center justify-center"
      style="background: radial-gradient(ellipse at center, #1e1e2a 0%, #111116 70%, #0a0a0e 100%)"
    >
      <div class="vtk-loader mb-3" />
      <div class="text-white/40 text-[10px] tracking-wide">Parsing mesh data...</div>
    </div>

    <div
      v-if="errorMsg"
      class="absolute inset-0 z-30 flex flex-col items-center justify-center"
      style="background: radial-gradient(ellipse at center, #1e1e2a 0%, #111116 70%, #0a0a0e 100%)"
    >
      <div class="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center mb-2">
        <Icon icon="carbon:warning-alt" class="text-red-400 text-lg" />
      </div>
      <div class="text-red-400/80 text-[10px] mb-1">Mesh load failed</div>
      <div class="text-white/25 text-[9px] max-w-[200px] text-center">{{ errorMsg }}</div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.vtk-ctrl-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: all 0.15s ease;
  cursor: pointer;
}

.vtk-ctrl-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(0, 0, 0, 0.6);
}

.vtk-loader {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(139, 92, 246, 0.15);
  border-top-color: rgba(139, 92, 246, 0.6);
  border-radius: 50%;
  animation: vtk-spin 0.8s linear infinite;
}

@keyframes vtk-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
