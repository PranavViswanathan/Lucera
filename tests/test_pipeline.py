import pytest
from src.main import VideoPipeline

class TestPipeline:
    
    @pytest.fixture
    def pipeline(self, mock_video_path):
        return VideoPipeline(mock_video_path)
        
    def test_pipeline_flow(self, pipeline, mocker):
        mocker.patch.object(pipeline, '_run_analysis')
        mocker.patch.object(pipeline, '_run_captioning')
        mocker.patch.object(pipeline, '_run_enhancement', return_value="enhanced.mp4")
        mocker.patch.object(pipeline, '_run_packaging')
        mocker.patch.object(pipeline, '_run_quality_check')
        mocker.patch.object(pipeline, '_generate_report')
        mocker.patch.object(pipeline, '_export_artifacts')
        
        res = pipeline.run()
        
        pipeline._run_analysis.assert_called_once()
        pipeline._run_captioning.assert_called_once()
        pipeline._run_enhancement.assert_called_once()
        pipeline._run_packaging.assert_called_with("enhanced.mp4")
        pipeline._run_quality_check.assert_called_with("enhanced.mp4")
        pipeline._generate_report.assert_called_once()
        pipeline._export_artifacts.assert_called_once()
        
        assert res is not None
        
    def test_run_combine(self, pipeline, mocker, tmp_path):
        # Setup mocks
        pipeline.results['stages']['captioning'] = {'srt_path': '/path/to/subs.srt'}
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('pathlib.Path.mkdir') 
        mock_run = mocker.patch('subprocess.run')
        
        # Call method
        output_dir = str(tmp_path / "combined_out")
        pipeline._run_combine("enhanced.mp4", output_dir)
        
        # Verify ffmpeg was called with expected args
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "ffmpeg" == cmd[0]
        assert "-c:s" in cmd
        assert "mov_text" in cmd
        assert str(tmp_path) in cmd[-1] or "combined" in cmd[-1]


