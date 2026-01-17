import os
import sys
import numpy as np
import logging
import threading
import time
import shutil

from moviepy import VideoFileClip, CompositeVideoClip
import subprocess

if len(sys.argv) > 1:
    file = sys.argv[1]
    arg = sys.argv[2:]
else:
    sys.exit("\33[31mno arg!\33[0m, --help to help")

if "--help" in sys.argv or "-help" in sys.argv or "-h" in sys.argv:
    print(f"""
ZSV [FAILE] [COMMAND] [OPTIONS]
command:
 \33[34m-\33[0m info - информация об видео
 \33[34m-\33[0m optimization (opt) - сжение видео в %

""")
    exit(0)

bitrate=None
logging.getLogger("moviepy").setLevel(logging.ERROR)

if os.name == "nt":
    if not shutil.which("ffmpeg"):
        ffmpeg_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'ffmpeg', 'ffmpeg.exe')
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
else:
    ffmpeg_path="ffprobe"

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
    if audio:
        clip.without_audio()
        audio.with_duration(clip.duration)
        clip.with_audio(audio)

    print(f"info:  width:{width} height:{height} fps:{fps}")

    clip.with_fps(fps)
    clip = clip.resized(width=width, height=height)

elif command == "info":
    #получение кодека
    relust=subprocess.run([ffmpeg_path, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', in_video_path], capture_output=True, text=True)
    # удобный вывод веса
    if filesize//1_073_741_824 > 0:
        vsize=f"{round(filesize/1_073_741_824, 1)} ГБ"

    elif filesize//1_048_576 > 0:
        vsize=f"{round(filesize/1_048_576, 1)} МБ"

    elif filesize//1024 > 0:
        vsize=f"{round(filesize/1024, 1)} КБ"

    else:
        vsize=f"{filesize} Байт"

    print(f"Длительность: {clip.duration} секунд")
    print(f"разришение: {clip.size[0]}X{clip.size[1]}")
    print(f"вес: {vsize}")
    print(f"FPS: {round(clip.fps)}")
    print(f"кодек: {relust.stdout}")
    exit()

loading=True

def compilation_video():
    global loading
    file = CompositeVideoClip([clip])
    file.write_videofile("output.mp4",
                        fps=fps, logger=None)
    loading=False

def progres_barr():
    timer=time.time()
    while loading:
        print(f"|               {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"/               {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"—               {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"\\               {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
    print("\33[32mcompleted!\33[0m")

t1 = threading.Thread(target=compilation_video, daemon=True)
t2 = threading.Thread(target=progres_barr, daemon=True)

t1.start()
t2.start()

t1.join()
t2.join()