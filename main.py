import os
import sys
import numpy as np
import logging
import threading
import time
import shutil
import traceback

from moviepy import VideoFileClip, CompositeVideoClip
import subprocess

if len(sys.argv) > 1:
    file = sys.argv[1]
    arg = sys.argv[2:]
else:
    sys.exit("\33[31mno arg!\33[0m, --help to help")

if "--help" in sys.argv or "-help" in sys.argv or "-h" in sys.argv:
    print(f"""
ZSV [FAILE] [COMMAND] [OPTIONS] [ARG]
command:
 \33[34m-\33[0m info - информация об видео
 \33[34m-\33[0m optimization (opt) - сжение видео в %
 \33[34m-\33[0m without_audio - удаление аудио   
 \33[34m-\33[0m metadata - работа с мета данными       

arg:
 \33[34m-\33[0m file_name - имя нового сохранаяемого файла, применение:  file_name=new_video.mp4. по умолчанию output.mp4
""")
    exit(0)

bitrate=None

logging.getLogger("moviepy").setLevel(logging.ERROR)

if os.name == "nt":
    if not shutil.which("ffmpeg"): # применимо лиш для релиза под винду
        ffmpeg_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'ffmpeg', 'ffmpeg.exe')
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
else:
    ffmpeg_path="ffmpeg"

in_video_path = os.path.join(os.getcwd(), file)
filesize = os.path.getsize(in_video_path)  # байты
save_file_name="output.mp4"

clip = VideoFileClip(in_video_path)

fps = clip.fps

command = arg[0].lower().replace(' ', '')

def meta_data_read()->str:
    subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', "-i", in_video_path, '-f', 'ffmetadata', f'temp_({tt}).tmp'])
    with open(f'temp_({tt}).tmp', 'r') as f:
        data=f.read()
    os.remove(f'temp_({tt}).tmp')
    return data

if len(arg)>2:
    if arg[2].startswith("file_name"):
        name = arg[2].split("=")
        if len(name)>1:
            save_file_name=name[1]

if command == "optimization" or command == "opt":
    procent=int(arg[1].replace('%', '')) 
    width = round(clip.size[0]/100 * (100 - procent))
    height = round(clip.size[1]/100 * (100 - procent))
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
    relust=subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', in_video_path], capture_output=True, text=True)
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
    exit(0)

elif command == "without_audio":
    subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y', "-i", in_video_path, "-c:v", "copy", "-an", save_file_name], check=True)
    exit(0)

elif command == "metadata":
    tt=time.time()
    if len(arg)>1:
        if arg[1]=="read":
            print(meta_data_read())
            exit()
        elif '=' in arg[1] and arg[1].split("=")[0] in ['title', 'author', 'album_artist', 'composer', 'album', 'year', 'encoding_tool', 'comment', 'genre', 'copyright', 'grouping', 'lyrics', 'description', 'synopsis', 'show', 'episode_id', 'network', 'keywords', 'episode_sort', 'season_number', 'media_type', 'hd_video', 'gapless_playback', 'compilation', 'track']: 
                w_data=arg[1]
        else:
            print(f"\33[31mERROR не коректный аргумента ({arg[1]} не существует или он не коректен)\33[0m")
            exit(1)

        subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y', "-i", in_video_path, '-metadata', w_data, save_file_name], capture_output=True)
    else:
        print(meta_data_read())
    exit(0)


loading=True

def compilation_video():
    global loading
    try:
        file = CompositeVideoClip([clip])
        file.write_videofile(save_file_name,
                        fps=fps, logger=None, threads=5)
        subprocess.run([ffmpeg_path, '-i', save_file_name, '-i', in_video_path, '-map', '0', '-map_metadata', '1', '-y', '-c', 'copy', save_file_name])
    except Exception:
        loading=False
        traceback.print_exc()    
    loading=False

def progres_barr():
    timer=time.time()
    while loading:
        print(f"|                {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"/                {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"—                {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
        print(f"\\                {round(time.time()-timer, 1)}s", end="\r")
        time.sleep(0.5)
    print("\33[32mcompleted!\33[0m")

t1 = threading.Thread(target=compilation_video, daemon=True)
t2 = threading.Thread(target=progres_barr, daemon=True)

t1.start()
t2.start()

t1.join()
t2.join()