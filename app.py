import os
import tempfile
import logging
import wave
from functools import wraps
from flask import Flask, request, jsonify, send_file
from piper import PiperVoice, SynthesisConfig

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

MAX_TEXT_LENGTH = 5000
MAX_SEGMENTS = 20
LENGTH_SCALE_MIN = 0.1
LENGTH_SCALE_MAX = 5.0

if "ACCESS_TOKEN" not in os.environ:
    raise RuntimeError("The ACCESS_TOKEN environment variable is required but was not set.")

ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

tempfile.tempdir = '/tmp/piper'

# Voice cache to avoid reloading models
voice_cache = {}

MODELS_CONFIG = {
    'en': '/models/en_US-lessac-medium.onnx',
    'fr': '/models/fr_FR-upmc-medium.onnx',
    'el': '/models/el_GR-chreece-high.onnx',
    'tr': '/models/tr_TR-dfki-medium.onnx',
    'de': '/models/de_DE-thorsten-medium.onnx',
    'es': '/models/es_ES-davefx-medium.onnx',
    'it': '/models/it_IT-paola-medium.onnx',
}


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ")[1]
        if token != ACCESS_TOKEN:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


def parse_length_scale(value):
    try:
        length_scale = float(value)
    except (TypeError, ValueError):
        return None, 'length_scale must be a number'
    if not LENGTH_SCALE_MIN <= length_scale <= LENGTH_SCALE_MAX:
        return None, f'length_scale must be between {LENGTH_SCALE_MIN} and {LENGTH_SCALE_MAX}'
    return length_scale, None


def get_voice(model_path):
    if model_path not in voice_cache:
        app.logger.debug(f"Loading voice model: {model_path}")
        voice_cache[model_path] = PiperVoice.load(model_path)
    return voice_cache[model_path]


@app.route('/tts', methods=['POST'])
@require_auth
def tts():
    """
    TTS endpoint.
    Receives a JSON {"text": "...", "lang": "...", "length_scale": 1.0} and returns a WAV audio file.
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']
    lang = data.get('lang', 'en')

    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'Text too long (max {MAX_TEXT_LENGTH} characters)'}), 400

    length_scale, err = parse_length_scale(data.get('length_scale', 1.0))
    if err is not None:
        return jsonify({'error': err}), 400

    if lang not in MODELS_CONFIG:
        return jsonify({'error': f'Unsupported language: {lang}'}), 400

    model_path = MODELS_CONFIG[lang]

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name

    try:
        app.logger.debug(f"Processing TTS request (lang={lang}, length_scale={length_scale}, text_len={len(text)})")

        voice = get_voice(model_path)

        syn_config = SynthesisConfig(length_scale=length_scale)
        with wave.open(output_path, 'wb') as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)

        app.logger.debug("Piper generation completed successfully")

        return send_file(output_path, mimetype='audio/wav')

    except Exception as e:
        app.logger.error(f"TTS error: {e}")
        return jsonify({'error': 'Internal synthesis error'}), 500
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


@app.route('/polyglot', methods=['POST'])
@require_auth
def polyglot():
    """
    Multilingual TTS endpoint for generating speech with multiple languages.

    Generates a single WAV file from multiple text segments, each with its own language.
    Useful for phrases mixing languages, like: "Tu dis Γεια σας pour saluer."

    Request:
        POST /polyglot
        Headers:
            Authorization: Bearer <token>
            Content-Type: application/json
        Body:
            {
                "segments": [
                    {"text": "Tu dis ", "lang": "fr"},
                    {"text": "Γεια σας", "lang": "el", "length_scale": 1.2},
                    {"text": " pour saluer.", "lang": "fr"}
                ]
            }

    Supported languages: en, fr, el, tr, de, es, it

    Response:
        200: audio/wav file
        400: Invalid request (missing segments, invalid lang)
        401: Missing or invalid token
        500: Server error
    """
    data = request.get_json()
    if not data or 'segments' not in data:
        return jsonify({'error': 'No segments provided'}), 400

    segments = data['segments']
    if not isinstance(segments, list) or len(segments) == 0:
        return jsonify({'error': 'Segments must be a non-empty array'}), 400

    if len(segments) > MAX_SEGMENTS:
        return jsonify({'error': f'Too many segments (max {MAX_SEGMENTS})'}), 400

    temp_files = []
    output_path = None
    reference_params = None

    try:
        for i, segment in enumerate(segments):
            if 'text' not in segment or 'lang' not in segment:
                return jsonify({'error': f'Segment {i} missing text or lang'}), 400

            text = segment['text']
            lang = segment['lang']

            if len(text) > MAX_TEXT_LENGTH:
                return jsonify({'error': f'Segment {i} text too long (max {MAX_TEXT_LENGTH} characters)'}), 400

            length_scale, err = parse_length_scale(segment.get('length_scale', 1.0))
            if err is not None:
                return jsonify({'error': err}), 400

            if lang not in MODELS_CONFIG:
                return jsonify({'error': f'Unsupported language: {lang}'}), 400

            model_path = MODELS_CONFIG[lang]
            voice = get_voice(model_path)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
                temp_path = tf.name
            temp_files.append(temp_path)

            syn_config = SynthesisConfig(length_scale=length_scale)
            with wave.open(temp_path, 'wb') as wav_file:
                voice.synthesize_wav(text, wav_file, syn_config=syn_config)

            with wave.open(temp_path, 'rb') as wav_file:
                params = wav_file.getparams()
                if reference_params is None:
                    reference_params = params
                elif (params.nchannels != reference_params.nchannels or
                      params.sampwidth != reference_params.sampwidth or
                      params.framerate != reference_params.framerate):
                    return jsonify({'error': f'Segment {i} has incompatible audio parameters'}), 500

            app.logger.debug(f"Generated segment {i} (lang={lang}, length_scale={length_scale})")

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
            output_path = tf.name

        with wave.open(output_path, 'wb') as output_wav:
            output_wav.setparams(reference_params)
            for temp_file in temp_files:
                with wave.open(temp_file, 'rb') as segment_wav:
                    output_wav.writeframes(segment_wav.readframes(segment_wav.getnframes()))

        app.logger.debug(f"Concatenated {len(temp_files)} segments")

        return send_file(output_path, mimetype='audio/wav')

    except Exception as e:
        app.logger.error(f"Polyglot error: {e}")
        return jsonify({'error': 'Internal synthesis error'}), 500

    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
