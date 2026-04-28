param(
    [switch]$All,
    [string]$Mirrors = "",
    [string]$Distro = "Ubuntu"
)

$ErrorActionPreference = "Stop"

function Quote-Sh {
    param([string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

function ConvertTo-WslPath {
    param([string]$Path)

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    if ($fullPath -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLowerInvariant()
        $rest = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    return $fullPath -replace '\\', '/'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRootWsl = ConvertTo-WslPath $repoRoot
$scriptPath = "$repoRootWsl/scripts/install-docker-wsl.sh"
$pullSet = if ($All) { "all" } else { "core" }

$command = "chmod +x $(Quote-Sh $scriptPath) && "
$command += "CAE_CLI_REPO_ROOT=$(Quote-Sh $repoRootWsl) "
$command += "CAE_DOCKER_PULL_SET=$(Quote-Sh $pullSet) "
if ($Mirrors.Trim()) {
    $command += "CAE_DOCKER_REGISTRY_MIRRORS=$(Quote-Sh $Mirrors.Trim()) "
}
$command += "$(Quote-Sh $scriptPath)"

& wsl -d $Distro -u root -e bash -lc $command
exit $LASTEXITCODE
