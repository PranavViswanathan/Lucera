import datetime
import hashlib
import os
import json
import subprocess
from pathlib import Path
from subprocess import Popen, PIPE
import cv2
import numpy as np

class Analytics_Generator:
    def __init__(self, video_path):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.analysis_root = script_dir / "analysis_results"
        self.analysis_root.mkdir(exist_ok=True)
        
        print("video name:", self.video_name)
    
    def gather_metadata(self):
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()

        dump_path = self.analysis_root / "metadata_dump"
        metadata_name = f"{self.video_name}_{current_time_hash}.json"
        full_metadata_path = dump_path / metadata_name

        dump_path.mkdir(exist_ok=True)
        
        command = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "v:0", 
            "-show_entries", "stream=width,height,r_frame_rate,duration,nb_frames,pix_fmt,codec_name",
            "-of", "json",
            self.video_path
        ]

        with open(full_metadata_path, 'w') as outfile:
            process = Popen(command, stdout=outfile, stderr=PIPE)
            stdout, stderr = process.communicate()
        
        print(f"Metadata saved to: {full_metadata_path}")
        return str(full_metadata_path)

    def scene_analysis_filter(self, threshold=0.1):
        scenes_dir = self.analysis_root / "scene_detection"
        scenes_dir.mkdir(exist_ok=True)
        
        scenes_file = scenes_dir / f"{self.video_name}_scenes.txt"
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null",
            "-"
        ]
        
        process = Popen(command, stdout=PIPE, stderr=PIPE, text=True)
        stdout, stderr = process.communicate()
        
        scene_count = 0
        with open(scenes_file, 'w') as f:
            f.write(f"Scene Detection (threshold={threshold})\n")
            f.write("=" * 50 + "\n\n")
            
            for line in stderr.split('\n'):
                if 'Parsed_showinfo' in line and 'pts_time' in line:
                    if 'pts_time:' in line and 'scene:' in line:
                        timestamp = line.split('pts_time:')[1].split()[0]
                        scene_score = line.split('scene:')[1].split()[0]
                        
                        if float(scene_score) > threshold:
                            f.write(f"Scene cut at {timestamp}s (score: {scene_score})\n")
                            scene_count += 1
            
            if scene_count == 0:
                f.write("No scene cuts detected above threshold.\n")
                f.write("This video appears to be a single continuous scene.\n")
        
        print(f"Detected {scene_count} scene cuts")
        print(f"Scene detection saved to: {scenes_file}")
        return str(scenes_file)

    def motion_analysis(self):
        motion_dir = self.analysis_root / "motion_analysis"
        motion_dir.mkdir(exist_ok=True)
        
        motion_file = motion_dir / f"{self.video_name}_motion.txt"
        motion_video = motion_dir / f"{self.video_name}_motion_vectors.mp4"
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-vf", "mestimate=epzs:mb_size=16,codecview=mv=pf+bf+bb",
            "-y",
            str(motion_video)
        ]
        
        process = Popen(command, stdout=PIPE, stderr=PIPE, text=True)
        stdout, stderr = process.communicate()
        cap = cv2.VideoCapture(self.video_path)
        ret, prev_frame = cap.read()
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        motion_scores = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None, 
                0.5, 3, 15, 3, 5, 1.2, 0
            )
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            avg_motion = np.mean(magnitude)
            max_motion = np.max(magnitude)
            
            motion_scores.append({
                'frame': frame_count,
                'avg_motion': float(avg_motion),
                'max_motion': float(max_motion),
                'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS)
            })
            
            prev_gray = gray
            frame_count += 1
        
        cap.release()
        
        with open(motion_file, 'w') as f:
            f.write("Motion Analysis (Optical Flow)\n")
            f.write("=" * 50 + "\n\n")
            
            total_motion = sum(s['avg_motion'] for s in motion_scores)
            avg_motion = total_motion / len(motion_scores) if motion_scores else 0
            
            f.write(f"Total frames analyzed: {len(motion_scores)}\n")
            f.write(f"Average motion: {avg_motion:.2f}\n")
            f.write(f"Motion classification: {self._classify_motion(avg_motion)}\n\n")
            
            f.write("Frame-by-frame motion:\n")
            for score in motion_scores[::10]:  
                f.write(f"Frame {score['frame']} ({score['timestamp']:.2f}s): "
                       f"avg={score['avg_motion']:.2f}, max={score['max_motion']:.2f}\n")
        
        print(f"Motion analysis saved to: {motion_file}")
        return str(motion_file), motion_scores

    def complexity_analysis(self):
        complexity_dir = self.analysis_root / "complexity_analysis"
        complexity_dir.mkdir(exist_ok=True)
        
        complexity_file = complexity_dir / f"{self.video_name}_complexity.txt"
        edges_video = complexity_dir / f"{self.video_name}_edges.mp4"
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-vf", "edgedetect=low=0.1:high=0.4",
            "-y",
            str(edges_video)
        ]
        
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        
        cap = cv2.VideoCapture(self.video_path)
        complexity_scores = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150)
            
            edge_density = np.sum(edges > 0) / edges.size
            edge_count = np.sum(edges > 0)
            
            complexity_scores.append({
                'frame': frame_count,
                'edge_density': float(edge_density),
                'edge_count': int(edge_count),
                'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS)
            })
            
            frame_count += 1
        
        cap.release()
        
        with open(complexity_file, 'w') as f:
            f.write("Complexity Analysis (Edge Detection)\n")
            f.write("=" * 50 + "\n\n")
            
            avg_density = sum(s['edge_density'] for s in complexity_scores) / len(complexity_scores)
            
            f.write(f"Total frames analyzed: {len(complexity_scores)}\n")
            f.write(f"Average edge density: {avg_density:.4f}\n")
            f.write(f"Complexity classification: {self._classify_complexity(avg_density)}\n\n")
            
            f.write("Frame-by-frame complexity:\n")
            for score in complexity_scores[::10]:
                f.write(f"Frame {score['frame']} ({score['timestamp']:.2f}s): "
                       f"density={score['edge_density']:.4f}, edges={score['edge_count']}\n")
        
        print(f"Complexity analysis saved to: {complexity_file}")
        return str(complexity_file), complexity_scores

    def noise_estimation(self):
        noise_dir = self.analysis_root / "noise_estimation"
        noise_dir.mkdir(exist_ok=True)
        
        noise_file = noise_dir / f"{self.video_name}_noise.txt"
        cap = cv2.VideoCapture(self.video_path)
        noise_scores = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            
            noise_scores.append({
                'frame': frame_count,
                'laplacian_variance': float(variance),
                'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS)
            })
            
            frame_count += 1
        
        cap.release()
        
        with open(noise_file, 'w') as f:
            f.write("Noise Estimation (Laplacian Variance)\n")
            f.write("=" * 50 + "\n\n")
            
            avg_variance = sum(s['laplacian_variance'] for s in noise_scores) / len(noise_scores)
            
            f.write(f"Total frames analyzed: {len(noise_scores)}\n")
            f.write(f"Average Laplacian variance: {avg_variance:.2f}\n")
            f.write(f"Noise level: {self._classify_noise(avg_variance)}\n\n")
            
            f.write("Frame-by-frame noise:\n")
            for score in noise_scores[::10]: 
                f.write(f"Frame {score['frame']} ({score['timestamp']:.2f}s): "
                       f"variance={score['laplacian_variance']:.2f}\n")
        
        print(f"Noise estimation saved to: {noise_file}")
        return str(noise_file), noise_scores

    def blur_detection(self):
        blur_dir = self.analysis_root / "blur_detection"
        blur_dir.mkdir(exist_ok=True)
        
        blur_file = blur_dir / f"{self.video_name}_blur.txt"
        cap = cv2.VideoCapture(self.video_path)
        blur_scores = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fft = np.fft.fft2(gray)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shift)
            rows, cols = gray.shape
            crow, ccol = rows // 2, cols // 2
            
            mask = np.ones((rows, cols), dtype=np.uint8)
            r = 30  
            cv2.circle(mask, (ccol, crow), r, 0, -1)
            
            high_freq = magnitude * mask
            high_freq_mean = np.mean(high_freq)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            blur_scores.append({
                'frame': frame_count,
                'high_freq_content': float(high_freq_mean),
                'laplacian_variance': float(laplacian_var),
                'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS)
            })
            
            frame_count += 1
        
        cap.release()
    
        with open(blur_file, 'w') as f:
            f.write("Blur Detection (Frequency Analysis)\n")
            f.write("=" * 50 + "\n\n")
            
            avg_laplacian = sum(s['laplacian_variance'] for s in blur_scores) / len(blur_scores)
            
            f.write(f"Total frames analyzed: {len(blur_scores)}\n")
            f.write(f"Average Laplacian variance: {avg_laplacian:.2f}\n")
            f.write(f"Blur classification: {self._classify_blur(avg_laplacian)}\n\n")
            
            f.write("Frame-by-frame blur:\n")
            for score in blur_scores[::10]:  
                f.write(f"Frame {score['frame']} ({score['timestamp']:.2f}s): "
                       f"laplacian={score['laplacian_variance']:.2f}, "
                       f"freq={score['high_freq_content']:.2f}\n")
        
        print(f"Blur detection saved to: {blur_file}")
        return str(blur_file), blur_scores

    def decision_engine(self, motion_scores, complexity_scores, noise_scores, blur_scores):
        decision_dir = self.analysis_root / "decision_engine"
        decision_dir.mkdir(exist_ok=True)
        
        decision_file = decision_dir / f"{self.video_name}_decision.json"
        avg_motion = sum(s['avg_motion'] for s in motion_scores) / len(motion_scores)
        avg_complexity = sum(s['edge_density'] for s in complexity_scores) / len(complexity_scores)
        avg_noise = sum(s['laplacian_variance'] for s in noise_scores) / len(noise_scores)
        avg_blur = sum(s['laplacian_variance'] for s in blur_scores) / len(blur_scores)
        
        motion_class = self._classify_motion(avg_motion)
        complexity_class = self._classify_complexity(avg_complexity)
        noise_class = self._classify_noise(avg_noise)
        blur_class = self._classify_blur(avg_blur)

        quality_score = self._calculate_quality_score(avg_motion, avg_complexity, avg_noise, avg_blur)
        
        decision = {
            'video_name': self.video_name,
            'analysis_timestamp': datetime.datetime.now().isoformat(),
            'metrics': {
                'motion': {
                    'average': float(avg_motion),
                    'classification': motion_class
                },
                'complexity': {
                    'average': float(avg_complexity),
                    'classification': complexity_class
                },
                'noise': {
                    'average': float(avg_noise),
                    'classification': noise_class
                },
                'blur': {
                    'average': float(avg_blur),
                    'classification': blur_class
                }
            },
            'overall_quality_score': quality_score,
            'recommendations': self._generate_recommendations(motion_class, complexity_class, noise_class, blur_class)
        }
        with open(decision_file, 'w') as f:
            json.dump(decision, f, indent=4)
        print(f"DECISION ENGINE RESULTS")
        print(f"Overall Quality Score: {quality_score}/100")
        print(f"Motion: {motion_class}")
        print(f"Complexity: {complexity_class}")
        print(f"Noise Level: {noise_class}")
        print(f"Blur Level: {blur_class}")
        print(f"\nDecision saved to: {decision_file}")
        
        return decision

    def _classify_motion(self, avg_motion):
        if avg_motion < 1.0:
            return "Static/Low Motion"
        elif avg_motion < 5.0:
            return "Moderate Motion"
        else:
            return "High Motion"
    
    def _classify_complexity(self, avg_density):
        if avg_density < 0.05:
            return "Simple/Low Complexity"
        elif avg_density < 0.15:
            return "Moderate Complexity"
        else:
            return "High Complexity"
    
    def _classify_noise(self, avg_variance):
        if avg_variance < 100:
            return "High Noise"
        elif avg_variance < 500:
            return "Moderate Noise"
        else:
            return "Low Noise"
    
    def _classify_blur(self, avg_laplacian):
        if avg_laplacian < 100:
            return "Heavily Blurred"
        elif avg_laplacian < 500:
            return "Moderately Blurred"
        else:
            return "Sharp/Clear"
    
    def _calculate_quality_score(self, motion, complexity, noise, blur):
        motion_score = min(motion / 10.0, 1.0) * 100
        complexity_score = min(complexity / 0.2, 1.0) * 100
        noise_score = min(noise / 1000.0, 1.0) * 100
        blur_score = min(blur / 1000.0, 1.0) * 100
        
        quality = (motion_score * 0.2 + complexity_score * 0.2 + 
                  noise_score * 0.3 + blur_score * 0.3)
        
        return round(quality, 2)
    
    def _generate_recommendations(self, motion, complexity, noise, blur):
        recommendations = []
        
        if "Low Motion" in motion:
            recommendations.append("Consider adding dynamic camera movements or action")
        
        if "Low Complexity" in complexity:
            recommendations.append("Scene appears simple - consider adding more visual elements")
        
        if "High Noise" in noise:
            recommendations.append("Video has significant noise - consider noise reduction")
        
        if "Blurred" in blur:
            recommendations.append("Video appears blurred - check focus and stabilization")
        
        if not recommendations:
            recommendations.append("Video quality is good across all metrics")
        
        return recommendations

    def run_full_analysis(self):
        print("Starting full video analysis pipeline")
        print("="*60)
        
        print("\n[1/6] Extracting metadata")
        metadata_path = self.gather_metadata()
        
        print("\n[2/6] Detecting scenes")
        scenes_path = self.scene_analysis_filter()
        
        print("\n[3/6] Analyzing motion")
        motion_path, motion_scores = self.motion_analysis()
        
        print("\n[4/6] Analyzing complexity")
        complexity_path, complexity_scores = self.complexity_analysis()
        
        print("\n[5/6] Estimating noise")
        noise_path, noise_scores = self.noise_estimation()
      
        print("\n[6/6] Detecting blur")
        blur_path, blur_scores = self.blur_detection()
        
        print("\n[FINAL] Running decision engine")
        decision = self.decision_engine(motion_scores, complexity_scores, noise_scores, blur_scores)
        print("ANALYSIS COMPLETE!")

        return decision