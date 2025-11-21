# ETAPA 1: BUILDER (Compilación segura en Debian)
# Usamos Python 3.11 para instalar compiladores y librerías grandes (como numpy/whisper)
FROM python:3.11 as builder

# Instalamos herramientas de compilación
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Instalamos TODAS las dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# ETAPA 2: RUNTIME (Imagen final Alpine, muy ligera)
# Usamos Alpine para el entorno de producción más pequeño
FROM python:3.11-alpine

# Instalamos FFmpeg nativo de Alpine (es pequeño y necesario para el runtime)
RUN apk update && \
    apk add --no-cache ffmpeg curl bash && \
    rm -rf /var/cache/apk/*

WORKDIR /app

# Copiamos solo los archivos Python y las librerías compiladas del Builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# CRÍTICO: Añadir backend al PYTHONPATH para que Gunicorn encuentre 'services/'
ENV PYTHONPATH "${PYTHONPATH}:/app/backend" 

# Copiamos el código de la aplicación
COPY . .

# Creamos las carpetas necesarias
RUN mkdir -p backend/temp/uploads backend/temp/clips

EXPOSE 5000

# Comando de inicio con Gunicorn (servidor de producción)
CMD ["python", "-m", "gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "backend.app:app"]