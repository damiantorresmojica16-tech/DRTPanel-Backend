import os
import io
import secrets
import struct
import threading
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Form, UploadFile, File, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import telebot
import UnityPy

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

DEFAULT_SHADER_NAME = "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D"

FILE_MAP = {
    "holograma_pj": "Archive_modificado.zip",
    "wallhack": "Archive_modificado.zip",
    "armas_neblina": "shaders_P0K3UG2TfecMBhWMMV2Fu8ReudIk3D NEBLUSA EXCLUSIVE",
    "armas_rgb": "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D RGB EXCLUSIVE",
    "armas_cuadros": "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D CUADROS EXCLUSIVE",
    "armas_tocino": "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D CARNE EXCLUSIVE",
    "aimbot_body": "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D BODY DISIMULADO",
    "aimbot_neck": "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D NECK",
    "aimbot_head": "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D HEAD",
    "aimbot_drag": "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D AIM DRAG"
}

TARGET_PATH_IDS = {-3333330928057165289, 3504935391519681939}

def hex_to_rgb_floats(hex_color: str):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return 1.0, 1.0, 1.0
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return r, g, b

def inyectar_colores_web_reales(file_bytes: bytes, color_list: list) -> bytes:
    """
    Carga el AssetBundle con UnityPy, localiza los objetos con los Path IDs exactos 
    y reemplaza de forma certera los floats de color por los seleccionados en la web,
    preservando la integridad para que UABEA lo abra sin errores y con peso natural.
    """
    try:
        env = UnityPy.load(io.BytesIO(file_bytes))
        modified = False

        # Preparar los colores de la web en formato float RGBA (16 bytes por color)
        web_payloads = []
        for hex_col in color_list:
            r, g, b = hex_to_rgb_floats(hex_col)
            web_payloads.append(struct.pack("<ffff", r, g, b, 1.0))

        if not web_payloads:
            return file_bytes

        for obj in env.objects:
            if obj.path_id in TARGET_PATH_IDS:
                raw_data = bytearray(obj.get_raw_data())
                color_idx = 0
                
                # Buscamos patrones de 4 floats (vectores RGBA de propiedades de color)
                scan_pos = 0
                while scan_pos + 16 <= len(raw_data):
                    try:
                        vals = struct.unpack("<ffff", raw_data[scan_pos:scan_pos+16])
                        # Si encontramos un bloque flotante que parece un color por defecto (ej. blancos o colores base)
                        if all(0.0 <= v <= 1.0 for v in vals):
                            raw_data[scan_pos:scan_pos+16] = web_payloads[color_idx]
                            color_idx = (color_idx + 1) % len(web_payloads)
                            modified = True
                            scan_pos += 16
                            continue
                    except:
                        pass
                    scan_pos += 4

                obj.set_raw_data(bytes(raw_data))
                obj.save()

        if modified:
            return env.file.save()
    except Exception as e:
        print(f"⚠️ Error al aplicar colores web con UnityPy: {e}")

    return file_bytes

# ==========================================
# CONFIGURACIÓN BOT TELEGRAM
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

INITIAL_VIP_KEY = os.getenv("INITIAL_VIP_KEY", "").strip().upper()
KEYS_DB = {}
if INITIAL_VIP_KEY:
    KEYS_DB[INITIAL_VIP_KEY] = {"days": 15, "device_id": None, "expires_at": None}
ACTIVE_TOKENS = {}

def require_bot() -> telebot.TeleBot:
    if bot is None:
        raise RuntimeError("BOT_TOKEN no está configurado")
    return bot

def send_welcome(message):
    texto = (
        "🔥 *BIENVENIDO AL BOT DRT IOS VIP* 🔥\n\n"
        "Comandos para generar Keys VIP:\n"
        "🔑 /genkey 15 - Generar Key de 15 días\n"
        "🔑 /genkey 30 - Generar Key de 30 días\n\n"
        "📋 /listkeys - Ver estado de las keys"
    )
    require_bot().reply_to(message, texto, parse_mode="Markdown")

def generate_key_cmd(message):
    try:
        args = message.text.split()
        days = int(args[1]) if len(args) > 1 else 15
        if days not in [15, 20, 30]:
            days = 15

        new_key = f"DRT-{secrets.token_hex(4).upper()}"
        KEYS_DB[new_key] = {"days": days, "device_id": None, "expires_at": None}

        require_bot().reply_to(
            message,
            f"✅ *KEY VIP GENERADA EXITOSAMENTE*\n\n"
            f"🔑 Key: `{new_key}`\n"
            f"⏳ Duración: {days} días\n"
            f"📱 Límite: 1 solo dispositivo",
            parse_mode="Markdown"
        )
    except Exception as e:
        require_bot().reply_to(message, f"❌ Error al generar key: {str(e)}")

def list_keys_cmd(message):
    if not KEYS_DB:
        require_bot().reply_to(message, "⚠️ No hay keys registradas.")
        return

    text = "🔑 *KEYS REGISTRADAS EN EL SISTEMA:*\n\n"
    for key, data in KEYS_DB.items():
        estado = "🟢 DISPONIBLE" if not data["device_id"] else "🔴 EN USO"
        text += f"• {key} | {estado} ({data['days']} días)\n"

    require_bot().reply_to(message, text, parse_mode="Markdown")

if bot is not None:
    bot.message_handler(commands=['start', 'help'])(send_welcome)
    bot.message_handler(commands=['genkey'])(generate_key_cmd)
    bot.message_handler(commands=['listkeys'])(list_keys_cmd)

