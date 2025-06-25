
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
        "connected": list(clients.keys())
    })

@app.post("/upload")
async def upload_list(request: Request, file: UploadFile, ddd: str = Form("")):
    global numbers, shuffled_numbers, index
    content = (await file.read()).decode("utf-8").splitlines()
    clean_numbers = []

    for line in content:
        line = line.strip()
        if line:
            if ddd and not line.startswith(ddd):
                line = f"{ddd}{line}"
            clean_numbers.append(line)

    numbers = clean_numbers
    shuffled_numbers = random.sample(numbers, len(numbers))
    index = 0
    return {"status": "lista carregada", "quantidade": len(shuffled_numbers)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    global index
    await websocket.accept()
    clients[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if isinstance(msg, dict) and msg.get("tipo") == "registrar":
                    aparelho_id = msg.get("aparelho_id")
                    if aparelho_id and aparelho_id not in clients:
                        clients[aparelho_id] = websocket
                        print(f"Aparelho registrado: {aparelho_id}")
                elif data == "ligar":
                    await enviar_para_todos()
            except json.JSONDecodeError:
                if data == "ligar":
                    await enviar_para_todos()
    except WebSocketDisconnect:
        if client_id in clients:
            del clients[client_id]

async def enviar_para_todos(tamanho: int = 6):
    global index
    if not shuffled_numbers:
        return

    lote = []
    for _ in range(tamanho):
        if index >= len(shuffled_numbers):
            index = 0
            random.shuffle(shuffled_numbers)
        lote.append(shuffled_numbers[index])
        index += 1

    for client_ws in list(clients.values()):
        try:
            await client_ws.send_json({"acao": "ligar", "numeros": lote})
        except:
            pass  # desconectado ou erro
