<div align="center">
  <img src="logo.svg" alt="cae-cli" width="380">
  <h1>cae-cli</h1>
  <p>A lightweight CAE command-line tool: run a simulation with one command and inspect results with one link.</p>
  <p>Built around <a href="https://www.calculix.org/">CalculiX</a>, with support for meshing, solving, visualization, diagnosis, and reporting.</p>
</div>

<p align="center">
  <a href="https://github.com/yd5768365-hue/cae-cli">GitHub</a> |
  <a href="https://pypi.org/project/cae-cxx/">PyPI</a> |
  <a href="DEVELOPMENT_LOG.md">Development Log</a> |
  <a href="https://github.com/yd5768365-hue/cae-cli/issues">Issues</a>
</p>

---

## Features

- End-to-end workflow: mesh generation -> solving -> visualization -> diagnosis -> PDF reporting
- Local-first execution: core computation and result processing run on your own machine
- AI-assisted diagnosis: rule-based checks + reference cases + optional deep AI analysis
- INP toolchain: inspect, view, modify, generate templates, and suggest fixes
- Standalone Docker workflow: check Docker/WSL Docker and run containerized CalculiX separately
- Automation-friendly: CLI-first design for scripting and batch integration

---

## Installation

```bash
pip install cae-cxx
```

Optional extras:

```bash
# AI features
pip install "cae-cxx[ai]"

# Mesh support (Gmsh / meshio)
pip install "cae-cxx[mesh]"

# PDF reporting (weasyprint)
pip install "cae-cxx[report]"

# MCP server integration
pip install "cae-cxx[mcp]"
```

Install CalculiX manually:

1. Download and install CalculiX from [calculix.org](https://www.calculix.org/).
2. Make sure `ccx` / `ccx.exe` is available in your `PATH`, or configure `solver_path` via `cae config`.

---

## Quick Start

```bash
# 1) Generate an INP template
cae inp template cantilever_beam -o beam.inp

# 2) Run the solver
cae solve beam.inp

# 3) View results in the browser (FRD is converted to VTU automatically)
cae view results/

# 4) Diagnose issues (optional)
cae diagnose results/

# 5) Generate a PDF report (optional)
cae report results/
```

---

## Command Overview

Main commands:

- `cae solve`: run an FEA solve
- `cae solvers`: inspect solver availability
- `cae info`: show configuration and version information
- `cae view`: inspect simulation results in the browser
- `cae convert`: manually convert `.frd -> .vtu`
- `cae diagnose`: diagnose simulation issues
- `cae docker`: standalone Docker and containerized solver tools
- `cae report`: generate a PDF report
- `cae inp`: parse and modify INP files
- `cae mesh`: meshing tools
- `cae model`: manage local Ollama models
- `cae config`: manage workspace configuration
- `cae-mcp`: run the MCP server for OpenCode and other MCP clients

`cae inp` subcommands:

- `info` / `check` / `show` / `modify` / `suggest` / `list` / `template`

`cae mesh` subcommands:

- `gen` / `check`

`cae model` subcommands:

- `list` / `pull` / `show` / `delete` / `set`

AI diagnose model resolution order:

1. `--model-name` (explicit per run)
2. `CAE_AI_MODEL` environment variable
3. `cae model set` stored `active_model`
4. default `deepseek-r1:1.5b`

`cae docker` subcommands:

- `catalog`: list built-in solver image aliases
- `pull`: pull an image by alias or direct Docker image reference
- `images`: list local Docker images visible to the selected Docker backend
- `status`: check Docker availability, including Docker installed inside Windows WSL
- `path`: convert a Windows path to the mount path used by WSL Docker
- `calculix`: run CalculiX in a Docker container as a separate workflow

---

## Common Usage

```bash
# Solve with a specified output directory
cae solve model.inp -o results/

# Inspect and view an INP file
cae inp check model.inp
cae inp show model.inp -k *MATERIAL

# Modify an INP file (example)
cae inp modify model.inp -k *ELASTIC --set "210000, 0.3"

# Generate a mesh
cae mesh gen geo.step -o mesh.inp

# Check mesh quality/preview
cae mesh check mesh.inp

# Enable deep AI diagnosis
cae diagnose results/ --ai

# Pin a specific AI model for this run (useful for fine-tuned A/B tests)
cae diagnose results/ --ai --model-name cae-ft:v1

# Export structured diagnosis JSON
cae diagnose results/ --json

# Export JSON to a file
cae diagnose results/ --json-out out/diagnose.json

# Override evidence guardrails config
cae diagnose results/ --json --guardrails cae/ai/data/evidence_guardrails.json

# Enable optional diagnosis history calibration (SQLite)
cae diagnose results/ --json --history-db out/diagnosis_history.db

# Check Docker or WSL Docker
cae docker status

# Show built-in solver image aliases
cae docker catalog
cae docker catalog --capability cfd
cae docker recommend "steady CFD turbulence"

# Pull the default CalculiX image and save it for future containerized runs
cae docker pull calculix-parallelworks --set-default

# List local Docker images
cae docker images

# Convert a Windows path for WSL Docker volume mounting
cae docker path D:\CAE-CLI\case

# Run CalculiX in a Docker container, separate from native `cae solve`
cae docker calculix model.inp --image calculix:latest -o results/docker-model

# Build a local SU2 runtime image that actually exposes SU2_CFD
cae docker build-su2-runtime --tag local/su2-runtime:8.3.0

# Run the included official SU2 CFD smoke case
cae docker run su2-runtime examples/su2_inviscid_bump/inv_channel_smoke.cfg -o results/su2-inviscid-bump-smoke

# Run the included minimal Code_Aster smoke case
cae docker pull code-aster
cae docker run code-aster examples/code_aster_minimal_smoke/case.comm -o results/code-aster-smoke

# Run the included OpenFOAM cavity smoke case
cae docker pull openfoam-lite
cae docker run openfoam-lite examples/openfoam_cavity_smoke --cmd "bash -lc 'blockMesh && icoFoam'" -o results/openfoam-cavity-smoke

# Run the included Elmer smoke case
cae docker run elmer examples/elmer_steady_heat/case.sif -o results/elmer-heat
```

---

## Docker Workflow

Docker support is intentionally separate from the native solver command. Use
`cae solve` for local/native CalculiX execution and `cae docker ...` for
containerized workflows.

To create an independent Docker Engine inside Ubuntu WSL for this project and
pull the core CalculiX image, run from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-cae-cli-docker-wsl.ps1
```

The reusable runtime definition is stored in `docker.yml`. If Docker is already
available inside WSL or Linux, you can build the project runtime directly from
the repository root:

```bash
docker compose -f docker.yml up --build cae-cli
docker tag cae-cli:latest cae-cli:calculix
```

The Compose flow builds a local `cae-cli:latest` image from
`docker/cae-cli/Dockerfile`, verifies the CalculiX executable, and keeps its
Compose-owned resources separate from older manually created `cae-cli`
containers or networks.
The PowerShell setup script wraps the same Compose path after installing Docker
Engine in WSL, and tags the default CalculiX runtime as
`cae-cli:latest` / `cae-cli:calculix`.
Use `-All` to also pull the larger optional solver images, including
`parallelworks/calculix:v2.15_exo`.
When Docker Hub is slow, pass mirrors with `-Mirrors`, for example
`-Mirrors "https://dockerproxy.net,https://docker.1panel.live,https://docker.m.daocloud.io"`.

On Windows, `cae docker status` probes native Docker first, then Docker installed
inside WSL through `wsl -e docker`. When WSL Docker is selected, host paths are
converted to `/mnt/<drive>/...` for volume mounts.

Containerized CalculiX uses this command shape:

```bash
cae docker pull cae-cli --set-default
cae docker calculix model.inp -o results/model-docker

# Or pass the local runtime explicitly without changing config.
cae docker calculix model.inp --image cae-cli -o results/model-docker
```

Other open-source solvers are exposed through the shared Docker catalog and
generic runner:

```bash
# CFD candidates: OpenFOAM and SU2
cae docker recommend "external aerodynamic CFD"
cae docker pull openfoam-lite
cae docker run openfoam-lite examples/openfoam_cavity_smoke --cmd "bash -lc 'blockMesh && icoFoam'" -o results/openfoam-cavity-smoke

# Structural and thermomechanical candidates: CalculiX and code_aster
cae docker recommend "nonlinear structural contact"
cae docker pull code-aster
cae docker run code-aster examples/code_aster_minimal_smoke/case.comm -o results/code-aster-smoke

# Multiphysics candidate: Elmer
cae docker recommend "thermal electromagnetic multiphysics"
cae docker pull elmer
cae docker run elmer case.sif -o results/elmer-case

# Local SU2 runtime candidate with an official CFD tutorial-derived smoke case
cae docker build-su2-runtime --tag local/su2-runtime:8.3.0
cae docker run su2-runtime examples/su2_inviscid_bump/inv_channel_smoke.cfg -o results/su2-inviscid-bump-smoke
```

The image can also be provided with `CAE_CALCULIX_DOCKER_IMAGE` or the
`docker_calculix_image` config key.
For other solver families, `cae docker pull <alias> --set-default` writes
`docker_<solver>_image`, for example `docker_code_aster_image`.

If Docker runs inside WSL and Docker Hub is slow, update WSL's
`/etc/docker/daemon.json` registry mirror and restart Docker before pulling.
The built-in catalog records per-image command paths because public solver
images do not always expose their solver launchers on `PATH`.
For SU2 `.cfg` inputs, the generic runner also copies referenced sidecar files
such as `MESH_FILENAME` and other existing `*_FILENAME` inputs into the mounted
work directory before launching the container.
For Code_Aster `.export` inputs, the generic runner also copies referenced local
sidecar files such as `.comm` or `.med` inputs into the mounted work directory
before launching the container.
`cae docker pull` reuses a local image by default; add `--refresh` when you
want to contact the remote registry again.

Built-in Docker solver aliases currently include:

| Alias | Solver | Typical use |
| --- | --- | --- |
| `calculix-parallelworks` | CalculiX | Structural/thermal FEM with `.inp` input |
| `code-aster` | code_aster | Nonlinear structure, contact, thermal mechanics |
| `openfoam-foundation-11` | OpenFOAM | Smaller official OpenFOAM Foundation v11 fallback image |
| `openfoam` | OpenFOAM | CFD case directories; override `--cmd` per solver app |
| `openfoam-lite` | OpenFOAM | Community fallback image validated with the cavity smoke case |
| `su2-runtime` | SU2 | Locally built runtime image exposing `SU2_CFD` |
| `su2` | SU2 | Build container only; not a direct `SU2_CFD` runtime image |
| `elmer` | Elmer | Multiphysics FEM with `.sif` input |

The repository includes validated smoke examples for:

- `examples/openfoam_cavity_smoke`
- `examples/su2_inviscid_bump/inv_channel_smoke.cfg`
- `examples/code_aster_minimal_smoke/case.comm`
- `examples/elmer_steady_heat/case.sif`

---

## MCP Server (for OpenCode)

`cae-cli` can run as an MCP server over `stdio` so OpenCode can call it reliably.

Install MCP extra:

```bash
pip install "cae-cxx[mcp]"
```

Start server:

```bash
cae-mcp
```

Provided MCP tools:

- `cae_health`
- `cae_solvers`
- `cae_solve`
- `cae_docker_status`
- `cae_docker_catalog`
- `cae_docker_recommend`
- `cae_docker_images`
- `cae_docker_pull`
- `cae_docker_run`
- `cae_docker_build_su2_runtime`
- `cae_docker_calculix`
- `cae_diagnose`
- `cae_inp_check`

All tools return a stable envelope:

- success: `{"ok": true, "data": ...}`
- error: `{"ok": false, "error": {"code": "...", "message": "...", "details": {...}}}`

Example OpenCode MCP config:

```json
{
  "mcpServers": {
    "cae-cli": {
      "command": "python",
      "args": ["-m", "cae.mcp_server"]
    }
  }
}
```

---

## Diagnosis Output and Guardrails

`cae diagnose --json` exports structured issues with grounded evidence fields:

- `evidence_line`: `file:line: excerpt` evidence for the issue
- `evidence_score`: confidence score in `[0,1]`
- `evidence_support_count`: number of independent files supporting the issue
- `evidence_conflict`: contradiction note when evidence trends conflict

Guardrail thresholds are category-aware and configurable:

- Default config path: `cae/ai/data/evidence_guardrails.json`
- CLI override: `--guardrails <path>`
- Environment override: `CAE_EVIDENCE_GUARDRAILS_PATH=<path>`

You can also enable history-consistency calibration:

- CLI option: `--history-db <path>`
- Environment fallback: `CAE_DIAG_HISTORY_DB_PATH=<path>`
- JSON fields per issue:
  `history_hits`, `history_avg_score`, `history_conflict_rate`,
  `history_similarity`, `history_similar_hits`, `history_similar_conflict_rate`

The default guardrails file also supports a `default` bucket, used as fallback for
categories without an explicit entry.

When evidence is weak or contradictory for sensitive categories, severity can be
automatically downgraded (for example `error -> warning`) to reduce false positives.

---

## Project Structure

```text
cae-cli/
|-- cae/                  # Main code
|   |-- main.py            # CLI entry point (Typer)
|   |-- mcp_server.py      # MCP stdio server
|   |-- docker/            # Standalone Docker/containerized solver features
|   |-- runtimes/          # Runtime adapters such as native or WSL Docker
|   |-- inp/               # INP parsing, inspection, editing, and templates
|   |-- mesh/              # Mesh-related features
|   |-- solvers/           # Solver abstraction and registry
|   |-- viewer/            # FRD parsing, conversion, visualization, and reports
|   |-- ai/                # Diagnosis and AI features
|   |-- installer/         # Solver/model installation
|   `-- config/            # Configuration management
|-- cae-gui/              # Tauri + Vue desktop GUI
|-- cae_cli_v2/           # Fine-tune dataset v2 (291 records)
|-- cae_cli_v2_2000/      # Extended fine-tune dataset (2000 records)
|-- scripts/              # Build, export, and setup scripts
|-- tests/                # Tests
`-- README.md
```

---

## Development

Recommended clone command:

```bash
git clone --recurse-submodules https://github.com/yd5768365-hue/cae-cli.git
cd cae-cli
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Windows PowerShell setup:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip

# Minimal developer install: enough for CLI, diagnosis, lint, and tests.
python -m pip install -e ".[dev]"

# Optional full developer install.
python -m pip install -e ".[dev,ai,mesh,report,mcp]"
```

If PowerShell blocks virtualenv activation for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS / Linux setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"

# Optional full developer install.
python -m pip install -e ".[dev,ai,mesh,report,mcp]"
```

Verify the local checkout:

```bash
python -m ruff check cae tests
python -m pytest tests/test_diagnose_json_cli.py tests/test_mcp_server.py tests/test_solver_output_bridge.py -q
```

Run the CLI from source:

```bash
cae --help
cae diagnose tests/fixtures/diagnosis_cases/convergence/not_converged
cae diagnose tests/fixtures/diagnosis_cases/convergence/not_converged --json
```

Optional Docker/WSL checks:

```bash
cae docker status
cae docker catalog
cae docker recommend "CFD smoke test"
```

Regenerate fine-tune datasets:

```bash
# Export v2 dataset (291 records)
python scripts/export_finetune_dataset.py

# Generate extended v2-2000 dataset (2000 records)
python scripts/generate_2000_training_data.py
```

On Windows with Docker installed inside WSL, keep Docker running in the WSL
distribution first, then use `cae docker status` from PowerShell to confirm that
`cae-cli` can see it.

---

## Fine-tune Dataset

`cae-cli` ships structured diagnostic fine-tune datasets for training CAE-specific language models.

### v2 Dataset (291 records)

Located in `cae_cli_v2/`, exported from project test fixtures, solver logs, and routing policies.

```text
cae_cli_v2/
├── all.jsonl              # full rich records with metadata + messages
├── train.jsonl            # train split (221)
├── val.jsonl              # validation split (36)
├── test.jsonl             # test split (34)
├── train_hq.jsonl         # high-quality train (quality_score >= 0.9)
├── manifest.json          # counts and quality filter metadata
└── manifest_hq.json       # HQ subset counts
```

### v2-2000 Extended Dataset (2000 records)

Located in `cae_cli_v2_2000/`, expanded with richer error scenarios, wrong-diagnosis corrections, evidence guardrail checks, risk scoring, and solver family detection.

```text
cae_cli_v2_2000/
├── all.jsonl              # 2000 full records
├── train.jsonl            # train split (~1525)
├── val.jsonl              # validation split (~260)
├── test.jsonl             # test split (~215)
├── *_chat.jsonl           # chat-only format for common finetune toolchains
├── *_hq.jsonl             # high-quality subset (quality_score >= 0.9, ~1485)
└── manifest.json          # dataset manifest with split/task-type counts
```

**20 task types** including:

| Task Type | Description | Records |
| --- | --- | --- |
| `status_reason_routing_augmented` | Map runtime status reasons to solver routes | 518 |
| `evidence_guardrail_check` | Check evidence against guardrail thresholds | 367 |
| `fixture_route_mapping` | Route fixture issues to diagnostic lanes | 269 |
| `risk_score_calculation` | Calculate risk scores for diagnostic issues | 165 |
| `solver_route_decision_augmented` | Augmented solver gate routing | 124 |
| `guarded_executor_decision_augmented` | Evaluate guarded write eligibility | 104 |
| `status_reason_routing` | Map status reasons to solver status | 62 |
| `issue_key_extraction` | Extract diagnosis labels from INP+stderr | 61 |
| `inp_keyword_validation` | Validate CalculiX INP keywords | 54 |
| `wrong_diagnosis_correction` | Correct wrong diagnoses with explanations | 27 |
| ... | (10 more types) | ... |

**Key features:**

- Both **correct** and **incorrect** diagnosis examples for contrastive training
- Deterministic routing policies: `failed→runtime_remediation`, `not_converged→convergence_tuning`, `success→physics_diagnosis`, `unknown→evidence_expansion`
- Multi-solver coverage: CalculiX, SU2, OpenFOAM, Code_Aster, Elmer
- Guarded executor write-safety decisions with backup-first policies
- Evidence guardrail thresholds with pass/fail outcomes
- Risk scoring with category-aware severity weights

Regenerate the extended dataset:

```bash
python scripts/generate_2000_training_data.py
```

---

## License

MIT. See [LICENSE](LICENSE).
