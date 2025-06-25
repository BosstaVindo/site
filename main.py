from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import random, os, qrcode, socket, uuid, asyncio, json

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

clients = {}
numbers = []
shuffled_numbers = []
index = 0

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

def generate_qr(ws_url: str):
    qr = qrcode.make(ws_url)
    qr_path = "static/qr_code.png"
    qr.save(qr_path)
    return qr_path

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    public_host = "painel-discador.onrender.com"
    unique_id = str(uuid.uuid4())
    ws_url = f"wss://{public_host}/ws/{unique_id}"
    generate_qr(ws_url)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "numbers": numbers,
        "qr_url": f"/static/qr_code.png",
        "ws_url": ws_url,
        "connected": list(clients.keys()),
        "uuid": unique_id
    })

@app.post("/upload")
async def upload_txt(file: UploadFile):
    global numbers, shuffled_numbers, index
    content = await file.read()
    text = content.decode("utf-8")
    numbers = [line.strip() for line in text.splitlines() if line.strip().isdigit()]
    shuffled_numbers = numbers.copy()
    random.shuffle(shuffled_numbers)
    index = 0
    return {"status": "success", "loaded": len(shuffled_numbers)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    global index
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            if data == "next_number" and index < len(shuffled_numbers):
                number = shuffled_numbers[index]
                index += 1
                await websocket.send_text(number)
            elif index >= len(shuffled_numbers):
                await websocket.send_text("done")
    except WebSocketDisconnect:
        del clients[client_id]
