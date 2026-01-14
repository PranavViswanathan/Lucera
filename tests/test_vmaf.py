import pytest
import json
from src.utility_classes.VMAF import VMAF_Calculator

class TestVMAF:
    
    @pytest.fixture
    def vmaf(self, mock_video_path):
        return VMAF_Calculator(mock_video_path, mock_video_path)
        
    def test_init(self, vmaf, mock_video_path):
        assert vmaf.reference_video == mock_video_path
        
    def test_parsing_logic_mock(self, vmaf, mocker):
        mocker.patch('subprocess.run')
        mocker.patch.object(vmaf, 'calculate_vmaf', return_value=("path.json", 95.5))
        mocker.patch.object(vmaf, 'calculate_psnr', return_value=("log", 40.0))
        mocker.patch.object(vmaf, 'calculate_ssim', return_value=("log", 0.98))
        mocker.patch.object(vmaf, 'generate_vmaf_report', return_value=({}, "", {'metrics': {'vmaf': {'status': 'good'}, 'psnr': {'status': 'good'}, 'ssim': {'status': 'good'}}}))
        
        res = vmaf.run_full_analysis()
        assert res['vmaf_score'] == 95.5
        assert res['psnr_score'] == 40.0

    def test_calculate_ssim_mock(self, vmaf, mocker):
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value.stdout = "SSIM Y:0.9823423"
        mocker.patch('os.path.exists', return_value=True)
        
        pass

    def test_no_metrics_default(self, vmaf, mocker):
        mocker.patch.object(vmaf, 'calculate_vmaf', return_value=("path.json", 0))
        mocker.patch.object(vmaf, 'calculate_psnr', return_value=("log", 0))
        mocker.patch.object(vmaf, 'calculate_ssim', return_value=("log", 0))
        mocker.patch.object(vmaf, 'generate_vmaf_report', return_value=({}, "", {'metrics': {'vmaf': {'status': 'bad'}, 'psnr': {'status': 'bad'}, 'ssim': {'status': 'bad'}}}))
        
        res = vmaf.run_full_analysis()
        assert res['vmaf_score'] == 0
