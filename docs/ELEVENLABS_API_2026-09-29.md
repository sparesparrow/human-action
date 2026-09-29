# ElevenLabs API notes — 2026-09-29

This project targets the current stable ElevenLabs Python SDK release available on
2026-09-29: **2.69.0** (released 2026-09-24). The SDK's development branch may
already report a newer unreleased version, so production dependencies intentionally
stay on the stable 2.x line.

## Sources reviewed

- PyPI stable SDK: https://pypi.org/project/elevenlabs/2.69.0/
- Python SDK repository: https://github.com/elevenlabs/elevenlabs-python
- Create Speech API: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- Request Stitching: https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching
- Text-to-Speech product guide: https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech
- Audiobooks product guide: https://elevenlabs.io/docs/eleven-creative/products/audiobooks
- API input limits: https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/whats-the-maximum-amount-of-characters-and-text-i-can-generate

## Python SDK shape used here

The supported synchronous client shape is:

```python
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="...")
audio = client.text_to_speech.convert(
    voice_id="...",
    text="...",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    voice_settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        speed=1.0,
        use_speaker_boost=True,
    ),
)
```

`convert()` returns an iterator of audio byte chunks. For long-form generation,
the SDK exposes `client.text_to_speech.with_raw_response.convert(...)`, whose
response provides both the audio iterator and headers such as `request-id` and
`character-cost`.

## Long-form audiobook decisions

- Keep `eleven_multilingual_v2` as the default audiobook model. ElevenLabs
  recommends Multilingual v2 for high-quality long-form narration/audiobooks.
- Multilingual v2 accepts up to 10,000 input characters per API request. This repo's
  existing chunk size (5,000 characters) remains comfortably inside that limit.
- Generate audiobook chunks sequentially and pass up to the three latest
  `previous_request_ids` to reduce abrupt prosody changes between chunks.
- Request IDs used for stitching should be fresh (ElevenLabs documents a two-hour
  window). When resuming after existing audio, this project falls back to
  `previous_text` continuity instead of relying on stale request IDs.
- Request stitching is not available for `eleven_v3`; the implementation
  disables request-ID stitching automatically for that model.
- Keep the conservative voice settings already used by the project:
  stability 0.5, similarity 0.75, style 0, speed 1.0, speaker boost enabled.
- Save a JSON generation manifest with output paths, response request IDs,
  character-cost headers, byte counts, and failures. This makes paid generation
  auditable and resumable.
- Skip non-empty output files by default to avoid accidental duplicate API spend.

## Running ElevenLabs generation

```bash
export ELEVENLABS_API_KEY="..."
python main.py --stage audio-gen --tts-engine elevenlabs
```

The API key is never committed. CI uses mocked SDK clients and does not make paid
ElevenLabs requests.
