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
| `playwright` | Browser automation for Fintel short-data scraping in squeeze scanner |

**Environment variables added:**

| Variable | Default | Description |
|---|---|---|
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/hermes/.playwright` | Chromium browser binaries location |

Chromium is installed at build time under `PLAYWRIGHT_BROWSERS_PATH` (inside the image). The squeeze scanner's `squeeze_alert.sh` reads this env var to find the browser for Fintel short-borrow data.

**Unraid template variables:**

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | Model size: `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `cuda` | `cuda` for NVIDIA GPU, `cpu` for CPU-only |
| `WHISPER_COMPUTE_TYPE` | `float16` | `float16` (GPU), `int8` (CPU/low-VRAM) |

> **CPU-only / no NVIDIA GPU?** Remove `nvidia-cudnn-cu12` and `nvidia-cublas-cu12` from the `Dockerfile` and set `WHISPER_DEVICE=cpu` in the template.

---

### Spotify auth via Tailscale

Hermes's built-in Spotify PKCE flow only accepts `http://localhost` redirect URIs, which
doesn't work inside Docker without HTTPS. This image bundles a patch script that lifts that
restriction so you can use a Tailscale HTTPS hostname as the redirect URI.

**Bundled file:** `/opt/fix_spotify_auth.py`

**Full setup guide:** [`spotify-tailscale-auth.md`](./spotify-tailscale-auth.md)

Quick start (run once after a fresh container):

```bash
# 1. Patch Hermes's auth code
docker exec -u 0 hermes python3 /opt/fix_spotify_auth.py

# 2. Set the redirect URI (adjust hostname to match your Tailscale machine name)
docker exec hermes sed -i \
  's|HERMES_SPOTIFY_REDIRECT_URI=.*|HERMES_SPOTIFY_REDIRECT_URI=https://<your-machine>.ts.net/spotify/callback|' \
  /home/hermes/.hermes/.env

# 3. Authenticate
docker exec -it hermes hermes auth spotify
```

See the [full guide](./spotify-tailscale-auth.md) for Tailscale serve configuration and recovery steps.

---

*Add future capability additions to this README as new sections.*