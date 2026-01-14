import pytest
from src.utility_classes.packaging_generator import HLS_Packaging_Generator

class TestPackaging:
    
    @pytest.fixture
    def packager(self, mock_video_path):
        return HLS_Packaging_Generator(mock_video_path)
        
    def test_create_hls_package_call(self, packager, mocker):
        mocker.patch('subprocess.run')
        mocker.patch('pathlib.Path.mkdir')
        res = packager.create_hls_package("final.mp4")
        assert isinstance(res, tuple)
        assert len(res) == 2
        assert "hls_package" in res[0]
        
    def test_adaptive_bitrate_encoding(self, packager, mocker, tmp_path):
        mocker.patch('subprocess.run')
        variants_dir = tmp_path / "variants"
        variants_dir.mkdir()
        
        variants = packager.adaptive_bitrate_encoding("final.mp4", str(variants_dir))
        assert len(variants) > 0
        assert variants[0]['resolution'] == "1920x1080"
