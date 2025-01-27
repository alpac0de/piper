from flask import Flask, request, send_file
import subprocess
import os
import tempfile
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configuration du dossier temporaire
tempfile.tempdir = '/tmp/piper'

@app.route('/tts', methods=['POST'])
def tts():
    data = request.get_json()
    if not data or 'text' not in data:
        return {'error': 'No text provided'}, 400

    text = data['text']
    lang = data.get('lang', 'en')  # Valeur par défaut: "en"

    # Sélection du modèle en fonction de la langue
    if lang == 'en':
        model_path = "/models/en_US-lessac-medium.onnx"
        config_path = "/models/en_US-lessac-medium.json"
    elif lang == 'fr':
        model_path = "/models/fr/fr_FR-tom-med.onnx"
        config_path = "/models/fr/fr_FR-tom-med.json"
    elif lang == 'el':
        model_path = "/models/el/el_GR-rapunzelina-low.onnx"
        config_path = "/models/el/el_GR-rapunzelina-low.json"

    elif lang == 'tr':
        model_path = "/models/tr/tr_TR-fettah-medium.onnx"
        config_path = "/models/tr/tr_TR-fettah-medium.json"
    else:
        return {'error': f"Unsupported language: {lang}"}, 400

    # Créer un fichier temporaire pour l'audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name

    try:
        app.logger.debug(f"Trying to process text: {text} (lang={lang})")
        # Appel à Piper en précisant le modèle ONNX et son fichier JSON
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

        # Retourner le fichier WAV généré
        return send_file(output_path, mimetype='audio/wav')

    except subprocess.CalledProcessError as e:
        # Log l'erreur Piper en stderr
        app.logger.error(f"Piper error: {e.stderr.decode()}")
        return {'error': f'Piper error: {e.stderr.decode()}'}, 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return {'error': f'Unexpected error: {str(e)}'}, 500
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
