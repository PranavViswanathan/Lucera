import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import datetime
import hashlib
import json
import os


class HLS_Packaging_Generator:
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        self.video_format = path.suffix
        
        script_dir = Path(__file__).parent
        self.hls_root = script_dir / "hls_results"
        self.hls_root.mkdir(exist_ok=True)
        
        self.encoding_profiles = [
            {'resolution': '1920x1080', 'bitrate': '5000k', 'name': '1080p'},
            {'resolution': '1280x720', 'bitrate': '2800k', 'name': '720p'},
            {'resolution': '854x480', 'bitrate': '1400k', 'name': '480p'},
            {'resolution': '640x360', 'bitrate': '800k', 'name': '360p'}
        ]
        
        print("video name:", self.video_name)
        print("HLS packaging initialized")
    
    def ffmpeg_merge(self, video_sources: List[str]):
        merge_dir = self.hls_root / "merged_output"
        merge_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        merged_video = merge_dir / f"{self.video_name}_merged_{current_time_hash}.mp4"
        
        print("Merging video sources with FFmpeg...")
        
        if len(video_sources) == 1:
            command = [
                "ffmpeg",
                "-i", video_sources[0],
                "-c", "copy",
                str(merged_video)
            ]
        else:
            filter_complex = ""
            for i in range(len(video_sources)):
                filter_complex += f"[{i}:v]"
            filter_complex += f"concat=n={len(video_sources)}:v=1:a=0[outv]"
            
            command = ["ffmpeg"]
            for source in video_sources:
                command.extend(["-i", source])
            command.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                str(merged_video)
            ])
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Video merged: {merged_video}")
            return str(merged_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg merge error: {e.stderr.decode()}")
    
    def create_final_enhanced_video(self, merged_video: str):
        final_dir = self.hls_root / "final_enhanced"
        final_dir.mkdir(exist_ok=True)
        
        final_video = final_dir / f"{self.video_name}_final_1080p_60fps.mp4"
        
        print("Creating final enhanced video: 1080p @ 60fps, Clean, Sharp")
        
        command = [
            "ffmpeg",
            "-i", merged_video,
            "-vf", "scale=1920:1080:flags=lanczos,unsharp=5:5:1.0:5:5:0.0",
            "-r", "60",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(final_video)
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"Final enhanced video: {final_video}")
            return str(final_video)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Final video creation error: {e.stderr.decode()}")
    
    def create_hls_package(self, final_video: str):
        hls_dir = self.hls_root / "hls_package" / self.video_name
        hls_dir.mkdir(parents=True, exist_ok=True)
        
        print("Creating HLS package...")
        
        variants_dir = hls_dir / "variants"
        variants_dir.mkdir(exist_ok=True)
        
        return str(hls_dir), str(variants_dir)
    
    def adaptive_bitrate_encoding(self, final_video: str, variants_dir: str):
        print("Encoding adaptive bitrate ladder...")
        
        variant_info = []
        
        for profile in self.encoding_profiles:
            variant_name = profile['name']
            variant_path = Path(variants_dir) / variant_name
            variant_path.mkdir(exist_ok=True)
            
            playlist_name = f"{variant_name}.m3u8"
            segment_pattern = f"{variant_name}_%03d.ts"
            
            print(f"  Encoding {variant_name} @ {profile['bitrate']}...")
            
            command = [
                "ffmpeg",
                "-i", final_video,
                "-vf", f"scale={profile['resolution']}:flags=lanczos",
                "-c:v", "libx264",
                "-b:v", profile['bitrate'],
                "-maxrate", profile['bitrate'],
                "-bufsize", str(int(profile['bitrate'].replace('k', '')) * 2) + 'k',
                "-preset", "medium",
                "-g", "60",
                "-sc_threshold", "0",
                "-keyint_min", "60",
                "-hls_time", "6",
                "-hls_playlist_type", "vod",
                "-hls_segment_filename", str(variant_path / segment_pattern),
                str(variant_path / playlist_name)
            ]
            
            try:
                subprocess.run(command, check=True, capture_output=True)
                
                variant_info.append({
                    'name': variant_name,
                    'resolution': profile['resolution'],
                    'bitrate': profile['bitrate'],
                    'playlist': str(variant_path / playlist_name)
                })
                
                print(f"  ✓ {variant_name} encoded")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Encoding error for {variant_name}: {e.stderr.decode()}")
        
        return variant_info
    
    def generate_master_manifest(self, hls_dir: str, variant_info: List[Dict]):
        master_manifest = Path(hls_dir) / "master.m3u8"
        
        print("Generating master manifest (master.m3u8)...")
        
        with open(master_manifest, 'w') as f:
            f.write("#EXTM3U\n")
            f.write("#EXT-X-VERSION:3\n\n")
            
            for variant in variant_info:
                bandwidth = int(variant['bitrate'].replace('k', '')) * 1000
                resolution = variant['resolution']
                playlist_path = Path(variant['playlist']).relative_to(hls_dir)
                
                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}\n")
                f.write(f"{playlist_path}\n\n")
        
        print(f"Master manifest saved: {master_manifest}")
        return str(master_manifest)
    
    def run_full_analysis(self, video_sources: List[str] = None):
        print("Starting HLS packaging and adaptive bitrate encoding")
        print("="*60)
        
        if video_sources is None:
            video_sources = [self.video_path]
        
        print("\n[1/5] FFmpeg merge")
        merged_video = self.ffmpeg_merge(video_sources)
        
        print("\n[2/5] Creating final enhanced video (1080p @ 60fps)")
        final_video = self.create_final_enhanced_video(merged_video)
        
        print("\n[3/5] Setting up HLS package structure")
        hls_dir, variants_dir = self.create_hls_package(final_video)
        
        print("\n[4/5] Adaptive bitrate encoding ladder")
        variant_info = self.adaptive_bitrate_encoding(final_video, variants_dir)
        
        print("\n[5/5] Generating master manifest")
        master_manifest = self.generate_master_manifest(hls_dir, variant_info)
        
        print("\nHLS PACKAGING COMPLETE!")
        
        return {
            'video_name': self.video_name,
            'merged_video': merged_video,
            'final_video': final_video,
            'master_manifest': master_manifest,
            'variants': variant_info,
            'hls_directory': hls_dir
        }


