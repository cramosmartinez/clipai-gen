import os
import threading
import uuid
import time
import json
import pathlib
import sqlite3
import sys
from queue import Queue
import queue 

# --- SOLUCIÓN CRÍTICA PARA IMPORTACIONES ---
current_dir_abs = os.path.dirname(os.path.abspath(__file__)) 
if current_dir_abs not in sys.path:
    sys.path.append(current_dir_abs)
# -------------------------------------------

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS 
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user 
from werkzeug.security import generate_password_hash, check_password_hash
import yt_dlp

# Importar servicios
from services.downloader import download_video
from services.transcriber import transcribe_video, generate_clip_srt 
from services.analyzer import analyze_transcript 
from services.editor import process_clip

# --- INYECCIÓN DE RUTA DE FFMPEG ---
FFMPEG_PATH = os.path.join(current_dir_abs, 'ffmpeg.exe')
if os.path.exists(FFMPEG_PATH):
    os.environ["PATH"] += os.pathsep + current_dir_abs

# --- CONFIGURACIÓN ---
RETENTION_SECONDS = 86400 
ROOT_DIR = os.path.dirname(current_dir_abs) 
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
TEMP_DIR = os.path.join(current_dir_abs, "temp")
UPLOADS_DIR = os.path.join(TEMP_DIR, "uploads")
CLIPS_DIR = os.path.join(TEMP_DIR, "clips")
DATABASE_FILE = os.path.join(TEMP_DIR, "clips.db")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

# --- ESTADO GLOBAL ---
JOBS = {} 
job_queue = Queue()
job_progress = {} 

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'SUPER_SECRETO_DEV') 
CORS(app) 

# --- LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_route'

