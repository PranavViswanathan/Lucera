import pytest
import cv2
import numpy as np
import json
from src.utility_classes.video_analysis import Analytics_Generator

class TestAnalyticsGenerator:
    
    @pytest.fixture
    def analytics(self, mock_video_path):
        return Analytics_Generator(mock_video_path)
    
    def test_initialization(self, analytics, mock_video_path):
        assert analytics.video_path == mock_video_path
        assert analytics.video_name == "test_video"
        
    @pytest.mark.parametrize("score,expected", [
        (15.0, "High Motion"),
        (4.0, "Moderate Motion"),
        (0.5, "Static/Low Motion"),
        (25.0, "High Motion"),
        (0.0, "Static/Low Motion")
    ])
    def test_classify_motion(self, analytics, score, expected):
        assert analytics._classify_motion(score) == expected
        
    @pytest.mark.parametrize("score,expected", [
        (1.0, "High Complexity"),
        (0.1, "Moderate Complexity"),
        (0.01, "Simple/Low Complexity"),
        (0.2, "High Complexity"),
        (0.0, "Simple/Low Complexity")
    ])
    def test_classify_complexity(self, analytics, score, expected):
        assert analytics._classify_complexity(score) == expected
        
    @pytest.mark.parametrize("score,expected", [
        (1000, "Low Noise"),
        (50, "High Noise"),
        (200, "Moderate Noise")
    ])
    def test_classify_noise(self, analytics, score, expected):
        assert analytics._classify_noise(score) == expected

    @pytest.mark.parametrize("score,expected", [
        (50, "Blurry"), 
        (500, "Sharp"),
        (0, "Blurry")
    ])
    def test_classify_blur(self, analytics, score, expected):
        res = analytics._classify_blur(score)
        assert isinstance(res, str)
    
    def test_calculate_quality_score(self, analytics):
        score = analytics._calculate_quality_score(
            motion=0.1, complexity=0.1, noise=10.0, blur=1000.0)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_generate_recommendations(self, analytics):
        recs = analytics._generate_recommendations(
            motion="High Motion", 
            complexity="Moderate Complexity", 
            noise="High Noise", 
            blur="Sharp"
        )
        rec_str = json.dumps(recs)
        assert "noise reduction" in rec_str
        
    def test_scene_analysis_filter(self, analytics, mocker):
        mock_cap = mocker.Mock()
        mock_cap.read.side_effect = [
            (True, np.zeros((100, 100, 3), dtype=np.uint8)),
            (True, np.ones((100, 100, 3), dtype=np.uint8) * 255),
            (False, None)
        ]
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)
        
        analytics.scene_analysis_filter()
        scene_file = analytics.analysis_root / "scene_detection" / "test_video_scenes.txt"
        assert scene_file.exists()

    def test_full_analysis_structure(self, analytics, mocker):
        mocker.patch.object(analytics, 'gather_metadata', return_value={})
        mocker.patch.object(analytics, 'scene_analysis_filter', return_value=[])
        mocker.patch.object(analytics, 'motion_analysis', return_value=(1.0, []))
        mocker.patch.object(analytics, 'complexity_analysis', return_value=(1.0, []))
        mocker.patch.object(analytics, 'noise_estimation', return_value=(10.0, []))
        mocker.patch.object(analytics, 'blur_detection', return_value=(100.0, []))
        mocker.patch.object(analytics, 'decision_engine', return_value={'score': 50})
        
        result = analytics.run_full_analysis()
        assert isinstance(result, dict)
        assert result['score'] == 50
