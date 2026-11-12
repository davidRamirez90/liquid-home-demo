# Always-on listener MVP

**Goal:** Add a local macOS menu-bar listener that wakes on a pre-trained phrase and sends bounded speech to the existing mock-home backend.

**Architecture:** A native menu-bar process owns microphone lifecycle. Its worker processes 80 ms PCM frames through openWakeWord, keeps a bounded pre-roll in memory, and uses WebRTC VAD to finish a bounded request. It closes the microphone during model inference and reply playback, then reopens it. The existing backend continues to validate all simulated actions.

**Steps:**
1. Test and implement a pure capture state machine: wake, bounded pre-roll, post-wake speech, silence termination, timeouts and reset.
2. Install and verify local wake-word and VAD inference; use only the pre-trained English “hey jarvis” model and document its non-commercial license.
3. Implement the menu-bar listener, bounded queues, pause/resume, error handling, backend submission and playback.
4. Document microphone permissions, setup, privacy, limitations and verification. Test with fixtures and the real local model; only access the live microphone when the user runs the listener and grants permission.
