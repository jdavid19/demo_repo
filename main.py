from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
import uuid
import re

app = FastAPI()

UPLOAD_DIR = Path("uploads")
STATIC_DIR = Path("static")

STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=UPLOAD_DIR, html=True), name="files")

@app.get("/", response_class=HTMLResponse)
def read_index():
    # html_path = Path("static/index.html")
    html_path = STATIC_DIR / "index.html"
    return html_path.read_text(encoding="utf-8")


def sanitize_ip(ip: str) -> str:
    """Sanitize IP address for filename use (remove unsafe characters)."""
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", ip)


@app.post("/upload")
async def upload_text(request: Request):
    # Extract client IP
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0] if forwarded else request.client.host
    safe_ip = sanitize_ip(client_ip)

    # Read and decode the request body
    raw_text = await request.body()
    content = raw_text.decode('utf-8')

    # Create unique filename with IP address
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"{timestamp}_{safe_ip}_{uuid.uuid4().hex}.txt"
    filepath = UPLOAD_DIR / filename

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "message": "File saved",
        "filename": filename,
        "client_ip": client_ip
    }


@app.get("/collected", response_class=HTMLResponse)
def list_files():
    file_links = []
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            view_url = f"/collected/{f.name}"
            file_links.append(f'<li><a href="{view_url}" target="_blank">{f.name}</a></li>')

    html_content = f"""
    <html>
        <head>
            <title>Uploaded Files</title>
        </head>
        <body>
            <h2>Uploaded Files</h2>
            <ul>
                {''.join(file_links)}
            </ul>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """
    return html_content


@app.get("/collected/{filename}", response_class=PlainTextResponse)
def view_file(filename: str):
    filepath = UPLOAD_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return filepath.read_text(encoding="utf-8")


@app.get("/download/{filename}")
def download_file(filename: str):
    filepath = UPLOAD_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=filepath, filename=filename, media_type='text/plain')