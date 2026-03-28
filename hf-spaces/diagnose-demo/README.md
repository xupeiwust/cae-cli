# cae-cli Diagnosis Demo

A Gradio-based CalculiX solver output diagnosis tool.

## Features

- Upload `.inp` / `.stderr` / `.dat` files for automatic problem root cause detection
- Or paste solver output content directly

## Deploy to Hugging Face Spaces

1. Upload `app.py` and `requirements.txt` to your Space
2. Hugging Face will automatically install dependencies and start the app

## Local Run

```bash
pip install -r requirements.txt
python app.py
```

## Detectable Problem Types

| Category | Detection Content |
|----------|------------------|
| Convergence | Solution divergence, increment too small, not converged |
| Material Definition | Missing elastic constants, density, material card |
| Element Quality | Negative Jacobian, hourglass mode |
| Input Syntax | Invalid card, parameter name error |
| Numerical Anomaly | Displacement overflow, large deformation detection |

## Related Links

- **GitHub**: https://github.com/yd5768365-hue/cae-cli
- **Full version**: `pip install cae-cxx`
