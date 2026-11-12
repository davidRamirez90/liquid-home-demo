"""Local menu-bar wake-word listener. Never opens the microphone on import."""
import base64
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from listener_audio import FRAME_BYTES, FRAME_SAMPLES, RATE, pcm_to_wav
from listener_capture import Capture

API = 'http://127.0.0.1:8765'
WAKE_THRESHOLD = float(os.environ.get('HAVEN_WAKE_THRESHOLD', '0.5'))


def check_server():
    with urllib.request.urlopen(API + '/api/state', timeout=3) as response:
        return json.load(response)


def submit_audio(pcm):
    boundary = 'haven-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="command.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + pcm_to_wav(pcm) + f'\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(API + '/api/voice?speak=true', data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def voiced(vad, frame):
    # WebRTC VAD accepts 10, 20 or 30 ms frames, not 80 ms.
    decisions = [vad.is_speech(frame[i:i + 640], RATE) for i in range(0, len(frame), 640)]
    return any(decisions)


class Listener:
    def __init__(self):
        self.enabled = threading.Event()
        self.quit_event = threading.Event()
        self.enabled.set()
        self.lock = threading.Lock()
        self.status = 'Starting…'
        self.detail = 'Say “Hey Jarvis”'
        self.playback = None
        self.generation = 0
        self.thread = threading.Thread(target=self.run, daemon=True)

    def update(self, status, detail=None):
        with self.lock:
            self.status = status
            if detail is not None:
                self.detail = detail
        print(f'[Haven] {status}' + (f' — {detail}' if detail else ''), flush=True)

    def snapshot(self):
        with self.lock:
            return self.status, self.detail

    def session_token(self):
        with self.lock:
            return self.generation

    def is_current(self, token):
        with self.lock:
            return token == self.generation and self.enabled.is_set() and not self.quit_event.is_set()

    def pause(self):
        with self.lock:
            self.enabled.clear()
            self.generation += 1
            player = self.playback
        if player and player.poll() is None:
            player.terminate()
        self.update('Paused', 'Microphone is closed; an already-sent request may finish.')

    def resume(self):
        self.enabled.set()
        self.update('Starting…', 'Say “Hey Jarvis”')

    def close(self):
        self.quit_event.set()
        self.pause()

    def play(self, encoded, token):
        if not encoded or not self.is_current(token):
            return
        audio = base64.b64decode(encoded, validate=True)
        with self.lock:
            if token != self.generation or not self.enabled.is_set() or self.quit_event.is_set():
                return
            self.playback = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'error', '-i', 'pipe:0'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            player = self.playback
        try:
            _, err = player.communicate(input=audio, timeout=60)
            if player.returncode and self.is_current(token):
                raise RuntimeError('Audio playback failed: ' + err.decode(errors='replace')[:200])
        finally:
            with self.lock:
                self.playback = None

    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
            import webrtcvad
            import openwakeword
            from openwakeword.model import Model
            model_path = Path(openwakeword.__file__).parent / 'resources/models/hey_jarvis_v0.1.onnx'
            if not model_path.exists():
                raise RuntimeError('Wake model missing. Run ./setup-listener.sh')
            detector = Model(wakeword_models=[str(model_path)], inference_framework='onnx')
            vad = webrtcvad.Vad(2)
        except Exception as exc:
            self.enabled.clear()
            self.update('Error', str(exc))
            return
        while not self.quit_event.is_set():
            if not self.enabled.wait(.2):
                continue
            token = self.session_token()
            try:
                check_server()
                if not self.is_current(token):
                    continue
                capture = Capture()
                detector.reset()
                pcm = None
                self.update('Starting…', 'Opening microphone…')
                with sd.RawInputStream(samplerate=RATE, blocksize=FRAME_SAMPLES, channels=1, dtype='int16') as stream:
                    if self.is_current(token):
                        self.update('Listening', 'Say “Hey Jarvis”')
                    while self.is_current(token):
                        frame, overflowed = stream.read(FRAME_SAMPLES)
                        frame = bytes(frame)
                        if not self.is_current(token):
                            break
                        if overflowed or len(frame) != FRAME_BYTES:
                            capture.reset()
                            detector.reset()
                            continue
                        was_recording = capture.recording
                        score = 0.0 if was_recording else max(detector.predict(np.frombuffer(frame, dtype=np.int16)).values(), default=0.0)
                        pcm = capture.feed(frame, score >= WAKE_THRESHOLD, voiced(vad, frame) if was_recording else False)
                        if not was_recording and capture.recording:
                            self.update('Recording', 'Listening for your request…')
                        elif was_recording and not capture.recording and pcm is None:
                            detector.reset()
                            self.update('Listening', 'No request heard. Say “Hey Jarvis”')
                        if pcm is not None:
                            break
                # Microphone is closed during inference and playback.
                if pcm is None or not self.is_current(token):
                    continue
                self.update('Thinking', 'Microphone closed while processing')
                result = submit_audio(pcm)
                del pcm
                if not self.is_current(token):
                    continue
                print('[You]', result.get('text', ''), flush=True)
                print('[Haven]', result.get('answer', ''), flush=True)
                for event in result.get('events', []):
                    print('[Tool]', json.dumps(event, ensure_ascii=False), flush=True)
                self.update('Speaking', result.get('answer', '')[:100])
                self.play(result.get('audio'), token)
                if self.is_current(token) and result.get('speech_error'):
                    self.update('Voice error', result['speech_error'][:120])
                    time.sleep(2)
            except Exception as exc:
                if self.quit_event.is_set():
                    break
                if self.is_current(token):
                    self.enabled.clear()
                    self.update('Error', str(exc)[:160] + ' — check server, microphone permissions, then Resume.')


def main():
    import rumps
    class HavenApp(rumps.App):
        def __init__(self):
            super().__init__('Haven', title='◉ Haven', quit_button=None)
            self.listener = Listener()
            self.status_item = rumps.MenuItem('Starting…', callback=None)
            self.detail_item = rumps.MenuItem('Say “Hey Jarvis”', callback=None)
            self.toggle_item = rumps.MenuItem('Pause listening', callback=self.toggle)
            self.menu = [self.status_item, self.detail_item, None, self.toggle_item, rumps.MenuItem('Quit Haven Listener', callback=self.quit_app)]
            self.timer = rumps.Timer(self.refresh, .5)
            self.timer.start()
            self.listener.thread.start()

        def toggle(self, _):
            if self.listener.enabled.is_set():
                self.listener.pause()
            else:
                if not self.listener.thread.is_alive():
                    self.listener = Listener()
                    self.listener.thread.start()
                else:
                    self.listener.resume()

        def refresh(self, _):
            status, detail = self.listener.snapshot()
            self.title = ('◉ ' if status in ('Listening', 'Recording') else '○ ') + 'Haven'
            self.status_item.title = status
            self.detail_item.title = detail
            self.toggle_item.title = 'Pause listening' if self.listener.enabled.is_set() else 'Resume listening'

        def quit_app(self, _):
            self.listener.close()
            rumps.quit_application()
    HavenApp().run()

if __name__ == '__main__':
    main()
