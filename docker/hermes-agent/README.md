# hermes-agent (custom build)

This image extends [`nousresearch/hermes-agent:latest`](https://hub.docker.com/r/nousresearch/hermes-agent) with additional capabilities.

## Additions

### faster-whisper — local speech-to-text

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) is a reimplementation of OpenAI Whisper using [CTranslate2](https://github.com/OpenNMT/CTranslate2), providing significantly faster inference with lower memory usage.

**Packages added to the hermes venv:**

| Package | Purpose |
|---|---|
| `faster-whisper` | Core STT library |
| `nvidia-cudnn-cu12` | cuDNN runtime for CUDA 12 (GPU inference) |
| `nvidia-cublas-cu12` | cuBLAS runtime for CUDA 12 (GPU inference) |

**Unraid template variables:**

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | Model size: `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `cuda` | `cuda` for NVIDIA GPU, `cpu` for CPU-only |
| `WHISPER_COMPUTE_TYPE` | `float16` | `float16` (GPU), `int8` (CPU/low-VRAM) |

> **CPU-only / no NVIDIA GPU?** Remove `nvidia-cudnn-cu12` and `nvidia-cublas-cu12` from the `Dockerfile` and set `WHISPER_DEVICE=cpu` in the template.

---

*Add future capability additions to this README as new sections.*