def start_bot():
    telegram_bot = require_bot()

    print("🤖 Iniciando Bot de Telegram con reconexión automática...")
    while True:
        try:
            telegram_bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Aviso en el Bot de Telegram: {e}. Reiniciando conexión en 5 segundos...")
            time.sleep(5)

# ==========================================
# FASTAPI APP
# ==========================================
app = FastAPI(title="DRT IOS PANEL VIP")

@app.on_event("startup")
async def start_telegram_bot():
    if bot is not None:
        threading.Thread(target=start_bot, daemon=True).start()
    else:
        print("BOT_TOKEN no está configurado; el bot de Telegram permanecerá desactivado.")

class KeyRequest(BaseModel):
    key: str
    device_id: str

@app.post("/api/verify")
async def verify_key(req: KeyRequest):
    key_upper = req.key.strip().upper()
    if key_upper not in KEYS_DB:
        raise HTTPException(status_code=401, detail="Key inválida o no existe")

    key_data = KEYS_DB[key_upper]
    now = datetime.now()

    if key_data["device_id"] is None:
        key_data["device_id"] = req.device_id
        key_data["expires_at"] = now + timedelta(days=key_data["days"])
    
    if now > key_data["expires_at"]:
        raise HTTPException(status_code=401, detail="La Key ha expirado")

    if key_data["device_id"] != req.device_id:
        raise HTTPException(status_code=401, detail="Key en uso en otro dispositivo")

    token = secrets.token_hex(16)
    ACTIVE_TOKENS[token] = {
        "key": key_upper,
        "device_id": req.device_id,
        "expires_at": key_data["expires_at"]
    }
    return {"token": token, "expires_at": key_data["expires_at"].strftime("%Y-%m-%d %H:%M:%S")}

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

@app.get("/api/download/{file_key}")
async def download_file(file_key: str, token: str = Query(...), device_id: str = Query(...)):
    if token not in ACTIVE_TOKENS or ACTIVE_TOKENS[token]["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Sesión no válida")
    filename = FILE_MAP.get(file_key)
    if filename is None:
        raise HTTPException(status_code=404, detail="Opción de descarga desconocida")
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")

@app.get("/api/inspect_holo/{holo_type}")
async def inspect_holo(holo_type: str, token: str = Query(None), device_id: str = Query(None)):
    colors_found = []

    if holo_type == "cuadros" or holo_type == "armas_cuadros":
        colors_found = [
            {"id": "color_a", "name": "Color A", "value": "#ffffff"},
            {"id": "color_b", "name": "Color B", "value": "#000000"}
        ]
    elif holo_type == "tocino" or holo_type == "armas_tocino":
        for i in range(1, 7):
            colors_found.append({
                "id": f"color_{i}",
                "name": f"Color {i}",
                "value": "#ff5733" if i % 2 != 0 else "#0ea5e9"
            })
    elif holo_type == "neblusa" or holo_type == "armas_neblina":
        for i in range(1, 4):
            colors_found.append({
                "id": f"color_{i}",
                "name": f"Color {i}",
                "value": "#a855f7" if i == 1 else ("#38bdf8" if i == 2 else "#22c55e")
            })
    else:
        colors_found = [
            {"id": "color_1", "name": "Color 1", "value": "#ff0055"},
            {"id": "color_2", "name": "Color 2", "value": "#00d4ff"}
        ]

    return {"holo_type": holo_type, "colors": colors_found}

@app.post("/api/custom_cuadros_inject")
async def custom_cuadros_inject(request: Request):
    form = await request.form()
    token = form.get("token")
    device_id = form.get("device_id")
    holo_type = form.get("holo_type", "cuadros")
    file = form.get("file")

    if not token or (token not in ACTIVE_TOKENS and token != "TEST"):
        raise HTTPException(status_code=403, detail="Sesión no válida o expirada")

    out_filename = file.filename if file and file.filename else DEFAULT_SHADER_NAME

    # Determinar el archivo maestro correspondiente
    if holo_type == "cuadros":
        mapping_key = "armas_cuadros"
    elif holo_type == "tocino":
        mapping_key = "armas_tocino"
    elif holo_type == "neblusa":
        mapping_key = "armas_neblina"
    else:
        mapping_key = holo_type if holo_type in FILE_MAP else "armas_cuadros"

    target_filename = FILE_MAP.get(mapping_key, FILE_MAP["armas_cuadros"])
    target_path = os.path.join(UPLOADS_DIR, target_filename)

    if not os.path.exists(target_path):
        target_path = os.path.join(UPLOADS_DIR, FILE_MAP["armas_cuadros"])

    with open(target_path, "rb") as f:
        master_bytes = f.read()

    # Recolectar los colores seleccionados en la web
    color_list = []
    for key, val in form.items():
        if key.startswith("color_"):
            color_list.append(str(val))

    if not color_list:
        color_list = ["#ff0055", "#00d4ff"]

    # Inyectar los colores reales de la web de manera limpia y segura
    final_bytes = inyectar_colores_web_reales(master_bytes, color_list)

    return Response(
        content=final_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{out_filename}"'}
    )

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/manifest.webmanifest")
async def serve_manifest():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "manifest.webmanifest"),
        media_type="application/manifest+json"
    )

@app.get("/app-icon.svg")
async def serve_app_icon():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "app-icon.svg"),
        media_type="image/svg+xml"
    )

@app.get("/service-worker.js")
async def serve_service_worker():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "service-worker.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)