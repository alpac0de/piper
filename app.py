import os
import subprocess
import tempfile
import logging
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

if "ACCESS_TOKEN" not in os.environ:
    raise RuntimeError("The ACCESS_TOKEN environment variable is required but was not set.")

ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

tempfile.tempdir = '/tmp/piper'

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
            'config_path': "/models/en_US-lessac-medium.json"
        },
        'fr': {
            'model_path': "/models/fr/fr_FR-tom-med.onnx",
            'config_path': "/models/fr/fr_FR-tom-med.json"
        },
        'el': {
            'model_path': "/models/el/el_GR-chreece-high.onnx",
            'config_path': "/models/el/el_GR-chreece-high.json"
        },
        'tr': {
            'model_path': "/models/tr/tr_TR-fettah-medium.onnx",
            'config_path': "/models/tr/tr_TR-fettah-medium.json"
        },
    }

    if lang not in models_config:
        return jsonify({'error': f'Unsupported language: {lang}'}), 400

    model_path = models_config[lang]['model_path']
    config_path = models_config[lang]['config_path']

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name

    try:
        app.logger.debug(f"Trying to process text: '{text}' (lang={lang})")

        process = subprocess.run(
            [
                '/usr/local/bin/piper',
                '--model', model_path,
                '--config', config_path,
                '--output_file', output_path
            ],
            input=text.encode(),
            capture_output=True,
            check=True
        )
        app.logger.debug(f"Piper stdout: {process.stdout}")
        app.logger.debug(f"Piper stderr: {process.stderr}")

        return send_file(output_path, mimetype='audio/wav')

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Piper error: {e.stderr.decode()}")
        return jsonify({'error': f'Piper error: {e.stderr.decode()}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)