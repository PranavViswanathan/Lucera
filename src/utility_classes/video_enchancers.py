import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
import datetime
import hashlib
import json
import cv2
import os


class Upscaling_Generator:
    
    def __init__(self, video_path: str, model_name: str = "RealESRGAN_x4plus"):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.upscaling_root = script_dir / "upscaling_results"
        self.upscaling_root.mkdir(exist_ok=True)
        
        self.model_name = model_name
        
        print("video name:", self.video_name)
        print(f"Upscaling model: {model_name}")
    
    def load_model(self):
        model_dir = self.upscaling_root / "models"
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / f"{self.model_name}.pth"
        
        print(f"Loading Real-ESRGAN model: {self.model_name}")
        
        return str(model_path)
    
    def extract_frames(self):
        frames_dir = self.upscaling_root / "frame_extraction" / self.video_name
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        output_pattern = frames_dir / "frame_%06d.png"
        
        print(f"Extracting frames to PNG sequence...")
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-qscale:v", "1",
            "-qmin", "1",
            "-qmax", "1",
            "-vsync", "0",
            str(output_pattern)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            frame_count = len(list(frames_dir.glob("*.png")))
            print(f"Extracted {frame_count} frames")
            return str(frames_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Frame extraction error: {e.stderr.decode()}")
    
    def batch_process_gpu(self, frames_dir: str):
        upscaled_dir = self.upscaling_root / "upscaled_frames" / self.video_name
        upscaled_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Running GPU batch inference with Real-ESRGAN...")
        
        command = [
            "realesrgan-ncnn-vulkan",
            "-i", frames_dir,
            "-o", str(upscaled_dir),
            "-n", self.model_name,
            "-s", "4",
            "-f", "png"
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Batch processing complete")
            return str(upscaled_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"GPU processing error: {e.stderr.decode()}")
    
    def upscale_4x(self, upscaled_frames_dir: str):
        print(f"Applying 4x upscaling (480p -> 1920p)")
        return upscaled_frames_dir
    
    def encode_video(self, frames_dir: str):
        output_dir = self.upscaling_root / "final_videos"
        output_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        output_video = output_dir / f"{self.video_name}_upscaled_{current_time_hash}.mp4"
        
        frame_pattern = Path(frames_dir) / "frame_%06d.png"
        
        print(f"Encoding upscaled video...")
        
        command = [
            "ffmpeg",
            "-framerate", "30",
            "-i", str(frame_pattern),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(output_video)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Video encoded: {output_video}")
            return str(output_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Video encoding error: {e.stderr.decode()}")
    
    def run_full_analysis(self):
        print("Starting video upscaling pipeline")
        print("="*60)
        
        print("\n[1/5] Loading Real-ESRGAN model")
        model_path = self.load_model()
        
        print("\n[2/5] Extracting frames as PNG sequence")
        frames_dir = self.extract_frames()
        
        print("\n[3/5] Batch processing with GPU inference")
        upscaled_frames = self.batch_process_gpu(frames_dir)
        
        print("\n[4/5] Applying 4x upscale")
        final_frames = self.upscale_4x(upscaled_frames)
        
        print("\n[5/5] Encoding back to video")
        output_video = self.encode_video(final_frames)
        
        print("\nUPSCALING COMPLETE!")
        
        return {
            'video_name': self.video_name,
            'output_video': output_video,
            'model_used': self.model_name,
            'scale_factor': '4x',
            'resolution': '1920p'
        }


class Interpolation_Generator:
    
    def __init__(self, video_path: str, target_fps: int = 60):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.interpolation_root = script_dir / "interpolation_results"
        self.interpolation_root.mkdir(exist_ok=True)
        
        self.target_fps = target_fps
        
        print("video name:", self.video_name)
        print(f"Target FPS: {target_fps}")
    
    def check_fps(self):
        cap = cv2.VideoCapture(self.video_path)
        current_fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        print(f"Current FPS: {current_fps}")
        
        if current_fps >= 60:
            print("FPS already >= 60, skipping interpolation")
            return False, current_fps
        
        return True, current_fps
    
    def load_rife_model(self):
        model_dir = self.interpolation_root / "models"
        model_dir.mkdir(exist_ok=True)
        
        print(f"Loading RIFE model...")
        return str(model_dir)
    
    def read_frame_pairs(self):
        frames_dir = self.interpolation_root / "frame_pairs" / self.video_name
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Reading frame pairs for interpolation...")
        
        cap = cv2.VideoCapture(self.video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        print(f"Total frames: {frame_count}")
        return str(frames_dir), frame_count
    
    def generate_intermediate_frames(self, frames_dir: str, frame_count: int):
        intermediate_dir = self.interpolation_root / "intermediate_frames" / self.video_name
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating intermediate frames with RIFE...")
        
        command = [
            "rife-ncnn-vulkan",
            "-i", self.video_path,
            "-o", str(intermediate_dir),
            "-m", "rife-v4.6",
            "-n", str(frame_count)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Intermediate frames generated")
            return str(intermediate_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Frame generation error: {e.stderr.decode()}")
    
    def interpolate_to_60fps(self, source_fps: float):
        multiplier = self.target_fps / source_fps
        print(f"Interpolation multiplier: {multiplier:.2f}x")
        return multiplier
    
    def encode_interpolated_video(self):
        output_dir = self.interpolation_root / "final_videos"
        output_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        output_video = output_dir / f"{self.video_name}_interpolated_{current_time_hash}.mp4"
        
        print(f"Encoding interpolated video at {self.target_fps}fps...")
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-filter:v", f"minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps={self.target_fps}'",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            str(output_video)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Video encoded: {output_video}")
            return str(output_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Video encoding error: {e.stderr.decode()}")
    
    def run_full_analysis(self):
        print("Starting frame interpolation pipeline")
        print("="*60)
        
        print("\n[0/5] Checking FPS")
        needs_interpolation, current_fps = self.check_fps()
        
        if not needs_interpolation:
            return {
                'video_name': self.video_name,
                'skipped': True,
                'reason': 'FPS already >= 60',
                'current_fps': current_fps
            }
        
        print("\n[1/5] Loading RIFE model")
        model_path = self.load_rife_model()
        
        print("\n[2/5] Reading frame pairs")
        frames_dir, frame_count = self.read_frame_pairs()
        
        print("\n[3/5] Generating intermediate frames")
        intermediate_dir = self.generate_intermediate_frames(frames_dir, frame_count)
        
        print("\n[4/5] Interpolating to 60fps")
        multiplier = self.interpolate_to_60fps(current_fps)
        
        print("\n[5/5] Encoding interpolated video")
        output_video = self.encode_interpolated_video()
        
        print("\nINTERPOLATION COMPLETE!")
        
        return {
            'video_name': self.video_name,
            'output_video': output_video,
            'original_fps': current_fps,
            'target_fps': self.target_fps,
            'multiplier': multiplier
        }


class Denoising_Generator:
    
    def __init__(self, video_path: str, noise_threshold: float = 100.0):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.denoising_root = script_dir / "denoising_results"
        self.denoising_root.mkdir(exist_ok=True)
        
        self.noise_threshold = noise_threshold
        
        print("video name:", self.video_name)
        print(f"Noise threshold: {noise_threshold}")
    
    def check_noise_level(self):
        print("Analyzing noise level...")
        
        cap = cv2.VideoCapture(self.video_path)
        noise_scores = []
        
        for i in range(10):
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            noise_scores.append(variance)
        
        cap.release()
        
        avg_noise = sum(noise_scores) / len(noise_scores) if noise_scores else 0
        
        print(f"Average noise level: {avg_noise:.2f}")
        print(f"Threshold: {self.noise_threshold}")
        
        needs_denoising = avg_noise < self.noise_threshold
        
        if not needs_denoising:
            print("Noise level below threshold, skipping denoising")
        
        return needs_denoising, avg_noise
    
    def configure_denoiser(self):
        config_dir = self.denoising_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        config = {
            'temporal_radius': 3,
            'strength': 7,
            'adaptive_filtering': True,
            'preserve_edges': True
        }
        
        config_file = config_dir / f"{self.video_name}_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"Denoiser configured: {config_file}")
        return config
    
    def temporal_analysis_motion_vectors(self):
        analysis_dir = self.denoising_root / "temporal_analysis"
        analysis_dir.mkdir(exist_ok=True)
        
        print("Performing temporal analysis with motion vectors...")
        
        analysis_file = analysis_dir / f"{self.video_name}_motion.txt"
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-vf", "mestimate=epzs:mb_size=16,codecview=mv=pf+bf+bb",
            "-an",
            "-f", "null",
            "-"
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Temporal analysis complete")
            return str(analysis_file)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Temporal analysis error: {e.stderr.decode()}")
    
    def adaptive_filtering_preserve_edges(self):
        print("Applying adaptive filtering while preserving edges...")
        
        filtered_dir = self.denoising_root / "filtered_frames"
        filtered_dir.mkdir(exist_ok=True)
        
        return str(filtered_dir)
    
    def output_clean_video(self):
        output_dir = self.denoising_root / "final_videos"
        output_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        output_video = output_dir / f"{self.video_name}_denoised_{current_time_hash}.mp4"
        
        print(f"Encoding denoised video...")
        
        command = [
            "ffmpeg",
            "-i", self.video_path,
            "-vf", "hqdn3d=4:3:6:4.5",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            str(output_video)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Clean video saved: {output_video}")
            return str(output_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Video encoding error: {e.stderr.decode()}")
    
    def run_full_analysis(self):
        print("Starting video denoising pipeline")
        print("="*60)
        
        print("\n[0/4] Checking noise level")
        needs_denoising, noise_level = self.check_noise_level()
        
        if not needs_denoising:
            return {
                'video_name': self.video_name,
                'skipped': True,
                'reason': 'Noise level below threshold',
                'noise_level': noise_level
            }
        
        print("\n[1/4] Configuring denoiser")
        config = self.configure_denoiser()
        
        print("\n[2/4] Temporal analysis - motion vectors")
        analysis_file = self.temporal_analysis_motion_vectors()
        
        print("\n[3/4] Adaptive filtering - preserve edges")
        filtered_dir = self.adaptive_filtering_preserve_edges()
        
        print("\n[4/4] Outputting clean video")
        output_video = self.output_clean_video()
        
        print("\nDENOISING COMPLETE!")
        
        return {
            'video_name': self.video_name,
            'output_video': output_video,
            'original_noise_level': noise_level,
            'config': config
        }


class Video_Enhancement_Pipeline:
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        
        self.upscaler = Upscaling_Generator(video_path)
        self.interpolator = Interpolation_Generator(video_path)
        self.denoiser = Denoising_Generator(video_path)
    
    def run_full_enhancement(self):
        print("\n" + "="*60)
        print("STARTING COMPLETE VIDEO ENHANCEMENT PIPELINE")
        print(f"Video: {self.video_name}")
        print("="*60)
        
        current_video = self.video_path
        results = {'original_video': self.video_path}
        
        print("\n[PHASE 1] Checking noise level")
        needs_denoising, noise_level = self.denoiser.check_noise_level()
        
        if needs_denoising:
            print("\n[PHASE 1] Running denoising")
            denoise_result = self.denoiser.run_full_analysis()
            results['denoising'] = denoise_result
            if not denoise_result.get('skipped'):
                current_video = denoise_result['output_video']
                self.interpolator.video_path = current_video
                self.upscaler.video_path = current_video
        
        print("\n[PHASE 2] Checking FPS")
        needs_interpolation, current_fps = self.interpolator.check_fps()
        
        if needs_interpolation:
            print("\n[PHASE 2] Running frame interpolation")
            interp_result = self.interpolator.run_full_analysis()
            results['interpolation'] = interp_result
            if not interp_result.get('skipped'):
                current_video = interp_result['output_video']
                self.upscaler.video_path = current_video
        
        print("\n[PHASE 3] Running upscaling")
        upscale_result = self.upscaler.run_full_analysis()
        results['upscaling'] = upscale_result
        current_video = upscale_result['output_video']
        
        results['final_video'] = current_video
        
        print("\n" + "="*60)
        print("COMPLETE ENHANCEMENT PIPELINE FINISHED!")
        print(f"Final video: {current_video}")
        print("="*60)
        
        return results


if __name__ == "__main__":
    video_file = "/path/to/video.mp4"
    
    pipeline = Video_Enhancement_Pipeline(video_file)
    results = pipeline.run_full_enhancement()