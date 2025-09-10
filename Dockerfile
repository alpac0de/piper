FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir /models && \
    mkdir -p /tmp/piper

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install piper-tts and Flask with Gunicorn for production
RUN pip install --no-cache-dir piper-tts flask gunicorn

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
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fettah/medium/tr_TR-fettah-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fettah/medium/tr_TR-fettah-medium.onnx.json

# Fix espeak-ng-data path with symbolic link
RUN ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true

# Expose port 5000
EXPOSE 5000

# Copy Flask application
COPY app.py /app/app.py

# Start Flask application with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
