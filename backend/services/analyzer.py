import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def analyze_transcript(transcript_text):
    print("🔍 Iniciando análisis de IA (Modo: Alta Cantidad - 6 a 10 clips)...")
    
    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Falta GEMINI_API_KEY en .env"}

    model_name = "gemini-1.5-flash"
    
    # --- PROMPT AGRESIVO PARA CANTIDAD ---
    prompt = f"""
    Actúa como un Editor de Contenido masivo para TikTok. Tienes un video largo y necesitas sacar MUCHO contenido.
    
    TU OBJETIVO: Extraer OBLIGATORIAMENTE entre 6 y 10 segmentos distintos del texto.
    
    REGLAS DE EXTRACCIÓN:
    1. CANTIDAD: No te limites. Si dudas, crea el clip. Necesito llenar la parrilla de contenido.
    2. DURACIÓN: Busca segmentos de 30 a 60 segundos.
    3. COBERTURA: Intenta cubrir diferentes partes del video (inicio, medio, final).
    
    FORMATO DE RESPUESTA (ARRAY JSON PURO):
    [ 
        {{"start": 10, "end": 50, "summary": "Título Atractivo 1", "virality_score": 8}},
        {{"start": 90, "end": 140, "summary": "Título Atractivo 2", "virality_score": 7}}
    ]

    TRANSCRIPCIÓN:
    {transcript_text[:40000]} 
    """

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "config": {
            "responseMimeType": "application/json",
            "temperature": 0.7 # Aumentamos creatividad para encontrar más clips
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()

        response_json = response.json()
        
        if 'candidates' not in response_json or not response_json['candidates']:
            return {"status": "error", "message": "Sin respuesta de IA"}

        text = response_json['candidates'][0]['content']['parts'][0]['text']
        
        # Limpieza de JSON
        start_idx = text.find('[')
        end_idx = text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            clean_json = text[start_idx:end_idx]
            clips = json.loads(clean_json)
            
            # Validación de cantidad
            print(f"🤖 La IA encontró {len(clips)} clips.")
            return {"status": "success", "clips": clips} 
        else:
            return {"status": "error", "message": "JSON inválido"}

    except Exception as e:
        print(f"⚠️ Error IA: {e}")
        return {"status": "error", "message": str(e)}