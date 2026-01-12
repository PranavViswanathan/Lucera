
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utility_classes.video_analysis import Analytics_Generator

# obj = Analytics_Generator("/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_1.MP4")
# results = obj.run_full_analysis()

obj2 = Analytics_Generator("/Users/pranavviswanathan/Programming/Lucera/practice_videos/practice_2.MP4")
results = obj2.run_full_analysis()