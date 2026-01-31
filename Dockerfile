FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y \
    wget \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir /models && \
    mkdir -p /tmp/piper

# Install piper-tts (piper1-gpl v1.3.0) and Flask with Gunicorn for production
RUN pip install --no-cache-dir "piper-tts>=1.3.0" flask gunicorn

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
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx.json

# Fix espeak-ng-data path with symbolic link
RUN ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true

# Expose port 5000
EXPOSE 5000

# Copy Flask application
COPY app.py /app/app.py

# Start Flask application with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