class User(UserMixin):
    def __init__(self, user_id, username, credits):
        self.id = str(user_id) 
        self.username = username
        self.credits = credits

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute("SELECT id, username, credits FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['credits'])
    return None

# --- DB FUNCTIONS ---
def get_db_connection():
    pathlib.Path(TEMP_DIR).mkdir(parents=True, exist_ok=True) 
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS clips (id TEXT PRIMARY KEY, title TEXT, score REAL, url TEXT, original_video TEXT, source_id TEXT, created_at REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, credits INTEGER)")
    
    cursor.execute("SELECT id FROM users WHERE username='test'")
    if not cursor.fetchone():
        hashed = generate_password_hash('test')
        cursor.execute("INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)", ('test', hashed, 100))
        print("✅ Usuario 'test' creado.")
    conn.commit()
    conn.close()

def save_to_history(clip_data):
    if 'created_at' not in clip_data: clip_data['created_at'] = time.time()
    conn = get_db_connection()
    conn.execute("INSERT INTO clips (id, title, score, url, original_video, source_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (clip_data['id'], clip_data['title'], clip_data['score'], clip_data['url'], clip_data['original_video'], clip_data['source_id'], clip_data['created_at']))
    conn.commit()
    conn.close()

def load_history():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM clips ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- WORKER PRINCIPAL ---
def processing_worker(job_id, url, settings):
    def update_job(step, progress=None, msg=None):
        if job_id not in JOBS: return
        state = JOBS[job_id]['state']
        if step: state['step'] = step
        if progress: state['progress'] = progress
        if msg: state['msg'] = msg
        JOBS[job_id]['queue'].put(json.dumps(state))

    try:
        update_job("download", 0, "Descargando...")
        res = download_video(url, UPLOADS_DIR, lambda p: update_job("download", float(p)))
        if res['status'] == 'error': raise Exception(res['message'])
        
        update_job("transcribe", 30, "Transcribiendo...")
        trans = transcribe_video(res['path'])
        
        update_job("analyze", 60, "Analizando...")
        
        # --- LÓGICA DE CLIPS ROBUSTA ---
        clips_to_process = []
        
        # 1. Intentar IA
        ia_res = analyze_transcript(trans['text'])
        
        if ia_res['status'] == 'success' and len(ia_res['clips']) > 0:
            clips_to_process = ia_res['clips']
        else:
            print("⚠️ IA falló o devolvió 0 clips. Usando Fallback Matemático.")
            
        # 2. Fallback Matemático (Si la IA devolvió menos de 3 clips)
        if len(clips_to_process) < 3:
            print("🔄 Generando clips matemáticos para rellenar...")
            video_duration = res['duration']
            # Generar un clip cada 90 segundos
            for start_sec in range(0, int(video_duration), 90):
                end_sec = min(start_sec + 60, video_duration)
                if end_sec - start_sec > 20: # Solo si el clip dura > 20s
                    clips_to_process.append({
                        'start': start_sec, 
                        'end': end_sec, 
                        'summary': f'Clip Auto {len(clips_to_process)+1}', 
                        'virality_score': 5.0
                    })
        
        # Limitar al máximo pedido (10)
        clips_to_process = clips_to_process[:10]
        
        update_job("edit", 80, f"Creando {len(clips_to_process)} clips...")
        
        final_clips = []
        for i, clip in enumerate(clips_to_process):
            srt_name = f"{res['video_id']}_{i}.srt"
            srt_path = os.path.join(UPLOADS_DIR, srt_name)
            
            has_subs = generate_clip_srt(trans['segments'], clip['start'], clip['end'], srt_path)
            
            out = process_clip(
                res['path'], clip['start'], clip['end'], f"{res['video_id']}_{i}", CLIPS_DIR,
                srt_path=srt_path if has_subs else None,
                primary_color_hex=settings['primaryColor'], outline_color_hex=settings['outlineColor']
            )
            
            if os.path.exists(srt_path): os.remove(srt_path)
            
            if out['status'] == 'success':
                c_data = {
                    "id": f"{res['video_id']}_{i}", 
                    "title": clip['summary'], 
                    "score": clip.get('virality_score', 5), 
                    "url": f"/download/{out['filename']}",
                    "original_video": res['title'], 
                    "source_id": res.get('youtube_id'), 
                    "created_at": time.time()
                }
                final_clips.append(c_data)
                save_to_history(c_data)

        if os.path.exists(res['path']): os.remove(res['path'])
        update_job("complete", 100, f"¡Listo! {len(final_clips)} clips creados.")

    except Exception as e:
        print(f"❌ Error: {e}")
        update_job("error", msg=str(e))

# --- RUTAS ---
@app.route('/start_process', methods=['POST'])
@login_required
def start():
    data = request.json
    
    # Costo Dinámico
    try:
        with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
            info = ydl.extract_info(data['url'], download=False)
            cost = int(info['duration']/60) + 1
    except: cost = 10

    if current_user.credits < cost:
        return jsonify({'error': f'Faltan créditos. Costo: {cost}'}), 402
    
    conn = get_db_connection()
    conn.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (cost, current_user.id))
    conn.commit()
    conn.close()

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {'queue': Queue(), 'state': {'step': 'init', 'progress': 0}}
    
    t = threading.Thread(target=processing_worker, args=(job_id, data['url'], data))
    t.start()
    
    return jsonify({'job_id': job_id})

@app.route('/stream/<job_id>')
def stream(job_id):
    if job_id not in JOBS: return Response('Not found', 404)
    def gen():
        q = JOBS[job_id]['queue']
        yield f'data: {json.dumps(JOBS[job_id]["state"])}\n\n'
        while True:
            try:
                msg = q.get(timeout=1)
                yield f'data: {msg}\n\n'
                if json.loads(msg)['step'] in ['complete', 'error']: break
            except queue.Empty: yield 'data: {"step":"ping"}\n\n'
            except: break
    return Response(gen(), mimetype='text/event-stream')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    u = conn.execute("SELECT * FROM users WHERE username=?", (data['username'],)).fetchone()
    conn.close()
    if u and check_password_hash(u['password_hash'], data['password']):
        login_user(User(u['id'], u['username'], u['credits']))
        return jsonify({'status': 'success', 'credits': u['credits']})
    return jsonify({'message': 'Error credenciales'}), 401

@app.route('/user_status')
def status():
    if current_user.is_authenticated:
        conn = get_db_connection()
        cr = conn.execute("SELECT credits FROM users WHERE id=?", (current_user.id,)).fetchone()['credits']
        conn.close()
        return jsonify({'is_authenticated': True, 'username': current_user.username, 'credits': cr})
    return jsonify({'is_authenticated': False})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'status':'success'})

@app.route('/history')
def history(): return jsonify(load_history())

@app.route('/')
def idx(): return send_from_directory(FRONTEND_DIR, 'index.html')
@app.route('/css/<path:f>')
def css(f): return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), f)
@app.route('/js/<path:f>')
def js(f): return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), f)
@app.route('/download/<f>')
def dl(f): return send_from_directory(CLIPS_DIR, f)

if __name__ == '__main__':
    init_db()
    print("\n🌐 SERVIDOR LISTO: http://localhost:8000")
    # No app.run() aquí porque usamos Waitress externamente