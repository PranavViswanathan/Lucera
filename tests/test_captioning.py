import pytest
from src.utility_classes.caption_generation import Caption_Generator, TranscriptSegment

class TestCaptionGenerator:
    
    @pytest.fixture
    def captioneer(self, mock_video_path):
        return Caption_Generator(mock_video_path)

    @pytest.mark.parametrize("seconds,expected", [
        (3661.5, "01:01:01,500"),
        (0.0, "00:00:00,000"),
        (1.0, "00:00:01,000")
    ])
    def test_timestamp_formatting_srt(self, captioneer, seconds, expected):
        assert captioneer._format_timestamp_srt(seconds) == expected

    @pytest.mark.parametrize("seconds,expected", [
        (3600.0, "01:00:00.000"),
        (0.500, "00:00:00.500")
    ])
    def test_timestamp_formatting_vtt(self, captioneer, seconds, expected):
        assert captioneer._format_timestamp_vtt(seconds) == expected
            
    def test_generate_srt(self, captioneer):
        segments = [
            TranscriptSegment(start=0.0, end=1.0, text="Hello"),
            TranscriptSegment(start=1.0, end=2.0, text="World")
        ]
        path = captioneer.generate_srt(segments)
        assert path.endswith(".srt")
        with open(path, 'r') as f:
            content = f.read()
            assert "00:00:00,000 --> 00:00:01,000" in content
            assert "Hello" in content
            
    def test_generate_vtt(self, captioneer):
        segments = [TranscriptSegment(start=0.0, end=1.0, text="Hello")]
        path = captioneer.generate_vtt(segments)
        assert path.endswith(".vtt")
        with open(path, 'r') as f:
            content = f.read()
            assert "WEBVTT" in content
            
    def test_extract_audio_call(self, captioneer, mocker):
        mocker.patch('subprocess.run')
        mocker.patch('pathlib.Path.exists', return_value=True)
        audio_path = captioneer.extract_audio()
        assert audio_path.endswith(".wav")
        
    def test_extract_audio_fail(self, captioneer, mocker):
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('subprocess.run', side_effect=RuntimeError("ffmpeg failed"))
        with pytest.raises(RuntimeError):
            captioneer.extract_audio()
        
    def test_transcribe_audio_mock(self, captioneer, mocker):
        mock_model = mocker.Mock()
        mock_model.transcribe.return_value = {
            'segments': [{'start': 0.0, 'end': 2.0, 'text': ' Test caption'}]
        }
        mocker.patch('whisper.load_model', return_value=mock_model)
        segments = captioneer.transcribe_audio("fake_audio.wav")
        assert len(segments) == 1
        assert segments[0].text == "Test caption"

    def test_full_pipeline_flow(self, captioneer, mocker):
        mocker.patch.object(captioneer, 'extract_audio', return_value="test.wav")
        mocker.patch.object(captioneer, 'transcribe_audio', return_value=[])
        mocker.patch.object(captioneer, 'generate_srt', return_value="test.srt")
        mocker.patch.object(captioneer, 'generate_vtt', return_value="test.vtt")
        mocker.patch('os.remove')
        mocker.patch('os.path.exists', return_value=True)
        res = captioneer.run_full_analysis()
        assert res['srt_path'] == "test.srt"
        assert res['vtt_path'] == "test.vtt"
