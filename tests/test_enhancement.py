import pytest
import shutil
from src.utility_classes.video_enchancers import Upscaling_Generator, Interpolation_Generator, Denoising_Generator

class TestEnhancement:
    
    @pytest.fixture
    def upscaler(self, mock_video_path):
        return Upscaling_Generator(mock_video_path)
        
    @pytest.fixture
    def interpolator(self, mock_video_path):
        return Interpolation_Generator(mock_video_path)

    @pytest.fixture
    def denoiser(self, mock_video_path):
        return Denoising_Generator(mock_video_path)

    def test_upscale_missing_binary(self, upscaler, mocker):
        mocker.patch('shutil.which', return_value=None)
        res = upscaler.batch_process_gpu("dummy_dir")
        assert res is None
        
    def test_upscale_existing_binary(self, upscaler, mocker, mock_frames_dir):
        mocker.patch('shutil.which', return_value="/usr/bin/realesrgan")
        mocker.patch('subprocess.run')
        res = upscaler.batch_process_gpu(mock_frames_dir)
        assert res is not None
        
    def test_upscale_run_full_skip(self, upscaler, mocker):
        mocker.patch.object(upscaler, 'load_model')
        mocker.patch.object(upscaler, 'extract_frames', return_value="frames_dir")
        mocker.patch.object(upscaler, 'batch_process_gpu', return_value=None)
        res = upscaler.run_full_analysis()
        assert res['skipped'] is True
        assert res['output_video'] == upscaler.video_path

    @pytest.mark.parametrize("model_name", ["realesrgan-x4plus", "realesrgan-x4plus-anime"])
    def test_upscaler_model_selection(self, mock_video_path, model_name):
        u = Upscaling_Generator(mock_video_path, model_name=model_name)
        assert u.model_name == model_name

    def test_interpolate_missing_binary(self, interpolator, mocker):
        mocker.patch('shutil.which', return_value=None)
        res = interpolator.generate_intermediate_frames("frames", 100)
        assert res is None
        
    def test_interpolate_existing_binary(self, interpolator, mocker, mock_frames_dir):
        mocker.patch('shutil.which', return_value="/usr/bin/rife")
        mocker.patch('subprocess.run')
        res = interpolator.generate_intermediate_frames(mock_frames_dir, 10)
        assert res is not None

    def test_check_fps_logic(self, interpolator, mocker):
        mock_cap = mocker.Mock()
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)
        
        # Case 1: Low fps
        mock_cap.get.return_value = 24.0
        needs, fps = interpolator.check_fps()
        assert needs is True
        
        # Case 2: Already high
        mock_cap.get.return_value = 60.0
        needs, fps = interpolator.check_fps()
        assert needs is False
        
        # Case 3: Higher than target
        mock_cap.get.return_value = 120.0
        needs, fps = interpolator.check_fps()
        assert needs is False

    def test_check_noise_level_high(self, denoiser, mocker):
        mock_cap = mocker.Mock()
        import numpy as np
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, frame)
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)
        
        mock_laplacian = mocker.Mock()
        mock_laplacian.var.return_value = 150.0
        mocker.patch('cv2.Laplacian', return_value=mock_laplacian)
        
        needs, level = denoiser.check_noise_level()
        assert needs is False
        assert level > 100

    def test_check_noise_level_low(self, denoiser, mocker):
        mock_cap = mocker.Mock()
        import numpy as np
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, frame)
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)
        
        mock_laplacian = mocker.Mock()
        mock_laplacian.var.return_value = 50.0
        mocker.patch('cv2.Laplacian', return_value=mock_laplacian)
        
        needs, level = denoiser.check_noise_level()
        assert needs is True
        assert level < 100
