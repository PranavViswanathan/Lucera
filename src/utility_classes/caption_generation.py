import whisper
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import tempfile
import os
import datetime
import hashlib


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


class Caption_Generator:
    def __init__(self, video_path, model_size: str = "base", device: str = "cpu"):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.captions_root = script_dir / "caption_results"
        self.captions_root.mkdir(exist_ok=True)
        
        self.model_size = model_size
        self.device = device
        self.model = None
        
        print("video name:", self.video_name)
        print(f"Whisper model: {model_size}")
    
    def _load_model(self):
        if self.model is None:
            print("Loading Whisper model...")
            self.model = whisper.load_model(self.model_size, device=self.device)
    
    def extract_audio(self):
        audio_dir = self.captions_root / "audio_extraction"
        audio_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        audio_name = f"{self.video_name}_{current_time_hash}.wav"
        audio_path = audio_dir / audio_name
        
        if not Path(self.video_path).exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        print(f"Extracting audio from {self.video_name}{self.video_format}...")
        
        command = [
            'ffmpeg',
            '-i', str(self.video_path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(audio_path)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Audio extracted to: {audio_path}")
            return str(audio_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg error: {e.stderr.decode()}")
    
    def transcribe_audio(self, audio_path: str):
        self._load_model()
        
        transcription_dir = self.captions_root / "transcription"
        transcription_dir.mkdir(exist_ok=True)
        
        print(f"Transcribing audio with Whisper ({self.model_size})...")
        result = self.model.transcribe(audio_path, word_timestamps=False)
        
        segments = []
        for seg in result['segments']:
            segments.append(TranscriptSegment(
                start=seg['start'],
                end=seg['end'],
                text=seg['text'].strip()
            ))
        
        print(f"Transcription complete: {len(segments)} segments")
        return segments
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def generate_srt(self, segments: List[TranscriptSegment]):
        srt_dir = self.captions_root / "srt_captions"
        srt_dir.mkdir(exist_ok=True)
        
        srt_file = srt_dir / f"{self.video_name}.srt"
        
        with open(srt_file, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_timestamp_srt(seg.start)} --> {self._format_timestamp_srt(seg.end)}\n")
                f.write(f"{seg.text}\n\n")
        
        print(f"SRT file saved: {srt_file}")
        return str(srt_file)
    
    def generate_vtt(self, segments: List[TranscriptSegment]):
        vtt_dir = self.captions_root / "vtt_captions"
        vtt_dir.mkdir(exist_ok=True)
        
        vtt_file = vtt_dir / f"{self.video_name}.vtt"
        
        with open(vtt_file, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for seg in segments:
                f.write(f"{self._format_timestamp_vtt(seg.start)} --> {self._format_timestamp_vtt(seg.end)}\n")
                f.write(f"{seg.text}\n\n")
        
        print(f"VTT file saved: {vtt_file}")
        return str(vtt_file)
    
    def run_full_analysis(self, keep_audio: bool = False):
        print("Starting full caption generation pipeline")
        print("="*60)
        
        print("\n[1/4] Extracting audio")
        audio_path = self.extract_audio()
        
        print("\n[2/4] Transcribing with Whisper")
        segments = self.transcribe_audio(audio_path)
        
        print("\n[3/4] Generating SRT captions")
        srt_path = self.generate_srt(segments)
        
        print("\n[4/4] Generating VTT captions")
        vtt_path = self.generate_vtt(segments)
        
        if not keep_audio and os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"\nRemoved temporary audio file")
        
        print("\nCAPTION GENERATION COMPLETE!")
        print(f"SRT: {srt_path}")
        print(f"VTT: {vtt_path}")
        
        result = {
            'video_name': self.video_name,
            'srt_path': srt_path,
            'vtt_path': vtt_path,
            'audio_path': audio_path if keep_audio else None,
            'segment_count': len(segments),
            'model_used': self.model_size
        }
        
        return result
