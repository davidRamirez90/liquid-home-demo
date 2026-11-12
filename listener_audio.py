"""Audio helpers for the always-on listener."""
import io
import wave

RATE = 16000
FRAME_SAMPLES = 1280  # 80 ms
FRAME_BYTES = FRAME_SAMPLES * 2

def pcm_to_wav(pcm):
    if not pcm or len(pcm) % 2:
        raise ValueError('Expected nonempty 16-bit PCM')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm)
    return buffer.getvalue()
