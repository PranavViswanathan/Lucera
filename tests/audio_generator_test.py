import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utility_classes.caption_generation import Caption_Generator

# Test 1: Practice video 1
# obj = Caption_Generator(
#     "/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_1.MP4",
#     model_size="base",
#     device="cpu"
# )
# results = obj.run_full_analysis(keep_audio=False)

# Test 2: Practice video 2
obj2 = Caption_Generator(
    "/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_2.MP4",
    model_size="base",
    device="cpu"
)
results = obj2.run_full_analysis(keep_audio=False)

# Test 3: Practice video 3
# obj3 = Caption_Generator(
#     "/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_3.mp4",
#     model_size="base",
#     device="cpu"
# )
# results = obj3.run_full_analysis(keep_audio=False)

# Test with different model size (more accurate but slower)
# obj_large = Caption_Generator(
#     "/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_2.MP4",
#     model_size="small",
#     device="cpu"
# )
# results_large = obj_large.run_full_analysis(keep_audio=True)

# Print results summary
print("\n" + "="*60)
print("TEST RESULTS")
print("="*60)
print(f"Video: {results['video_name']}")
print(f"Total segments: {results['segment_count']}")
print(f"Model used: {results['model_used']}")
print(f"\nOutput files:")
print(f"  SRT: {results['srt_path']}")
print(f"  VTT: {results['vtt_path']}")
if results['audio_path']:
    print(f"  Audio: {results['audio_path']}")