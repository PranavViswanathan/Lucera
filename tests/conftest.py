import os
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def mock_video_path(tmp_path):
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()
    return str(video_file)

@pytest.fixture
def mock_frames_dir(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "frame_000001.png").touch()
    (frames_dir / "frame_000002.png").touch()
    return str(frames_dir)
