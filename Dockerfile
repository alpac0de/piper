# Utilise l'image de base Debian
FROM debian:bookworm-slim

# Installation des dépendances
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    espeak-ng \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Création des dossiers nécessaires
RUN mkdir /models && \
    mkdir -p /tmp/piper

# Téléchargement et installation de Piper
RUN wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz && \
    tar xvzf piper_linux_x86_64.tar.gz && \
    mv piper/piper /usr/local/bin/ && \
    mv piper/*.so* /usr/local/lib/ && \
    rm -rf piper* && \
    chmod 755 /usr/local/bin/piper && \
    ldconfig

# Téléchargement du modèle (ONNX + JSON)
RUN cd /models && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json && \
    mv en_US-lessac-medium.onnx.json en_US-lessac-medium.json

# Téléchargement du modèle français "tom-medium"
RUN mkdir -p /models/fr && cd /models/fr && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx.json && \
    mv fr_FR-tom-medium.onnx fr_FR-tom-med.onnx && \
    mv fr_FR-tom-medium.onnx.json fr_FR-tom-med.json

# Téléchargement du modèle grec "el_gr-mls-medium"
RUN mkdir -p /models/el && cd /models/el && \
    wget https://huggingface.co/Chreece/el_GR-chreece-high/resolve/main/el_GR-chreece-high.onnx && \
    wget https://huggingface.co/Chreece/el_GR-chreece-high/resolve/main/el_GR-chreece-high.onnx.json && \
    mv el_GR-chreece-high.onnx.json el_GR-chreece-high.json

# Téléchargement du modèle turc "tr_TR-fettah-medium"
RUN mkdir -p /models/tr && cd /models/tr && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fettah/medium/tr_TR-fettah-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fettah/medium/tr_TR-fettah-medium.onnx.json && \
    mv tr_TR-fettah-medium.onnx.json tr_TR-fettah-medium.json

# Correction du chemin espeak-ng-data (lien symbolique)
# Sous Debian, les data Espeak-ng peuvent se trouver dans /usr/lib/x86_64-linux-gnu/espeak-ng-data
# Si le répertoire existe, on crée un symlink vers /usr/share/espeak-ng-data
RUN ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true

# Création et activation de l'environnement virtuel
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copie et installation des dépendances Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copie de l'application
COPY app.py /app/app.py

# Exposition du port 5000
EXPOSE 5000

# Lancement de l'application Flask
CMD ["python", "app.py"]
