import os
import sys
import logging
import threading
import time
import shutil
import traceback
import json

from moviepy import VideoFileClip, CompositeVideoClip, CompositeAudioClip, AudioFileClip
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
 \33[34m-\33[0m info - информация об видео.
 \33[34m-\33[0m optimization (opt) - сжение видео в %. 1 аргумент после команды это % сжатия (целое цисло)
 \33[34m-\33[0m without_audio - удаление аудио.
 \33[34m-\33[0m metadata - работа с мета данными. (без аргументов для чтения)
        аргументы:
          1 аргумент после команды это изменяемый порамитер (title, artist, date и т.д) с вносимыми данными. пример: venv/bin/python3 main.py test.mp4 metadata title=test_data
 \33[34m-\33[0m to - преобразование формата и переименование(опционально). 1 аргумент это имя файла с преобразованым фарматом
 \33[34m-\33[0m extrude_audio - извлечение аудио. 1 агумент название сохраняемого аудио файла
 \33[34m-\33[0m cut - образка видео от-до. пример venv/bin/python3 main.py test.mp4 cut 0:0-0:15
          
arg:
 \33[34m-\33[0m file_name - имя нового сохраняемого файла, применение:  file_name=new_video.mp4. по умолчанию output.mp4
""")
    sys.exit(0)

bitrate=None

logging.getLogger("moviepy").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

if os.name == "nt":
    if not shutil.which("ffmpeg"): # применимо лиш для релиза под винду
        ffmpeg_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'ffmpeg', 'ffmpeg.exe')
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
else:
    ffmpeg_path="ffmpeg"


def is_audio_or_video(path:str)->None|str:
    """определяет видео это или же аудио

    Args:
        path (str): название файла

    Returns:
        None|str: если `None` то не удалось прочитать если `unknown` то не известный файл если `video` то видео если `audio` то аудио
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-of", "json", path
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None  # не удалось прочитать файл
    info = json.loads(proc.stdout)
    streams = info.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    if has_video:
        return "video"
    if has_audio:
        return "audio"
    return "unknown"

def meta_data_read()->str:
    subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', "-i", in_file_path, '-f', 'ffmetadata', f'temp_({tt}).tmp'])
    with open(f'temp_({tt}).tmp', 'r') as f:
        data=f.read()
    os.remove(f'temp_({tt}).tmp')
    return data

def compilation_video():
    global loading
    try:
        if clip:
            temp =  f'temp_({time.monotonic()}){os.path.splitext(save_file_name)[1]}'
            file = CompositeVideoClip([clip])
            file.write_videofile(temp,
                            fps=fps, logger=None, threads=5)
            
            subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error',
            '-i', temp, '-i', in_file_path, '-map', '0', '-map_metadata', '1', '-y', '-c', 'copy', save_file_name])
            os.remove(temp)

    except Exception:
        loading=False
        traceback.print_exc()    
    loading=False

def audio_comfress(clip:VideoFileClip, file_name:str):
    global loading
    try:
        if clip:
            audioclip = CompositeAudioClip([clip.audio])
            audioclip.write_audiofile(file_name, logger=None)
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

compilation = threading.Thread(target=compilation_video, daemon=True)
progres_barr_p = threading.Thread(target=progres_barr, daemon=True)


fps=1

in_file_path = os.path.join(os.getcwd(), file)
filesize = os.path.getsize(in_file_path)  # байты
save_file_name = f"output{os.path.splitext(in_file_path)[1]}"

file_type=is_audio_or_video(in_file_path)

clip=None

if file_type == "video":
    clip = VideoFileClip(in_file_path)
    fps = clip.fps


command = arg[0].lower().replace(' ', '')


if len(arg)>2:
    if arg[2].startswith("file_name"):
        name = arg[2].split("=")
        if len(name)>1:
            save_file_name=name[1]

if clip and command == "optimization" or command == "opt":
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

elif clip and command == "info":
    #получение кодека
    relust=subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', in_file_path], capture_output=True, text=True)
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
    sys.exit(0)

elif command == "without_audio":
    subprocess.run([ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y', "-i", in_file_path, "-c:v", "copy", "-an", save_file_name], check=True)
    sys.exit(0)

elif command == "metadata":
    tt=time.time()
    if len(arg)>1:
        if arg[1]=="read":
            print(meta_data_read())
            sys.exit(0)
        elif '=' in arg[1] and arg[1].split("=")[0] in ['title', 'artist', 'author', 'album_artist', 'composer', 'album', 'year', 'encoding_tool', 'comment', 'genre', 'copyright', 'grouping', 'lyrics', 'description', 'synopsis', 'show', 'episode_id', 'network', 'keywords', 'episode_sort', 'season_number', 'media_type', 'hd_video', 'gapless_playback', 'compilation', 'track']: 
                w_data=arg[1]
        else:
            print(f"\33[31mERROR не коректный аргумента ({arg[1]} не существует или он не коректен)\33[0m")
            sys.exit(1)
        
        subprocess.run([ffmpeg_path, '-fflags', '+genpts', '-hide_banner', '-loglevel', 'error', '-y', "-i", in_file_path, '-c', 'copy', '-metadata', w_data, f"temp_{tt}{os.path.splitext(in_file_path)[1]}"], capture_output=True)
        os.replace(f"temp_{tt}{os.path.splitext(in_file_path)[1]}", save_file_name)
    else:
        print(meta_data_read())
    sys.exit(0)

elif command == "to":
    if len(arg)>0:
        if '.' in arg[1]: 
            save_file_name = arg[1]
        else:
            print(f"\33[31mERROR в новом имени нет расширения!\33[0m")
    else:
        print(f"\33[31mERROR нет аргумента\33[0m")

elif clip and command == "extrude_audio":
    if clip.audio:
        if len(arg)>1:
            loading=True
            audio_comfress_p = threading.Thread(target=audio_comfress, args=(clip, arg[1]), daemon=True)
            audio_comfress_p.start()
            progres_barr_p.start()
            audio_comfress_p.join()
            progres_barr_p.join()
        else:
            print(f"\33[31mERROR нет аргумента\33[0m")
    else:
        print("похоже в видео нет аудио дорожек")
    sys.exit(0)

elif clip and command == "cut":
    if len(arg)>1 and '-' in arg[1]:
        start = arg[1].split('-')[0]
        end = arg[1].split('-')[1]
    else:
        print(f"\33[31mERROR нет аргумента или он не коректен\33[0m")
        sys.exit(1)

    clip = clip.subclipped(start, end)

else:
    print(f"такой команды({command}) нет или она не удалетворительна")
    sys.exit(0)

loading=True


compilation.start()
progres_barr_p.start()

compilation.join()
progres_barr_p.join()
