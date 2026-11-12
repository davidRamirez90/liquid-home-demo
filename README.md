# Haven — local voice home demo

A simulated smart home you can talk to. Liquid AI's **LFM3-Audio-2B** runs on your Apple Silicon Mac with MLX: it transcribes your recording, chooses mock tools, responds in text, and synthesizes a spoken reply. The browser shows each requested tool call and whether it succeeded. The lights, music, thermostat and scenes are entirely simulated: no smart-home services or devices are connected.

## Start

Requires an Apple Silicon Mac, Python 3.10+ (3.12 recommended), [uv](https://docs.astral.sh/uv/) and `ffmpeg`. Model weights are downloaded separately and are not included in this repository.

```sh
git clone https://github.com/davidRamirez90/liquid-home-demo.git
cd liquid-home-demo
./start.sh
```

Open **http://127.0.0.1:8765**. Click **Talk to Haven**, allow microphone access, speak, then click **Stop recording**. You can also type or use the device controls. Turn off **Voice reply** for faster responses.

On first setup, `start.sh` creates a virtual environment and installs packages. The first inference downloads [LiquidAI/LFM3-Audio-2B-MLX-8bit](https://huggingface.co/LiquidAI/LFM3-Audio-2B-MLX-8bit) from Hugging Face (several GB); see that page for its license. Allow some time for the first model load. To use another compatible MLX model, set `LIQUID_MODEL` before starting. Install ffmpeg with `brew install ffmpeg` if needed.

Try:
- “Turn off the kitchen lights.”
- “Dim the living room lights to 30 percent.”
- “Play jazz at volume 35.”
- “Set the temperature to 22 degrees.”
- “Activate the relax scene.”

## Optional: always-on wake-word listener (macOS)

This is a separate menu-bar process; it does **not** start automatically with the web server. Say **“Hey Jarvis”**, then immediately give a command. This is openWakeWord's pre-trained English wake phrase—not a custom “Hey Haven” model.

Run `./setup-listener.sh` to install the listener dependencies and download the wake models, including after clearing those model files. Then use two terminals:

```sh
# Terminal 1: simulated home backend
./start.sh

# Terminal 2: native menu-bar listener
./listen.sh
```

Approve the macOS microphone permission prompt for the launching application if asked. Click **Haven** in the menu bar to see its status, pause/resume listening, or quit. When paused, the microphone stream closes and buffered audio is discarded. The listener checks the local server before opening the microphone; if the server or microphone is unavailable, fix the problem and select **Resume listening**. Listener transcripts and tool results are printed in Terminal; the web dashboard reflects device state, but its tab-local activity log does not receive listener events.

The wake detector processes 80 ms audio frames locally. It retains about one second of audio in a rolling in-memory buffer; on a wake, it collects speech until 1.2 seconds of silence, or a maximum of about 15 seconds. If no post-wake speech is detected within six seconds, it discards the capture. Only a captured request is sent to the local backend. The microphone closes during inference and reply playback to avoid the assistant waking itself; interruption and wake-free follow-ups are not implemented. Pausing cannot undo a request already submitted to the backend. The Mac must be awake; this is not a launch-at-login service.

To tune sensitivity, run `HAVEN_WAKE_THRESHOLD=0.5 ./listen.sh` (lower detects more but may false-trigger). Test in your own room. A wake word is **not authentication**; this demo must not be used to control security-sensitive real devices. The bundled pre-trained wake-word models are licensed [CC BY-NC-SA 4.0](https://github.com/dscripka/openWakeWord#license), which restricts commercial use; review licensing before using them in a product.

## How it works

The server binds to localhost. Audio is recorded in the browser, converted to WAV with ffmpeg, transcribed by LFM3, and passed back to the same model with function schemas and the current simulated state. Tool arguments are validated before modifying in-memory state. The model receives tool results and generates a response, which LFM3 can synthesize as speech. Model inference is serialized; requests can take a while. The activity feed is per browser tab and resets on reload; device state resets when the server restarts. Turns use current device state but do not retain conversation history. Music is simulated; no audio track is played. Small models may misunderstand or make incorrect tool choices, so inspect the activity feed.

The app doesn't send recordings or prompts to an external AI service. Initial dependency/model downloads require the internet; the Hugging Face client may check model metadata when loading. Microphone input requires a browser that supports MediaRecorder and permission for localhost.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```
