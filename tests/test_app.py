import os
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest

# Ensure temp dir exists before importing app
os.makedirs('/tmp/piper', exist_ok=True)

# Mock piper before importing app
mock_piper = MagicMock()
mock_voice = MagicMock()


def fake_synthesize_wav(text, wav_file, syn_config=None):
    """Generate a minimal valid WAV content."""
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(22050)
    frames = struct.pack('<' + 'h' * 100, *([0] * 100))
    wav_file.writeframes(frames)


mock_voice.synthesize_wav.side_effect = fake_synthesize_wav

with patch.dict('os.environ', {'ACCESS_TOKEN': 'test-token', 'LOG_LEVEL': 'DEBUG'}):
    with patch.dict('sys.modules', {'piper': mock_piper}):
        mock_piper.PiperVoice = MagicMock()
        mock_piper.PiperVoice.load.return_value = mock_voice
        mock_piper.SynthesisConfig = MagicMock()
        from app import app

from fastapi.testclient import TestClient

TOKEN = 'test-token'
AUTH = {'Authorization': f'Bearer {TOKEN}'}


@pytest.fixture
def client():
    return TestClient(app)


# --- Auth tests ---

class TestAuth:
    def test_missing_auth_header(self, client):
        resp = client.post('/tts', json={'text': 'hello'})
        assert resp.status_code in (401, 403)

    def test_invalid_token(self, client):
        resp = client.post('/tts', json={'text': 'hello'},
                           headers={'Authorization': 'Bearer wrong'})
        assert resp.status_code == 401

    def test_malformed_auth_header(self, client):
        resp = client.post('/tts', json={'text': 'hello'},
                           headers={'Authorization': 'Basic abc'})
        assert resp.status_code in (401, 403)


# --- Health check ---

class TestHealth:
    def test_health(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}


# --- TTS endpoint ---

class TestTTS:
    def test_no_text(self, client):
        resp = client.post('/tts', json={}, headers=AUTH)
        assert resp.status_code == 422

    def test_unsupported_lang(self, client):
        resp = client.post('/tts', json={'text': 'hello', 'lang': 'xx'}, headers=AUTH)
        assert resp.status_code == 400
        assert 'Unsupported language' in resp.json()['detail']

    def test_text_too_long(self, client):
        resp = client.post('/tts', json={'text': 'a' * 5001}, headers=AUTH)
        assert resp.status_code == 422

    def test_invalid_length_scale_type(self, client):
        resp = client.post('/tts', json={'text': 'hello', 'length_scale': 'abc'}, headers=AUTH)
        assert resp.status_code == 422

    def test_length_scale_out_of_range(self, client):
        resp = client.post('/tts', json={'text': 'hello', 'length_scale': 10.0}, headers=AUTH)
        assert resp.status_code == 422

    def test_success(self, client):
        resp = client.post('/tts', json={'text': 'hello', 'lang': 'en'}, headers=AUTH)
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'audio/wav'

    def test_default_lang_is_en(self, client):
        resp = client.post('/tts', json={'text': 'hello'}, headers=AUTH)
        assert resp.status_code == 200

    def test_with_length_scale(self, client):
        resp = client.post('/tts', json={'text': 'hello', 'length_scale': 1.5}, headers=AUTH)
        assert resp.status_code == 200


# --- Polyglot endpoint ---

class TestPolyglot:
    def test_no_segments(self, client):
        resp = client.post('/polyglot', json={}, headers=AUTH)
        assert resp.status_code == 422

    def test_empty_segments(self, client):
        resp = client.post('/polyglot', json={'segments': []}, headers=AUTH)
        assert resp.status_code == 422

    def test_too_many_segments(self, client):
        segments = [{'text': 'hi', 'lang': 'en'}] * 21
        resp = client.post('/polyglot', json={'segments': segments}, headers=AUTH)
        assert resp.status_code == 422

    def test_segment_missing_text(self, client):
        resp = client.post('/polyglot', json={'segments': [{'lang': 'en'}]}, headers=AUTH)
        assert resp.status_code == 422

    def test_segment_missing_lang(self, client):
        resp = client.post('/polyglot', json={'segments': [{'text': 'hi'}]}, headers=AUTH)
        assert resp.status_code == 422

    def test_segment_text_too_long(self, client):
        segments = [{'text': 'a' * 5001, 'lang': 'en'}]
        resp = client.post('/polyglot', json={'segments': segments}, headers=AUTH)
        assert resp.status_code == 422

    def test_segment_unsupported_lang(self, client):
        segments = [{'text': 'hi', 'lang': 'xx'}]
        resp = client.post('/polyglot', json={'segments': segments}, headers=AUTH)
        assert resp.status_code == 400

    def test_success(self, client):
        segments = [
            {'text': 'hello', 'lang': 'en'},
            {'text': 'bonjour', 'lang': 'fr'},
        ]
        resp = client.post('/polyglot', json={'segments': segments}, headers=AUTH)
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'audio/wav'

    def test_with_length_scale(self, client):
        segments = [{'text': 'hello', 'lang': 'en', 'length_scale': 1.2}]
        resp = client.post('/polyglot', json={'segments': segments}, headers=AUTH)
        assert resp.status_code == 200
