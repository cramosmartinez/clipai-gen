import whisper
import warnings
import os

warnings.filterwarnings("ignore")

print("⏳ Cargando modelo Whisper (Modo Tiny - Estable)...")
# Usamos el motor
model = whisper.load_model("tiny") 
print("✅ Modelo Whisper cargado.")

def format_timestamp(seconds):
    if seconds < 0: seconds = 0
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    mins = seconds // 60
    hrs = mins // 60
    mins = mins % 60
    seconds = seconds % 60
    return f"{hrs:02}:{mins:02}:{seconds:02},{millis:03}"

def generate_clip_srt(full_segments, start_time, end_time, output_path):
    clip_segments = []
    for seg in full_segments:
        # La API original usa diccionarios
        if seg['end'] < start_time: continue
        if seg['start'] > end_time: break
        clip_segments.append(seg)

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(clip_segments):
            rel_start = segment['start'] - start_time
            rel_end = segment['end'] - start_time
            if rel_start < 0: rel_start = 0
            clip_duration = end_time - start_time
            if rel_end > clip_duration: rel_end = clip_duration

            start_str = format_timestamp(rel_start)
            end_str = format_timestamp(rel_end)
            text = segment['text'].strip()
            
            f.write(f"{i+1}\n{start_str} --> {end_str}\n{text}\n\n")
            
    return len(clip_segments) > 0

def transcribe_video(video_path):
    try:
        result = model.transcribe(video_path, fp16=False)
        return {
            "status": "success",
            "text": result["text"],
            "segments": result["segments"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}