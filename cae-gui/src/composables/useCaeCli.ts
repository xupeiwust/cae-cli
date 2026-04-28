import { ref } from 'vue'

interface CommandResult<T = unknown> {
  ok: boolean
  data?: T
  error?: {
    code: string
    message: string
  }
}

export function useCaeCli() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function runCommand<T = unknown>(args: string[]): Promise<CommandResult<T>> {
    loading.value = true
    error.value = null

    try {
      const { Command } = await import('@tauri-apps/plugin-shell')
      const command = Command.create('cae', args)
      const output = await command.execute()

      if (output.code !== 0) {
        const errMsg = output.stderr || `命令执行失败 (code: ${output.code})`
        error.value = errMsg
        return { ok: false, error: { code: 'EXEC_FAILED', message: errMsg } }
      }

      try {
        const data = JSON.parse(output.stdout) as T
        return { ok: true, data }
      } catch {
        return { ok: true, data: output.stdout as unknown as T }
      }
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e)
      error.value = errMsg
      return { ok: false, error: { code: 'CALL_FAILED', message: errMsg } }
    } finally {
      loading.value = false
    }
  }

  async function solve(inputFile: string, outputDir?: string) {
    const args = ['solve', inputFile]
    if (outputDir) args.push('-o', outputDir)
    return runCommand(args)
  }

  async function diagnose(resultDir: string, options?: { ai?: boolean; json?: boolean }) {
    const args = ['diagnose', resultDir]
    if (options?.ai) args.push('--ai')
    if (options?.json) args.push('--json')
    return runCommand(args)
  }

  async function dockerStatus() {
    return runCommand(['docker', 'status'])
  }

  async function dockerCatalog() {
    return runCommand(['docker', 'catalog'])
  }

  async function dockerPull(image: string) {
    return runCommand(['docker', 'pull', image])
  }

  async function dockerCalculix(inputFile: string, image?: string, outputDir?: string) {
    const args = ['docker', 'calculix', inputFile]
    if (image) args.push('--image', image)
    if (outputDir) args.push('-o', outputDir)
    return runCommand(args)
  }

  async function inpCheck(file: string) {
    return runCommand(['inp', 'check', file])
  }

  async function inpInfo(file: string) {
    return runCommand(['inp', 'info', file])
  }

  async function solvers() {
    return runCommand(['solvers'])
  }

  async function info() {
    return runCommand(['info'])
  }

  return {
    loading,
    error,
    runCommand,
    solve,
    diagnose,
    dockerStatus,
    dockerCatalog,
    dockerPull,
    dockerCalculix,
    inpCheck,
    inpInfo,
    solvers,
    info,
  }
}
