import unittest
from listener_capture import Capture

class CaptureTests(unittest.TestCase):
    def test_wake_keeps_bounded_preroll_and_finishes_after_silence(self):
        c = Capture(preroll_frames=2, silence_frames=2, wait_frames=5, max_frames=10)
        self.assertIsNone(c.feed(b'a', False, False))
        self.assertIsNone(c.feed(b'b', False, False))
        self.assertIsNone(c.feed(b'c', True, False))
        self.assertTrue(c.recording)
        self.assertIsNone(c.feed(b'd', False, True))
        self.assertIsNone(c.feed(b'e', False, False))
        self.assertEqual(c.feed(b'f', False, False), b'bcdef')
        self.assertFalse(c.recording)

    def test_wake_without_speech_times_out_without_sending_audio(self):
        c = Capture(preroll_frames=2, silence_frames=2, wait_frames=2, max_frames=10)
        c.feed(b'a', True, False)
        c.feed(b'b', False, False)
        self.assertIsNone(c.feed(b'c', False, False))
        self.assertFalse(c.recording)

    def test_continuous_speech_has_a_hard_limit(self):
        c = Capture(preroll_frames=2, silence_frames=2, wait_frames=2, max_frames=3)
        c.feed(b'a', True, False)
        c.feed(b'b', False, True)
        self.assertEqual(c.feed(b'c', False, True), b'abc')
        self.assertFalse(c.recording)

    def test_reset_discards_audio(self):
        c = Capture(preroll_frames=2, silence_frames=2, wait_frames=2, max_frames=5)
        c.feed(b'secret', True, False)
        c.reset()
        c.feed(b'new', True, False)
        c.feed(b'voice', False, True)
        c.feed(b'quiet', False, False)
        self.assertEqual(c.feed(b'end', False, False), b'newvoicequietend')

class ListenerLifecycleTests(unittest.TestCase):
    def test_pause_and_resume_invalidates_in_flight_session(self):
        from listener import Listener
        listener = Listener()
        token = listener.session_token()
        listener.pause()
        listener.resume()
        self.assertFalse(listener.is_current(token))
        self.assertTrue(listener.is_current(listener.session_token()))

class AudioTests(unittest.TestCase):
    def test_vad_processes_every_subframe_even_when_speech_detected(self):
        from listener import voiced
        class Vad:
            def __init__(self): self.calls = 0
            def is_speech(self, frame, rate):
                self.calls += 1
                return self.calls == 1
        vad = Vad()
        self.assertTrue(voiced(vad, bytes(2560)))
        self.assertEqual(vad.calls, 4)

    def test_wav_wraps_pcm_as_mono_16khz(self):
        import io, wave
        from listener_audio import pcm_to_wav
        pcm = b'\x01\x00\xff\xff' * 100
        with wave.open(io.BytesIO(pcm_to_wav(pcm)), 'rb') as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 16000))
            self.assertEqual(wav.readframes(200), pcm)

    def test_rejects_invalid_pcm(self):
        from listener_audio import pcm_to_wav
        with self.assertRaises(ValueError): pcm_to_wav(b'123')
        with self.assertRaises(ValueError): pcm_to_wav(b'')

if __name__ == '__main__': unittest.main()
