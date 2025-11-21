# backend/tasks.py
import os
import uuid
import time
import json
import pathlib
import sys
from backend.celery_app import celery_app # Importa Celery

# 1. Asegúrate de que los imports de servicios estén bien (esto es CRÍTICO en nativo)
# Puedes usar la misma solución de sys.path que tenías en app.py si es necesario.
from services.downloader import download_video
from services.transcriber import transcribe_video, generate_clip_srt 
from services.analyzer import analyze_transcript 
from services.editor import process_clip

# --- FUNCIÓN DE TAREA ASÍNCRONA ---

@celery_app.task(bind=True) # El argumento bind=True permite acceder a 'self' (la instancia de la tarea)
def processing_worker(self, job_id, url, settings):
    
    # 💥 CAMBIO CRÍTICO: Usamos el método de Celery para reportar el estado
    def update_job_status(step, progress=None, msg=None, payload=None):
        meta = {"step": step, "progress": progress if progress is not None else 0, "msg": msg if msg else "Procesando"}
        if payload: meta.update(payload)
        
        # Celery actualizará el estado de la tarea en Redis
        self.update_state(state='PROGRESS', meta=meta)
        print(f"[{job_id}] Celery Update: {msg} (Step: {step})")

    try:
        # 1. DESCARGA
        update_job_status("download", 0, "Iniciando descarga...")
        
        # ... (Resto de la lógica de descarga, transcripción, análisis y edición) ...
        # ... (Mantén el cuerpo de tu función processing_worker, pero usa update_job_status) ...
        
        # Ejemplo de cómo usar el callback de progreso de descarga:
        def on_progress(percent_str):
            try:
                val = float(percent_str)
                # El progreso se escala (Descarga es el 25% del proceso)
                update_job_status("download", val * 0.25, f"Descargando: {val}%")
            except: pass

        download_res = download_video(url, UPLOADS_DIR, progress_callback=on_progress)
        
        # ... (Continuar la lógica) ...
        
        # 4. EDICIÓN Y SUBTITULADO (Progreso del 75% al 100%)
        # ... (Lógica de bucle para procesar clips) ...
        
        update_job_status("complete", 100, f'🎉 ¡Proceso finalizado! Clips generados.')
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error fatal en el trabajo {job_id}: {error_message}")
        update_job_status("error", msg=f"Error fatal: {error_message}")
        raise # Es importante levantar la excepción para que Celery marque la tarea como fallida