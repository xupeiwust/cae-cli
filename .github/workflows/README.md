# GitHub Actions CI/CD Workflow Documentation

## File Location
`cae-cli/.github/workflows/ci-cd.yml`

## Workflow Overview

| Job | Trigger | Description |
|-----|---------|-------------|
| `lint` | Every push/PR | Code linting (ruff) |
| `test` | Every push/PR | Multi-version Python (3.10/3.11/3.12) testing |
| `build` | Every push/PR | Build wheel package validation |
| `test-pygccx` | Every push/PR | Test pygccx library |
| `publish-test` | Tag `v*` | Publish to Test PyPI |
| `publish` | Tag `release/v*` | Publish to official PyPI |
| `release` | Tag `release/v*` | Create GitHub Release |

## Configuration Steps

### 1. GitHub Secrets Configuration

Add the following in repository Settings → Secrets and variables → Actions:

| Secret Name | Purpose | How to Get |
|-------------|---------|------------|
| `TEST_PYPI_API_TOKEN` | Test PyPI publishing | Generate API Token at [Test PyPI](https://test.pypi.org/account/register/) |
| `PYPI_API_TOKEN` | Official PyPI publishing | Generate API Token at [PyPI](https://pypi.org/account/register/) |

### 2. Publishing Process

```bash
# 1. Ensure version follows semantic versioning (PEP 440)
# The version in pyproject.toml must match the tag

# 2. Create release tag
git tag release/v1.5.0
git push origin release/v1.5.0

# Or use GitHub UI to create Release
```

### 3. Version Number Rules

- **Development version**: `git push` to main/develop → automatic CI/CD
- **Test release**: `git tag v1.5.0-alpha.1` → publishes to Test PyPI
- **Official release**: `git tag release/v1.5.0` → publishes to PyPI + creates GitHub Release

## Included Checks

### Lint
- ruff syntax checking
- ruff code formatting check

### Test
- Python 3.10, 3.11, 3.12
- Coverage report (cov-report)
- Automatic upload to Codecov

### Build
- Source code built to wheel
- Installation verification
- CLI command availability verification

## Customization Options

### Modify Python Versions
Edit the matrix in `ci-cd.yml`:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```

### Add More Dependencies
Edit `[project.optional-dependencies]` in `pyproject.toml`

### Modify Trigger Branches
```yaml
on:
  push:
    branches: [main, develop]  # Modify here
  pull_request:
    branches: [main]         # Modify here
```

## Important Notes

1. **Permissions**: PyPI publishing requires repository admin permissions
2. **Tag format**: Must use `release/v` prefix to trigger official release
3. **Test coverage**: Ensure there are test files in `tests/` directory
4. **Coverage**: First-time users need to authorize the repository on Codecov website

## Status Monitoring

- **GitHub Actions**: Repository → Actions tab
- **PyPI**: https://pypi.org/project/cae-cxx/
- **Codecov**: https://app.codecov.io/gh/<owner>/<repo>
