# Development Log

> Dated engineering notes for `cae-cli`. This log tracks implementation
> milestones and verification results rather than formal release notes.

## 2026-04-21 | Verified Docker solver smoke cases

### Completed

- Added real smoke examples for SU2, Code_Aster, and OpenFOAM under
  `examples/`.
- Verified a tutorial-derived SU2 CFD smoke case through `su2-runtime`
  using `examples/su2_inviscid_bump/inv_channel_smoke.cfg`.
- Verified a minimal Code_Aster smoke case through
  `simvia/code_aster:stable` using
  `examples/code_aster_minimal_smoke/case.comm`.
- Verified an OpenFOAM cavity smoke case through
  `microfluidica/openfoam:11` using
  `examples/openfoam_cavity_smoke` with `blockMesh && icoFoam`.
- Pushed commit `6558d62` (`feat: add verified solver docker smoke cases`)
  to `main`.

### Runtime and environment decisions

- Standardized the active Docker environment on the dedicated WSL distro
  `CAE-Docker` at `D:\WSL\CAE-Docker`.
- Switched the Docker registry setup in that distro to a multi-mirror
  configuration after `dockerproxy.net` became unreliable for some image
  namespaces.
- Kept the broken legacy `Ubuntu` distro out of the active Docker path
  instead of continuing to build on an unstable WSL instance.

### Code changes

- `cae/docker/generic.py`: copy solver sidecar inputs for SU2
  `*_FILENAME` references and Code_Aster `.export`-referenced local files
  into the mounted work directory.
- `cae/docker/images.py`: fixed runnable commands for Code_Aster,
  switched `openfoam-lite` to `microfluidica/openfoam:11`, and aligned the
  `su2-runtime` command with the image entrypoint.
- `tests/test_docker_feature.py`: expanded Docker feature coverage around
  smoke-case inputs and catalog behavior.

### Verification

```text
ruff check
python -m pytest
115 passed
```

### Runtime artifacts

- `results/su2-inviscid-bump-smoke/history.csv`
- `results/code-aster-smoke/docker-code_aster.log`
- `results/openfoam-cavity-smoke/docker-openfoam.log`

### Next

- Normalize solver output harvesting so logs, residuals, and result files
  can feed the diagnosis pipeline in a consistent shape.
- Add solver selection and preflight scoring on top of the current Docker
  catalog.
- Keep PINN as an augmentation layer after the traditional solver baseline
  remains stable and reproducible.
