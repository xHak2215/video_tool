import os
import sys
import numpy as np

from moviepy import VideoFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) > 1:
    file = sys.argv[1]
    arg = sys.argv[2:]
else:
    sys.exit("\33[31mno arg!\33[0m, --help to help")

if "--help" in sys.argv or "-help" in sys.argv or "-h" in sys.argv:
    print(f"""
ZSV [FAILE] [COMMAND] [OPTIONS]
 \33[34m-\33[0m info - информация об видео
 \33[34m-\33[0m optimization (opt) - сжение видео в %

""")
    exit(0)

bitrate=None

in_video_path = os.path.join(os.getcwd(), file)
filesize = os.path.getsize(in_video_path)  # байты

clip = VideoFileClip(in_video_path)

fps = clip.fps

command = arg[0].lower().replace(' ', '')

if command == "optimization" or command == "opt":
    procent=int(arg[1].replace('%', '')) 
    width = clip.size[0]/100 * (100 - procent)
    height = clip.size[1]/100 * (100 - procent)
    fps = round((fps/100 * (100 - procent))) + 1
    duration = clip.duration            # секунды (float)
    avg_bitrate_bps = (filesize * 8) / duration

    audio = clip.audio
    clip.without_audio()
    audio.with_duration(clip.duration)
    clip.with_audio(audio)

    print(f"width:{width}, height:{height}. fps:{fps}")

    clip.with_fps(fps)
    clip = clip.resized(width=width, height=height)

elif command == "info":
    print(f"Длительность: {clip.duration} секунд")
    print(f"разширение: {clip.size}")
    print(f"вес: {filesize} байт")
    print(f"FPS: {round(clip.fps)}")
    exit()


file = CompositeVideoClip([clip])
file.write_videofile("output.mp4",
                    fps=fps)
