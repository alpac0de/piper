import os
import subprocess
import tempfile
import logging
import wave
from flask import Flask, request, jsonify, send_file
from piper import PiperVoice

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

if "ACCESS_TOKEN" not in os.environ:
    raise RuntimeError("The ACCESS_TOKEN environment variable is required but was not set.")

ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

tempfile.tempdir = '/tmp/piper'

# Voice cache to avoid reloading models
voice_cache = {}

@app.route('/tts', methods=['POST'])
def tts():
    """
    TTS endpoint protected by a token in the header Authorization: Bearer <token>.
    Receives a JSON {"text": "...", "lang": "..."} and returns a WAV audio file.
    """

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split(" ")[1]  # Gets the part after 'Bearer'
    if token != ACCESS_TOKEN:
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']
    lang = data.get('lang', 'en')  # Default value: 'en'

    models_config = {
        'en': {
            'model_path': "/models/en_US-lessac-medium.onnx",
        },
        'fr': {
            'model_path': "/models/fr_FR-upmc-medium.onnx",
        },
        'el': {
            'model_path': "/models/el_GR-chreece-high.onnx",
        },
        'tr': {
            'model_path': "/models/tr_TR-fettah-medium.onnx",
        },
    }

    if lang not in models_config:
        return jsonify({'error': f'Unsupported language: {lang}'}), 400

    model_path = models_config[lang]['model_path']

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name

    try:
        app.logger.debug(f"Trying to process text: '{text}' (lang={lang})")

        # Load voice from cache or create new one
        if model_path not in voice_cache:
            app.logger.debug(f"Loading voice model: {model_path}")
            voice_cache[model_path] = PiperVoice.load(model_path)
        
        voice = voice_cache[model_path]
        
        # Generate speech using piper Python API with proper WAV format
        with wave.open(output_path, 'wb') as wav_file:
            # Let piper set the wav file parameters
            voice.synthesize_wav(text, wav_file)

        app.logger.debug(f"Piper generation completed successfully")

        return send_file(output_path, mimetype='audio/wav')

    except Exception as e:
        app.logger.error(f"Piper error: {str(e)}")
        return jsonify({'error': f'Piper error: {str(e)}'}), 500
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
