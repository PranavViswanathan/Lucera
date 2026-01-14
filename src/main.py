import os
import sys
import datetime
import json
import logging
from pathlib import Path
from typing import Dict, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from utility_classes.video_analysis import Analytics_Generator
    from utility_classes.caption_generation import Caption_Generator
    from utility_classes.video_enchancers import Video_Enhancement_Pipeline
    from utility_classes.packaging_generator import HLS_Packaging_Generator
    from utility_classes.VMAF import VMAF_Calculator, Quality_Metrics_Generator
except ImportError as e:
    print(f"Error importing utility classes: {e}")
    print("Please ensure you are running this from the project root or src directory.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger('VideoPipeline')

class VideoPipeline:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.path = Path(video_path)
        
        if not self.path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        self.video_name = self.path.stem
        self.results = {
            'original_video': str(self.path.absolute()),
            'start_time': datetime.datetime.now().isoformat(),
            'stages': {}
        }
        
    def run(self) -> Dict:
        logger.info(f"Starting pipeline for: {self.video_name}")
        
        try:
            self._run_analysis()
            
            self._run_captioning()
            
            enhanced_video_path = self._run_enhancement()
            
            self._run_packaging(enhanced_video_path)
            
            self._run_quality_check(enhanced_video_path)
            
            self._generate_report()
            
            logger.info("Pipeline completed successfully!")
            return self.results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            raise

    def _run_analysis(self):
        logger.info("STAGE 1: Video Analysis")
        analytics = Analytics_Generator(self.video_path)
        analysis_result = analytics.run_full_analysis()
        self.results['stages']['analysis'] = analysis_result
        logger.info("Analysis complete")

    def _run_captioning(self):
        logger.info("STAGE 2: Caption Generation")
        captions = Caption_Generator(self.video_path, model_size="base")
        caption_result = captions.run_full_analysis(keep_audio=False)
        self.results['stages']['captioning'] = caption_result
        logger.info("Captioning complete")

    def _run_enhancement(self) -> str:
        logger.info("STAGE 3: Video Enhancement")
        enhancer = Video_Enhancement_Pipeline(self.video_path)
        enhancement_result = enhancer.run_full_enhancement()
        self.results['stages']['enhancement'] = enhancement_result
        
        enhanced_video = enhancement_result.get('final_video')
        if not enhanced_video:
            logger.warning("Could not find 'final_video' in enhancement results. Checking sub-generators...")
          
            enhanced_video = self.video_path
            
        logger.info(f"Enhancement complete. Enhanced video: {enhanced_video}")
        return enhanced_video

    def _run_packaging(self, video_path: str):
        logger.info("STAGE 4: HLS Packaging")
        packager = HLS_Packaging_Generator(video_path)
        package_result = packager.run_full_analysis()
        self.results['stages']['packaging'] = package_result
        logger.info("Packaging complete")

    def _run_quality_check(self, enhanced_video_path: str):
        logger.info("STAGE 5: Quality Verification (VMAF)")
        if os.path.abspath(self.video_path) == os.path.abspath(enhanced_video_path):
            logger.info("Enhanced video identifies as original. Skipping VMAF check significantly.")
            self.results['stages']['quality'] = {"status": "skipped", "reason": "No enhancement performed"}
            return

        vmaf_calc = VMAF_Calculator(
            reference_video=self.video_path,
            enhanced_video=enhanced_video_path
        )
        quality_result = vmaf_calc.run_full_analysis()
        self.results['stages']['quality'] = quality_result
        logger.info("Quality check complete")

    def _generate_report(self):
        logger.info("STAGE 6: Final Reporting")
        enhanced_res = self.results['stages'].get('enhancement', {})
        enhanced_video = enhanced_res.get('final_video', self.video_path)
        
        quality_metrics = self.results['stages'].get('quality', {})
        metrics_gen = Quality_Metrics_Generator()
        try:
            audio_path = metrics_gen.extract_audio(enhanced_video)
            
            delivery_video = metrics_gen.generate_delivery_video(enhanced_video, audio_path)
            
            report_path, report_data = metrics_gen.create_final_report(
                original_video=self.video_path,
                enhanced_video=enhanced_video,
                delivery_video=delivery_video,
                quality_metrics=quality_metrics,
                audio_path=audio_path
            )
            
            self.results['final_report_path'] = str(report_path)
            self.results['stages']['final_report_data'] = report_data

            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                
        except Exception as e:
            logger.warning(f"Could not generate full visual report: {e}")
            report_file = f"pipeline_report_{self.video_name}.json"
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=4, default=str)
            self.results['final_report_path'] = report_file

        self.results['end_time'] = datetime.datetime.now().isoformat()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/main.py <video_file_path>")
        sys.exit(1)
        
    video_file = sys.argv[1]
    
    if not os.path.exists(video_file):
        print(f"Error: File {video_file} not found.")
        sys.exit(1)
        
    pipeline = VideoPipeline(video_file)
    pipeline.run()
