"""Local transcription for the enhance track (spec §Components).

faster-whisper runs on the Mac mini — offline, no new vendor. ffmpeg extracts
audio. The model call and ffmpeg are boundaries; the formatting helpers are pure
and unit-tested. Tests never download a model.
"""

import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_MODEL_SIZE = "base"


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _end_after_start(self) -> "TranscriptSegment":
        if self.end_s < self.start_s:
            raise ValueError("end_s must be >= start_s")
        return self


def format_for_prompt(segments: list[TranscriptSegment]) -> str:
    """One '[start-end] text' line per segment — the transcript Claude reads."""
    return "\n".join(f"[{s.start_s}-{s.end_s}] {s.text.strip()}" for s in segments)


def total_duration_s(segments: list[TranscriptSegment]) -> float:
    """Video length proxy: the last segment's end (0.0 if no speech)."""
    return segments[-1].end_s if segments else 0.0


def extract_audio(video_path: Path, out_wav: Path) -> None:
    """ffmpeg: strip a mono 16 kHz wav for Whisper (boundary)."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", str(out_wav)],
        check=True,
        capture_output=True,
    )


def transcribe(video_path: Path, model_size: str = DEFAULT_MODEL_SIZE) -> list[TranscriptSegment]:
    """Transcribe a local video file to timestamped segments (boundary)."""
    from faster_whisper import WhisperModel  # local import: tests never load it

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        extract_audio(video_path, wav)
        model = WhisperModel(model_size, device="auto", compute_type="int8")
        segments, _info = model.transcribe(str(wav), word_timestamps=False)
        return [
            TranscriptSegment(text=s.text, start_s=round(s.start, 2), end_s=round(s.end, 2))
            for s in segments
        ]
