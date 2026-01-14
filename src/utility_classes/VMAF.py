import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import datetime
import hashlib
import json
import csv
import os


class VMAF_Calculator:
    
    def __init__(self, reference_video: str, enhanced_video: str):
        self.reference_video = reference_video
        self.enhanced_video = enhanced_video
        
        ref_path = Path(reference_video)
        self.video_name = ref_path.stem
        
        script_dir = Path(__file__).parent
        self.vmaf_root = script_dir / "vmaf_results"
        self.vmaf_root.mkdir(exist_ok=True)
        
        print("Reference video:", reference_video)
        print("Enhanced video:", enhanced_video)
    
    def calculate_vmaf(self):
        vmaf_dir = self.vmaf_root / "vmaf_scores"
        vmaf_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        vmaf_json = vmaf_dir / f"{self.video_name}_vmaf_{current_time_hash}.json"
        
        print("Calculating VMAF score...")
        
        command = [
            "ffmpeg",
            "-i", self.enhanced_video,
            "-i", self.reference_video,
            "-lavfi",
            f"[0:v]setpts=PTS-STARTPTS[main];[1:v]setpts=PTS-STARTPTS[ref];[main][ref]libvmaf=log_fmt=json:log_path={vmaf_json}:n_threads=4",
            "-f", "null",
            "-"
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"VMAF calculation complete")
            
            with open(vmaf_json, 'r') as f:
                vmaf_data = json.load(f)
            
            pooled_metrics = vmaf_data.get('pooled_metrics', {})
            vmaf_score = pooled_metrics.get('vmaf', {}).get('mean', 0)
            
            print(f"VMAF Score: {vmaf_score:.2f}")
            
            return str(vmaf_json), vmaf_score
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"VMAF calculation error: {e.stderr.decode()}")
    
    def calculate_psnr(self):
        psnr_dir = self.vmaf_root / "psnr_scores"
        psnr_dir.mkdir(exist_ok=True)
        
        psnr_log = psnr_dir / f"{self.video_name}_psnr.log"
        
        print("Calculating PSNR...")
        
        command = [
            "ffmpeg",
            "-i", self.enhanced_video,
            "-i", self.reference_video,
            "-lavfi",
            "psnr",
            "-f", "null",
            "-"
        ]
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            psnr_score = None
            for line in result.stderr.split('\n'):
                if 'average:' in line.lower():
                    parts = line.split('average:')
                    if len(parts) > 1:
                        psnr_str = parts[1].split()[0]
                        try:
                            psnr_score = float(psnr_str)
                        except ValueError:
                            pass
            
            if psnr_score is None:
                psnr_score = 0.0
            
            with open(psnr_log, 'w') as f:
                f.write(result.stderr)
            
            print(f"PSNR Score: {psnr_score:.2f} dB")
            
            return str(psnr_log), psnr_score
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PSNR calculation error: {e.stderr.decode()}")
    
    def calculate_ssim(self):
        ssim_dir = self.vmaf_root / "ssim_scores"
        ssim_dir.mkdir(exist_ok=True)
        
        ssim_log = ssim_dir / f"{self.video_name}_ssim.log"
        
        print("Calculating SSIM...")
        
        command = [
            "ffmpeg",
            "-i", self.enhanced_video,
            "-i", self.reference_video,
            "-lavfi",
            "ssim",
            "-f", "null",
            "-"
        ]
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            ssim_score = None
            for line in result.stderr.split('\n'):
                if 'All:' in line:
                    parts = line.split('All:')
                    if len(parts) > 1:
                        ssim_str = parts[1].split()[0]
                        try:
                            ssim_score = float(ssim_str)
                        except ValueError:
                            pass
            
            if ssim_score is None:
                ssim_score = 0.0
            
            with open(ssim_log, 'w') as f:
                f.write(result.stderr)
            
            print(f"SSIM Score: {ssim_score:.4f}")
            
            return str(ssim_log), ssim_score
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"SSIM calculation error: {e.stderr.decode()}")
    
    def generate_vmaf_report(self, vmaf_json: str, vmaf_score: float, psnr_score: float, ssim_score: float):
        report_dir = self.vmaf_root / "quality_reports"
        report_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        json_report = report_dir / f"{self.video_name}_report_{current_time_hash}.json"
        csv_report = report_dir / f"{self.video_name}_report_{current_time_hash}.csv"
        
        report_data = {
            'video_name': self.video_name,
            'reference_video': self.reference_video,
            'enhanced_video': self.enhanced_video,
            'timestamp': datetime.datetime.now().isoformat(),
            'metrics': {
                'vmaf': {
                    'score': vmaf_score,
                    'scale': '0-100',
                    'threshold': 75,
                    'status': 'PASS' if vmaf_score >= 75 else 'FAIL'
                },
                'psnr': {
                    'score': psnr_score,
                    'unit': 'dB',
                    'status': 'PASS' if psnr_score >= 30 else 'FAIL'
                },
                'ssim': {
                    'score': ssim_score,
                    'scale': '0-1',
                    'status': 'PASS' if ssim_score >= 0.9 else 'FAIL'
                }
            }
        }
        
        with open(json_report, 'w') as f:
            json.dump(report_data, f, indent=4)
        
        with open(csv_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Score', 'Status'])
            writer.writerow(['VMAF', f"{vmaf_score:.2f}", report_data['metrics']['vmaf']['status']])
            writer.writerow(['PSNR', f"{psnr_score:.2f} dB", report_data['metrics']['psnr']['status']])
            writer.writerow(['SSIM', f"{ssim_score:.4f}", report_data['metrics']['ssim']['status']])
        
        print(f"\nQuality Report (JSON): {json_report}")
        print(f"Quality Report (CSV): {csv_report}")
        
        return str(json_report), str(csv_report), report_data
    
    def run_full_analysis(self):
        print("Starting quality metrics analysis")
        print("="*60)
        
        print("\n[1/4] Calculating VMAF")
        vmaf_json, vmaf_score = self.calculate_vmaf()
        
        print("\n[2/4] Calculating PSNR")
        psnr_log, psnr_score = self.calculate_psnr()
        
        print("\n[3/4] Calculating SSIM")
        ssim_log, ssim_score = self.calculate_ssim()
        
        print("\n[4/4] Generating quality report")
        json_report, csv_report, report_data = self.generate_vmaf_report(
            vmaf_json, vmaf_score, psnr_score, ssim_score
        )
        
        print("\nQUALITY METRICS COMPLETE!")
        print(f"VMAF: {vmaf_score:.2f}/100 ({report_data['metrics']['vmaf']['status']})")
        print(f"PSNR: {psnr_score:.2f} dB ({report_data['metrics']['psnr']['status']})")
        print(f"SSIM: {ssim_score:.4f} ({report_data['metrics']['ssim']['status']})")
        
        return {
            'video_name': self.video_name,
            'vmaf_json': vmaf_json,
            'vmaf_score': vmaf_score,
            'psnr_score': psnr_score,
            'ssim_score': ssim_score,
            'json_report': json_report,
            'csv_report': csv_report,
            'overall_status': report_data
        }


class Quality_Metrics_Generator:
    
    def __init__(self):
        script_dir = Path(__file__).parent
        self.metrics_root = script_dir / "final_quality_metrics"
        self.metrics_root.mkdir(exist_ok=True)
    
    def extract_audio(self, video_path: str):
        audio_dir = self.metrics_root / "extracted_audio"
        audio_dir.mkdir(exist_ok=True)
        
        video_name = Path(video_path).stem
        audio_output = audio_dir / f"{video_name}_audio.aac"
        
        print(f"Extracting audio from video...")
        
        command = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "copy",
            str(audio_output)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Audio extracted: {audio_output}")
            return str(audio_output)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Audio extraction failed: {e.stderr.decode()}")
            return None
    
    def generate_delivery_video(self, enhanced_video: str, audio_path: Optional[str] = None):
        delivery_dir = self.metrics_root / "delivery_videos"
        delivery_dir.mkdir(exist_ok=True)
        
        video_name = Path(enhanced_video).stem
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        delivery_video = delivery_dir / f"{video_name}_delivery_{current_time_hash}.mp4"
        
        print("Generating final delivery video...")
        
        if audio_path and Path(audio_path).exists():
            command = [
                "ffmpeg",
                "-i", enhanced_video,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(delivery_video)
            ]
        else:
            command = [
                "ffmpeg",
                "-i", enhanced_video,
                "-c:v", "copy",
                str(delivery_video)
            ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Delivery video created: {delivery_video}")
            return str(delivery_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Delivery video creation error: {e.stderr.decode()}")
    
    def create_final_report(
        self,
        original_video: str,
        enhanced_video: str,
        delivery_video: str,
        quality_metrics: Dict,
        audio_path: Optional[str] = None
    ):
        report_dir = self.metrics_root / "final_reports"
        report_dir.mkdir(exist_ok=True)
        
        video_name = Path(original_video).stem
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        final_report = report_dir / f"{video_name}_final_report_{current_time_hash}.json"
        
        report = {
            'project_name': video_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'input': {
                'original_video': original_video
            },
            'output': {
                'enhanced_video': enhanced_video,
                'delivery_video': delivery_video,
                'audio_track': audio_path
            },
            'quality_metrics': {
                'vmaf': {
                    'score': quality_metrics.get('vmaf_score', 0),
                    'scale': '0-100',
                    'target': 75,
                    'status': 'PASS' if quality_metrics.get('vmaf_score', 0) >= 75 else 'FAIL'
                },
                'psnr': {
                    'score': quality_metrics.get('psnr_score', 0),
                    'unit': 'dB',
                    'target': 30,
                    'status': 'PASS' if quality_metrics.get('psnr_score', 0) >= 30 else 'FAIL'
                },
                'ssim': {
                    'score': quality_metrics.get('ssim_score', 0),
                    'scale': '0-1',
                    'target': 0.9,
                    'status': 'PASS' if quality_metrics.get('ssim_score', 0) >= 0.9 else 'FAIL'
                }
            },
            'overall_quality': 'EXCELLENT' if quality_metrics.get('vmaf_score', 0) >= 90 else
                             'GOOD' if quality_metrics.get('vmaf_score', 0) >= 75 else
                             'ACCEPTABLE' if quality_metrics.get('vmaf_score', 0) >= 60 else
                             'POOR'
        }
        
        with open(final_report, 'w') as f:
            json.dump(report, f, indent=4)
        
        print(f"\nFinal report saved: {final_report}")
        
        return str(final_report), report


if __name__ == "__main__":
    reference_video = "/path/to/original.mp4"
    enhanced_video = "/path/to/enhanced.mp4"
    
    vmaf = VMAF_Calculator(reference_video, enhanced_video)
    result = vmaf.run_full_analysis()
    
    metrics_gen = Quality_Metrics_Generator()
    audio = metrics_gen.extract_audio(reference_video)
    delivery = metrics_gen.generate_delivery_video(enhanced_video, audio)
    report_path, report = metrics_gen.create_final_report(
        reference_video, 
        enhanced_video, 
        delivery, 
        result, 
        audio
    )