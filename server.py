import base64
import json
import os
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from home import Home, TOOLS, parse_calls

ROOT = Path(__file__).parent
MODEL = os.environ.get('LIQUID_MODEL', 'LiquidAI/LFM3-Audio-2B-MLX-8bit')
app = FastAPI()
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
home = Home()
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=1)
model = processor = None
status = {'state': 'not loaded', 'detail': 'The model loads on the first request.'}

class Action(BaseModel):
    name: str
    arguments: dict

class TextRequest(BaseModel):
    text: str
    speak: bool = True

def load_model():
    global model, processor
    if model is None:
        status.update(state='loading', detail='Loading the local model…')
        from mlx_vlm import load
        model, processor = load(MODEL)
        status.update(state='ready', detail='Running locally with Apple MLX')

def generate_text(messages, tools=None, audio=None, max_tokens=256):
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    prompt = apply_chat_template(processor, model.config, messages, num_audios=1 if audio else 0, **({'tools': tools} if tools else {}))
    return generate(model, processor, prompt, audio=audio, max_tokens=max_tokens, temperature=0, suppress_mixed=True, suppress_audio_out=True).text.strip()

def transcribe(path):
    return generate_text([{'role': 'system', 'content': 'Perform ASR in English.'}, {'role': 'user', 'content': ''}], audio=path)

def speak_text(text):
    from mlx_vlm.generate.audio import generate_audio
    from mlx_vlm.prompt_utils import apply_chat_template
    messages = [{'role': 'system', 'content': 'Perform TTS in American English using a female voice.'}, {'role': 'user', 'content': text}]
    prompt = apply_chat_template(processor, model.config, messages, use_tts_template=True)
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / 'reply.wav')
        generate_audio(model, processor, prompt, output_audio_path=path, max_tokens=512)
        return base64.b64encode(Path(path).read_bytes()).decode('ascii')

def run_turn(text=None, audio_data=None, speak=True):
    try:
        load_model()
        if audio_data is not None:
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'recording'
                wav = Path(directory) / 'input.wav'
                source.write_bytes(audio_data)
                subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', str(source), '-ac', '1', '-ar', '16000', str(wav)], check=True, timeout=30, capture_output=True)
                text = transcribe(str(wav))
        if not text or not text.strip():
            raise ValueError('No speech was detected. Please try again.')
        text = text.strip()[:2000]
        with lock:
            current = home.snapshot()
        system = 'You control a simulated home. Do not claim a device changed unless a tool confirms it. Be concise. Current state: ' + json.dumps(current) + '\n\nList of tools:'
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': text}]
        events = []
        answer = ''
        for _ in range(3):
            output = generate_text(messages, TOOLS)
            calls = parse_calls(output)
            if not calls:
                answer = output
                break
            results = []
            for call in calls[:6]:
                try:
                    with lock:
                        state = home.apply(call['name'], call['arguments'])
                    result = {'ok': True, 'state': state}
                except ValueError as exc:
                    result = {'ok': False, 'error': str(exc)}
                events.append({**call, **result})
                results.append(result)
            messages += [{'role': 'assistant', 'tool_calls': [{'type': 'function', 'function': call} for call in calls[:6]]}, {'role': 'tool', 'content': json.dumps(results)}]
        if not answer:
            answer = 'Actions were processed. Check the activity log for details.' if events else 'I could not complete that request. Please try again.'
        audio_reply = None
        speech_error = None
        if speak:
            try:
                audio_reply = speak_text(answer)
            except Exception as exc:
                speech_error = str(exc)
        with lock:
            state = home.snapshot()
        return {'text': text, 'answer': answer, 'events': events, 'state': state, 'audio': audio_reply, 'speech_error': speech_error}
    except Exception as exc:
        if model is None:
            status.update(state='error', detail=str(exc))
        raise

@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')

@app.get('/api/state')
def get_state():
    with lock:
        return {'state': home.snapshot(), 'model': dict(status)}

@app.post('/api/action')
def action(request: Action):
    try:
        with lock:
            return {'state': home.apply(request.name, request.arguments)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/chat')
def chat(request: TextRequest):
    if not request.text.strip() or len(request.text) > 2000:
        raise HTTPException(400, 'Enter a message of up to 2000 characters')
    try:
        return executor.submit(run_turn, request.text, None, request.speak).result()
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.post('/api/voice')
async def voice(file: UploadFile = File(...), speak: bool = True):
    data = await file.read(15_000_001)
    if not data or len(data) > 15_000_000:
        raise HTTPException(400, 'Recording must be between 1 byte and 15 MB')
    try:
        import asyncio
        return await asyncio.wrap_future(executor.submit(run_turn, None, data, speak))
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
