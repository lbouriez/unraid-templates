# hermes-agent (custom build)

This image extends [`nousresearch/hermes-agent:latest`](https://hub.docker.com/r/nousresearch/hermes-agent) with additional capabilities.

## Overview of additions

| Addition | Category | Bundled in image |
|---|---|---|
| faster-whisper | Speech-to-text (local STT) | ✅ Python package |
| Playwright + Chromium | Browser automation (Fintel scraping) | ✅ Python package + binaries |
| Spotify Tailscale auth patch | Auth fix for Docker | ✅ Script |
| OpenMemory plugin | Memory provider backend | ✅ Plugin files |

---

## 1. faster-whisper — local speech-to-text

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) is a reimplementation of OpenAI Whisper using [CTranslate2](https://github.com/OpenNMT/CTranslate2), providing significantly faster inference with lower memory usage.

**Python packages added:**

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

## 2. Playwright + Chromium — browser automation

Used by the **squeeze scanner** (ticker-lab repo) to scrape Fintel short-borrow data (shares available, borrow fee rates, short volume ratio).

**Python packages added:**

| Package | Purpose |
|---|---|
| `playwright` | Headless browser automation |

**Environment variables:**

| Variable | Value | Description |
|---|---|---|
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/hermes/.playwright` | Chromium binaries location (inside image) |

Chromium is installed at build time — no runtime download needed. The squeeze scanner's `squeeze_alert.sh` reads `PLAYWRIGHT_BROWSERS_PATH` to find the browser.

---

## 3. Spotify auth via Tailscale

Hermes's built-in Spotify PKCE flow only accepts `http://localhost` redirect URIs, which doesn't work inside Docker without HTTPS. This image bundles a patch script that lifts that restriction so you can use a Tailscale HTTPS hostname as the redirect URI.

**Bundled file:** `/opt/fix_spotify_auth.py`

**Full setup guide:** [`spotify-tailscale-auth.md`](./spotify-tailscale-auth.md)

Quick start (run once after a fresh container):

```bash
# 1. Patch Hermes's auth code
docker exec -u 0 hermes python3 /opt/fix_spotify_auth.py

# 2. Set the redirect URI (adjust hostname to match your Tailscale machine name)
docker exec hermes sed -i \
  's|HERMES_SPOTIFY_REDIRECT_URI=.*|HERMES_SPOTIFY_REDIRECT_URI=https://<your-machine>.ts.net/spotify/callback|' \
  /opt/data/.env

# 3. Authenticate
docker exec -it hermes hermes auth spotify
```

See the [full guide](./spotify-tailscale-auth.md) for Tailscale serve configuration and recovery steps.

---

## 4. OpenMemory memory provider plugin

Allows Hermes to connect to a self-hosted mem0-aio / OpenMemory server for persistent memory storage.

**Plugin files:** `/opt/hermes/plugins/memory/openmemory/`

The plugin is baked into the image's immutable `/opt/hermes` install tree. Persistent configuration and user data belong under `/opt/data`; do not mount a volume over `/opt/hermes`, because stale contents can hide files added by an image update.

**Activation inside Hermes:**
```bash
hermes memory setup openmemory
# or: hermes config set memory.provider openmemory
```
