# Piper TTS API

REST API for text-to-speech synthesis using [Piper](https://github.com/OHF-Voice/piper1-gpl).

## Quick Start (Docker)

```bash
docker compose up -d
```

## Configuration

| Variable | Description | Required |
|---|---|---|
| `ACCESS_TOKEN` | Bearer token for API authentication | Yes |

## API

### `POST /tts`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | — | Text to synthesize (required) |
| `lang` | string | `en` | Language code |
| `length_scale` | float | `1.0` | Speech speed: `< 1.0` = faster, `> 1.0` = slower (range: 0.1–5.0) |

**Supported languages:**

| Code | Language | Model |
|---|---|---|
| `en` | English | `en_US-lessac-medium` |
| `fr` | French | `fr_FR-upmc-medium` |
| `de` | German | `de_DE-thorsten-medium` |
| `es` | Spanish | `es_ES-davefx-medium` |
| `it` | Italian | `it_IT-paola-medium` |
| `el` | Greek | `el_GR-chreece-high` |
| `tr` | Turkish | `tr_TR-dfki-medium` |

**Response:** `audio/wav`

### Examples

```bash
# Basic
curl -X POST http://localhost:5000/tts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "lang": "en"}' \
  --output audio.wav

# Slower speech
curl -X POST http://localhost:5000/tts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour le monde", "lang": "fr", "length_scale": 1.3}' \
  --output audio.wav
```

## Development

```bash
# Run locally
export ACCESS_TOKEN="your_token"
python app.py

# Build Docker image
docker build -t piper .
```

## Troubleshooting

- **First request is slow:** normal, the voice model is loaded on first use then cached
- **API returns 401:** check your `ACCESS_TOKEN` env variable and `Authorization` header
- **Unsupported language error:** verify the `lang` code is in the supported list above
