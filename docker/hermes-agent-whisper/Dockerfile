# Extends the official Hermes Agent image with faster-whisper for local STT
FROM nousresearch/hermes-agent:latest

USER root

# Install faster-whisper into the existing hermes venv.
# nvidia-cudnn-cu12 and nvidia-cublas-cu12 provide GPU-accelerated inference
# on NVIDIA cards via CTranslate2 (no separate CUDA toolkit required on the host).
# Remove the nvidia-* packages if you only need CPU inference.
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir \
    faster-whisper \
    nvidia-cudnn-cu12 \
    nvidia-cublas-cu12 && \
    chown -R hermes:hermes /opt/hermes/.venv
