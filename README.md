# Piper TTS API

REST API for text-to-speech synthesis using [Piper](https://github.com/OHF-Voice/piper1-gpl), built with FastAPI.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your ACCESS_TOKEN
docker compose up -d
```

The API documentation is available at `http://localhost:5000/docs`.

## Configuration

| Variable | Description | Default | Required |
|---|---|---|---|
| `ACCESS_TOKEN` | Bearer token for API authentication | — | Yes |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | No |

## API

All endpoints (except `/health`) require a Bearer token:

```
Authorization: Bearer <token>
```

### `POST /tts`

Generate speech from text in a single language.

**Body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | — | Text to synthesize (required, max 5000 chars) |
| `lang` | string | `en` | Language code |
| `length_scale` | float | `1.0` | Speech speed: `< 1.0` = faster, `> 1.0` = slower (range: 0.1–5.0) |

**Response:** `audio/wav`

**Example:**

```bash
curl -X POST http://localhost:5000/tts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "lang": "en"}' \
  --output audio.wav
```

### `POST /polyglot`

Generate speech from multiple text segments, each with its own language. Useful for multilingual phrases.

**Body:**

| Field | Type | Description |
|---|---|---|
| `segments` | array | List of segments (1–20) |
| `segments[].text` | string | Text to synthesize (required, max 5000 chars) |
| `segments[].lang` | string | Language code (required) |
| `segments[].length_scale` | float | Speech speed (default: 1.0, range: 0.1–5.0) |

**Response:** `audio/wav` (concatenated segments)

**Example:**

```bash
curl -X POST http://localhost:5000/polyglot \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "segments": [
      {"text": "Tu dis ", "lang": "fr"},
      {"text": "Γεια σας", "lang": "el", "length_scale": 1.2},
      {"text": " pour saluer.", "lang": "fr"}
    ]
  }' \
  --output audio.wav
```

### `GET /health`

Health check endpoint (no authentication required).

**Response:** `{"status": "ok"}`

## Supported Languages

| Code | Language | Model |
|---|---|---|
| `en` | English | `en_US-lessac-medium` |
| `fr` | French | `fr_FR-upmc-medium` |
| `de` | German | `de_DE-thorsten-medium` |
| `es` | Spanish | `es_ES-davefx-medium` |
| `it` | Italian | `it_IT-paola-medium` |
| `el` | Greek | `el_GR-chreece-high` |
| `tr` | Turkish | `tr_TR-dfki-medium` |

## Development

```bash
# Build and run
docker compose up -d --build

# Run tests
docker run --rm -v $(pwd):/app -w /app python:3.13-slim-bookworm \
  bash -c "pip install -q uv && uv pip install --system --no-cache '.[dev]' && pytest tests/ -v"
```

## Troubleshooting

- **First request is slow:** normal, the voice model is loaded on first use then cached
- **401 Unauthorized:** check your `ACCESS_TOKEN` in `.env` and `Authorization` header
- **422 Validation Error:** check request body matches the expected schema (see `/docs`)
- **Unsupported language:** verify the `lang` code is in the supported list above
