"""Bounded wake-to-utterance state machine; frames are opaque PCM bytes."""
from collections import deque

class Capture:
    def __init__(self, preroll_frames=13, silence_frames=15, wait_frames=75, max_frames=188):
        self.preroll_frames = preroll_frames
        self.silence_frames = silence_frames
        self.wait_frames = wait_frames
        self.max_frames = max_frames
        self.reset()

    def reset(self):
        self.preroll = deque(maxlen=self.preroll_frames)
        self.frames = []
        self.recording = False
        self.spoken = False
        self.silence = 0
        self.waiting = 0

    def feed(self, frame, wake, voice):
        if not self.recording:
            self.preroll.append(frame)
            if wake:
                self.frames = list(self.preroll)
                self.recording = True
            return None
        self.frames.append(frame)
        self.waiting += 1
        if voice:
            self.spoken = True
            self.silence = 0
        else:
            self.silence += 1
        if self.spoken and (self.silence >= self.silence_frames or len(self.frames) >= self.max_frames):
            result = b''.join(self.frames)
            self.reset()
            return result
        if not self.spoken and self.waiting >= self.wait_frames:
            self.reset()
        return None
