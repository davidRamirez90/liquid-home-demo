# Local voice home demo implementation plan

**Goal:** Build a local, push-to-talk home simulator using Liquid LFM3 Audio on Apple Silicon.
**Architecture:** A local Python HTTP server owns simulated device state, validates every proposed tool call, and runs MLX inference; a browser UI records audio and presents conversation, controls, and an action log. No real devices are connected.
**Tech stack:** Python, FastAPI, MLX-VLM, plain browser JavaScript/CSS.

1. Write and run failing tests for simulated device actions and validation, then implement them.
2. Integrate local model inference, voice transcription, tool requests and speech output; explicitly surface errors and serialize model access.
3. Implement a responsive local dashboard with recording, text input, manual controls and an action log.
4. Install dependencies, start server, exercise tests and real model inference; document setup and limitations.
