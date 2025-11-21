import yt_dlp
import os
import uuid
import time
import re

def download_video(url, output_folder, progress_callback=None):
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        local_id = str(uuid.uuid4())[:8]
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        ffmpeg_path = os.path.join(backend_dir, 'ffmpeg.exe')
        
        if not os.path.exists(ffmpeg_path):
            ffmpeg_location = None 
        else:
            ffmpeg_location = backend_dir

        last_update_time = [0] 

        def my_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                current_time = time.time()
                if current_time - last_update_time[0] > 0.3:
                    try:
                        p = d.get('_percent_str', '0%').replace('%','').strip()
                        progress_callback(p)
                        last_update_time[0] = current_time
                    except: pass

        # FASE 1: OBTENER INFO Y LIMPIAR TÍTULO
        with yt_dlp.YoutubeDL({'skip_download': True, 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get('title', f"video_{local_id}")
            clean_title = re.sub(r'[\\/:*?"<>|]', '', raw_title) 
        
        # Plantilla de salida final: [Título Limpio]_[ID_Local].mp4
        output_template = os.path.join(output_folder, f"{clean_title}_{local_id}.%(ext)s")

        # FASE 2: DESCARGAR (MODO TURBO Y CALIDAD LIMITADA)
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': ffmpeg_location,
            'progress_hooks': [my_hook],
            'noplaylist': True,
            'concurrent_fragment_downloads': 5,
        }

        cookies_path = os.path.join(backend_dir, 'cookies.txt')
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        else:
            ydl_opts['cookiesfrombrowser'] = ('chrome',)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = os.path.join(output_folder, f"{clean_title}_{local_id}.mp4")
            
            return {
                "status": "success",
                "path": filename,
                "title": clean_title, 
                "youtube_id": info.get('id'),
                "duration": info.get('duration', 0),
                "video_id": local_id
            }

    except Exception as e:
        msg = str(e)
        if "DPAPI" in msg:
             return {"status": "error", "message": "❌ ERROR DPAPI: Descarga cookies.txt y ponlo en backend/"}
        return {"status": "error", "message": msg}