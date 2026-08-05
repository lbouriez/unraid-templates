# =============================================================================
# Hermes Agent — Custom Build
# =============================================================================
# Extends nousresearch/hermes-agent:latest with additional packages and
# plugins for local STT (faster-whisper), browser automation (Playwright),
# Spotify Tailscale auth patch, and OpenMemory provider plugin.
# =============================================================================

FROM nousresearch/hermes-agent:latest

USER root

# ---------------------------------------------------------------------------
# Environment — persist venv activation + custom paths
# ---------------------------------------------------------------------------
ENV VIRTUAL_ENV=/opt/hermes/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright

# ---------------------------------------------------------------------------
# Python packages — installed into the Hermes venv via uv
# ---------------------------------------------------------------------------
# faster-whisper (STT) + NVIDIA GPU libs: local speech-to-text via CTranslate2
#   Remove nvidia-* lines if CPU-only.
# Playwright + Chromium: browser automation for Fintel short-data scraping
#   (squeeze scanner in ticker-lab repo).


RUN uv pip install --no-cache-dir \
    faster-whisper \
    nvidia-cudnn-cu12 \
    nvidia-cublas-cu12 \
    playwright
RUN chown -R hermes:hermes /opt/hermes/.venv && \
    mkdir -p /opt/hermes/.playwright && \
    python3 -m playwright install chromium && \
    chown -R hermes:hermes /opt/hermes/.playwright

# --- Dashboard ---
COPY dashboard-run /etc/s6-overlay/s6-rc.d/dashboard/run
RUN chmod 755 /etc/s6-overlay/s6-rc.d/dashboard/run

# --- Spotify Tailscale auth patch ---
COPY fix_spotify_auth.py /opt/fix_spotify_auth.py

# ---------------------------------------------------------------------------
# OpenMemory memory provider plugin
# ---------------------------------------------------------------------------
COPY plugins/openmemory/ /opt/hermes/plugins/memory/openmemory/
RUN chmod -R 755 /opt/hermes/plugins/memory/openmemory/
