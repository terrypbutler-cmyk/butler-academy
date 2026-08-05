from array import array
from io import BytesIO
import math
import unittest
import wave

from modules.audio_utils import normalise_pcm16, pcm_segments_to_wav


def constant_pcm(level, sample_count=1000):
    return array("h", [level] * sample_count).tobytes()


def pcm_rms(pcm_data):
    samples = array("h")
    samples.frombytes(pcm_data)
    return math.sqrt(
        sum(sample * sample for sample in samples)
        / len(samples)
    )


class AudioUtilsTests(unittest.TestCase):
    def test_joins_pcm_segments_with_a_pause_into_one_wav(self):
        first = b"\x01\x00" * 100
        second = b"\x02\x00" * 100

        audio = pcm_segments_to_wav(
            [first, second],
            sample_rate=1000,
            pause_ms=100,
        )

        with wave.open(BytesIO(audio), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.getframerate(), 1000)
            self.assertEqual(wav_file.getnframes(), 300)

    def test_returns_none_when_no_audio_was_generated(self):
        self.assertIsNone(pcm_segments_to_wav([None, b""]))

    def test_quiet_and_loud_clips_are_levelled_towards_the_same_volume(self):
        quiet = normalise_pcm16(constant_pcm(1000))
        loud = normalise_pcm16(constant_pcm(10000))

        quiet_rms = pcm_rms(quiet)
        loud_rms = pcm_rms(loud)

        self.assertGreater(quiet_rms, 1000)
        self.assertLess(loud_rms, 10000)
        self.assertLess(abs(quiet_rms - loud_rms) / loud_rms, 0.08)

    def test_conversation_segments_are_individually_levelled_before_joining(self):
        audio = pcm_segments_to_wav(
            [constant_pcm(1000), constant_pcm(10000)],
            sample_rate=1000,
            pause_ms=0,
        )

        with wave.open(BytesIO(audio), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())

        midpoint = len(frames) // 2
        first_rms = pcm_rms(frames[:midpoint])
        second_rms = pcm_rms(frames[midpoint:])
        self.assertLess(abs(first_rms - second_rms) / second_rms, 0.08)


if __name__ == "__main__":
    unittest.main()