class Complete_Video_Pipeline:
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        path = Path(video_path)
        self.video_name = path.stem
        
        script_dir = Path(__file__).parent
        self.pipeline_root = script_dir / "complete_pipeline_results"
        self.pipeline_root.mkdir(exist_ok=True)
    
    def run_full_pipeline(self):
        print("\n" + "="*60)
        print("STARTING COMPLETE VIDEO PROCESSING PIPELINE")
        print(f"Video: {self.video_name}")
        print("="*60)
        
        from video_analysis import Analytics_Generator
        from caption_generation import Caption_Generator
        from video_enhancers import Video_Enhancement_Pipeline
        
        results = {
            'original_video': self.video_path,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        print("\n" + "="*60)
        print("[STAGE 1] VIDEO ANALYTICS")
        print("="*60)
        analytics = Analytics_Generator(self.video_path)
        analytics_result = analytics.run_full_analysis()
        results['analytics'] = analytics_result
        
        print("\n" + "="*60)
        print("[STAGE 2] CAPTION GENERATION")
        print("="*60)
        captions = Caption_Generator(self.video_path, model_size="base", device="cpu")
        caption_result = captions.run_full_analysis(keep_audio=False)
        results['captions'] = caption_result
        
        print("\n" + "="*60)
        print("[STAGE 3] VIDEO ENHANCEMENT")
        print("="*60)
        enhancer = Video_Enhancement_Pipeline(self.video_path)
        enhancement_result = enhancer.run_full_enhancement()
        results['enhancement'] = enhancement_result
        
        print("\n" + "="*60)
        print("[STAGE 4] HLS PACKAGING & ADAPTIVE BITRATE")
        print("="*60)
        
        enhanced_video = enhancement_result.get('final_video', self.video_path)
        
        hls_packager = HLS_Packaging_Generator(enhanced_video)
        hls_result = hls_packager.run_full_analysis()
        results['hls'] = hls_result
        
        self._save_final_report(results)
        
        print("\n" + "="*60)
        print("COMPLETE PIPELINE FINISHED!")
        print("="*60)
        print(f"\nFinal outputs:")
        print(f"  Analytics: {len(results['analytics'])} metrics")
        print(f"  Captions: {caption_result['srt_path']}")
        print(f"  Enhanced Video: {enhanced_video}")
        print(f"  HLS Master: {hls_result['master_manifest']}")
        print(f"  Variants: {len(hls_result['variants'])} quality levels")
        
        return results
    
    def _save_final_report(self, results: Dict):
        report_dir = self.pipeline_root / "final_reports"
        report_dir.mkdir(exist_ok=True)
        
        current_time_string = datetime.datetime.now().isoformat()
        time_bits = current_time_string.encode('utf-8')
        hash_object = hashlib.sha256(time_bits)
        current_time_hash = hash_object.hexdigest()[:8]
        
        report_file = report_dir / f"{self.video_name}_report_{current_time_hash}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=4, default=str)
        
        print(f"\nFinal report saved: {report_file}")


if __name__ == "__main__":
    video_file = "/path/to/video.mp4"
    
    hls = HLS_Packaging_Generator(video_file)
    result = hls.run_full_analysis()
    
    pipeline = Complete_Video_Pipeline(video_file)
    full_results = pipeline.run_full_pipeline()