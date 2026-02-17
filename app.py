import os
import tempfile
import logging
import wave
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from piper import PiperVoice, SynthesisConfig

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)

if "ACCESS_TOKEN" not in os.environ:
    raise RuntimeError("The ACCESS_TOKEN environment variable is required but was not set.")

ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

tempfile.tempdir = '/tmp/piper'

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

SUPPORTED_LANGS = set(MODELS_CONFIG.keys())

security = HTTPBearer()


@asynccontextmanager
async def lifespan(app):
    os.makedirs('/tmp/piper', exist_ok=True)
    yield


app = FastAPI(lifespan=lifespan)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_voice(model_path: str) -> PiperVoice:
    if model_path not in voice_cache:
        logger.debug(f"Loading voice model: {model_path}")
        voice_cache[model_path] = PiperVoice.load(model_path)
    return voice_cache[model_path]


class TTSRequest(BaseModel):
    text: str = Field(max_length=5000)
    lang: str = "en"
    length_scale: float = Field(default=1.0, ge=0.1, le=5.0)


class Segment(BaseModel):
    text: str = Field(max_length=5000)
    lang: str
    length_scale: float = Field(default=1.0, ge=0.1, le=5.0)


class PolyglotRequest(BaseModel):
    segments: list[Segment] = Field(min_length=1, max_length=20)


def cleanup_file(path: str):
    if os.path.exists(path):
        os.unlink(path)


def cleanup_files(paths: list[str]):
    for path in paths:
        if os.path.exists(path):
            os.unlink(path)


@app.post('/tts')
def tts(body: TTSRequest, _=Depends(verify_token)):
    if body.lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.lang}")

    model_path = MODELS_CONFIG[body.lang]

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name

    try:
        logger.debug(f"Processing TTS request (lang={body.lang}, length_scale={body.length_scale}, text_len={len(body.text)})")

        voice = get_voice(model_path)
        syn_config = SynthesisConfig(length_scale=body.length_scale)
        with wave.open(output_path, 'wb') as wav_file:
            voice.synthesize_wav(body.text, wav_file, syn_config=syn_config)

        logger.debug("Piper generation completed successfully")

        return FileResponse(
            output_path,
            media_type='audio/wav',
            background=BackgroundTask(cleanup_file, output_path),
        )
    except Exception as e:
        cleanup_file(output_path)
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail="Internal synthesis error")


@app.post('/polyglot')
def polyglot(body: PolyglotRequest, _=Depends(verify_token)):
    for i, segment in enumerate(body.segments):
        if segment.lang not in SUPPORTED_LANGS:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {segment.lang}")

    temp_files = []
    output_path = None
    reference_params = None

    try:
        for i, segment in enumerate(body.segments):
            model_path = MODELS_CONFIG[segment.lang]
            voice = get_voice(model_path)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
                temp_path = tf.name
            temp_files.append(temp_path)

            syn_config = SynthesisConfig(length_scale=segment.length_scale)
            with wave.open(temp_path, 'wb') as wav_file:
                voice.synthesize_wav(segment.text, wav_file, syn_config=syn_config)

            with wave.open(temp_path, 'rb') as wav_file:
                params = wav_file.getparams()
                if reference_params is None:
                    reference_params = params
                elif (params.nchannels != reference_params.nchannels or
                      params.sampwidth != reference_params.sampwidth or
                      params.framerate != reference_params.framerate):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Segment {i} has incompatible audio parameters",
                    )

            logger.debug(f"Generated segment {i} (lang={segment.lang}, length_scale={segment.length_scale})")

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
            output_path = tf.name

        with wave.open(output_path, 'wb') as output_wav:
            output_wav.setparams(reference_params)
            for temp_file in temp_files:
                with wave.open(temp_file, 'rb') as segment_wav:
                    output_wav.writeframes(segment_wav.readframes(segment_wav.getnframes()))

        logger.debug(f"Concatenated {len(temp_files)} segments")

        all_files = temp_files + [output_path]
        return FileResponse(
            output_path,
            media_type='audio/wav',
            background=BackgroundTask(cleanup_files, all_files),
        )
    except HTTPException:
        cleanup_files(temp_files)
        if output_path:
            cleanup_file(output_path)
        raise
    except Exception as e:
        cleanup_files(temp_files)
        if output_path:
            cleanup_file(output_path)
        logger.error(f"Polyglot error: {e}")
        raise HTTPException(status_code=500, detail="Internal synthesis error")


@app.get('/health')
def health():
    return {'status': 'ok'}
