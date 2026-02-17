FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    wget \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir /models && \
    mkdir -p /tmp/piper

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Download voice models - flat structure as expected by piper-tts
RUN cd /models && \
    # English model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json && \
    # French model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json && \
    # Greek model
    wget https://huggingface.co/Chreece/el_GR-chreece-high/resolve/main/el_GR-chreece-high.onnx && \
    wget https://huggingface.co/Chreece/el_GR-chreece-high/resolve/main/el_GR-chreece-high.onnx.json && \
    # Turkish model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx.json && \
    # German model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json && \
    # Spanish model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json && \
    # Italian model
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json

# Fix espeak-ng-data path with symbolic link
RUN ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true

RUN useradd --create-home --no-log-init piper && \
    chown -R piper:piper /app /models /tmp/piper

EXPOSE 5000

COPY --chown=piper:piper app.py /app/app.py

USER piper

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--timeout-keep-alive", "120"]
