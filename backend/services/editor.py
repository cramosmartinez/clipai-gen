import ffmpeg
import os
import sys

def hex_to_ffmpeg_bgr(hex_color):
    """Convierte el color HEX (#RRGGBB) a formato BGR hexadecimal de FFmpeg (&H00BBGGRR)."""
    hex_color = hex_color.lstrip('#')
    bgr_hex = hex_color[4:6] + hex_color[2:4] + hex_color[0:2]
    return f"&H00{bgr_hex}" 

def process_clip(video_path, start, end, clip_id, output_folder, srt_path=None, primary_color_hex="#FFFFFF", outline_color_hex="#000000", style="auto"):
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_filename = f"clip_{clip_id}.mp4"
        output_path = os.path.join(output_folder, output_filename)

        # 1. DIMENSIONES DEL VIDEO (BYPASS DE ERROR)
        # Forzamos 720p para el crop
        width = 1280 
        height = 720 
        
        # 2. CÁLCULO DE CROP CENTRADO
        target_width = 608 
        face_center_ratio = 0.5 
        center_pixel = int(face_center_ratio * width)
        crop_x = center_pixel - (target_width // 2)

        if crop_x < 0: crop_x = 0
        if crop_x + target_width > width: crop_x = width - target_width

        # 3. PROCESAMIENTO CON FFMPEG
        input_stream = ffmpeg.input(video_path, ss=start, t=end-start)
        video = input_stream.video.filter('crop', target_width, height, crop_x, 0)
        
        # 4. SUBTÍTULOS DINÁMICOS
        if srt_path and os.path.exists(srt_path):
            try:
                base_dir = os.getcwd()
                rel_path = os.path.relpath(srt_path, base_dir)
                safe_path = rel_path.replace('\\', '/')
                
                ffmpeg_primary = hex_to_ffmpeg_bgr(primary_color_hex)
                ffmpeg_outline = hex_to_ffmpeg_bgr(outline_color_hex)
                
                style_config = (
                    f"Fontname=Arial Black,FontSize=20,Alignment=2,MarginV=30,"
                    f"PrimaryColour={ffmpeg_primary},"
                    f"OutlineColour={ffmpeg_outline},"
                    f"BorderStyle=1,Outline=3,Shadow=1"
                )
                
                video = video.filter('subtitles', safe_path, force_style=style_config)
            except Exception as e:
                print(f"⚠️ Error al aplicar subtítulos. {e}")

        audio = input_stream.audio
        
        # 5. RENDERIZAR
        stream = ffmpeg.output(audio, video, output_path, vcodec='libx264', acodec='aac', strict='experimental')
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        return {"status": "success", "path": output_path, "filename": output_filename}

    except ffmpeg.Error as e:
        error_log = e.stderr.decode('utf8')
        print(f"❌ Error FFmpeg Detallado:\n{error_log}")
        return {"status": "error", "message": "Error procesando video (FFmpeg)"}
    except Exception as e:
        print(f"❌ Error General: {e}")
        return {"status": "error", "message": str(e)}