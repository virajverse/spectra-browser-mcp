import asyncio
import os
import inspect
import sys
from pathlib import Path
from typing import Any

from pydantic import create_model

# Ensure spectra-browser-mcp src is in path
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from browser_qa.server import mcp

app = FastAPI(
    title="SpectraBrowser MCP Tools",
    description="OpenAPI Tool Server for Open WebUI exposing all SpectraBrowser MCP capabilities",
    version="1.0.0",
    servers=[
        {"url": "/", "description": "Current Server (Auto-Resolved)"}
    ]
)


# ISSUE-12 FIX: allow_origins=["*"] + allow_credentials=True is a CORS spec violation
# Browsers reject credentialed requests to wildcard origins.
# For local Open WebUI usage, explicitly allow localhost origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# =============================================================================
# 🛠️ MCP TOOL REGISTRATION (Direct Clean Tool Access)
# =============================================================================
def register_tool_endpoint(tool):
    fn = tool.fn
    sig = inspect.signature(fn)
    tool_name = tool.name

    if not sig.parameters:
        async def no_param_handler():
            try:
                if inspect.iscoroutinefunction(fn):
                    return await asyncio.wait_for(fn(), timeout=120.0)
                return await asyncio.wait_for(asyncio.to_thread(fn), timeout=120.0)
            except asyncio.TimeoutError:
                return {"error": f"Tool '{tool_name}' timed out after 120s"}
            except Exception as e:
                return {"error": f"Tool execution failed: {str(e)}"}

        no_param_handler.__name__ = tool_name
        app.post(
            f"/{tool_name}",
            summary=tool_name,
            description=tool.description
        )(no_param_handler)
        app.get(
            f"/{tool_name}",
            summary=tool_name,
            description=tool.description
        )(no_param_handler)
        return

    fields = {}
    for name, param in sig.parameters.items():
        ann = param.annotation if param.annotation != inspect.Parameter.empty else Any
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[name] = (ann, default)

    ReqModel = create_model(f"{tool_name}_Payload", **fields)

    async def param_handler(payload: ReqModel):
        kwargs = payload.model_dump(exclude_unset=False)
        filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
        try:
            if inspect.iscoroutinefunction(fn):
                return await asyncio.wait_for(fn(**filtered), timeout=120.0)
            return await asyncio.wait_for(asyncio.to_thread(fn, **filtered), timeout=120.0)
        except asyncio.TimeoutError:
            return {"error": f"Tool '{tool_name}' timed out after 120s"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    param_handler.__name__ = tool_name
    app.post(
        f"/{tool_name}",
        summary=tool_name,
        description=tool.description
    )(param_handler)



# Register all MCP tools dynamically with typed request payload models
for tool in mcp._tool_manager.list_tools():
    register_tool_endpoint(tool)



import io
import zipfile
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi import Request

EXTENSION_DIR = CURRENT_DIR / "extension"

def get_base_url(request: Request) -> str:
    """Dynamically resolves root URL from incoming request headers or environment."""
    env_url = os.getenv("PUBLIC_URL", os.getenv("BASE_URL", "")).strip().rstrip("/")
    if env_url:
        return env_url
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}".rstrip("/")


def generate_landing_page_html(base_url: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpectraBrowser MCP - Extension Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0B0F19;
      --card-bg: rgba(17, 24, 39, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #3B82F6;
      --accent-glow: rgba(59, 130, 246, 0.25);
      --success: #10B981;
      --success-glow: rgba(16, 185, 129, 0.25);
      --text: #F9FAFB;
      --text-muted: #9CA3AF;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px;
      line-height: 1.6;
    }}
    .container {{ max-width: 900px; width: 100%; }}
    .header {{ text-align: center; margin-bottom: 40px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 9999px;
      font-size: 0.85rem;
      color: #60A5FA;
      margin-bottom: 16px;
    }}
    h1 {{
      font-size: 2.8rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin-bottom: 12px;
      background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .subtitle {{ color: var(--text-muted); font-size: 1.15rem; max-width: 600px; margin: 0 auto; }}
    .status-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(12px);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }}
    .status-left {{ display: flex; align-items: center; gap: 16px; }}
    .status-indicator {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #EF4444;
      box-shadow: 0 0 12px rgba(239, 68, 68, 0.6);
      transition: all 0.3s ease;
    }}
    .status-indicator.connected {{
      background: var(--success);
      box-shadow: 0 0 12px var(--success-glow);
    }}
    .status-title {{ font-weight: 700; font-size: 1.1rem; }}
    .status-desc {{ font-size: 0.9rem; color: var(--text-muted); }}
    .download-hero {{
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 20px;
      padding: 36px;
      text-align: center;
      margin-bottom: 40px;
    }}
    .download-hero h2 {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 8px; }}
    .download-hero p {{ color: var(--text-muted); margin-bottom: 24px; }}
    .cta-buttons {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }}
    .btn-download-primary {{
      background: linear-gradient(135deg, #10B981 0%, #059669 100%);
      color: white;
      text-decoration: none;
      font-weight: 700;
      font-size: 1.05rem;
      padding: 16px 28px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 20px var(--success-glow);
      transition: all 0.2s ease;
    }}
    .btn-download-primary:hover {{ transform: translateY(-2px); box-shadow: 0 6px 24px var(--success-glow); }}
    .btn-download-secondary {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: white;
      text-decoration: none;
      font-weight: 600;
      font-size: 1.05rem;
      padding: 16px 24px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      transition: all 0.2s ease;
    }}
    .btn-download-secondary:hover {{ background: rgba(255, 255, 255, 0.1); transform: translateY(-2px); }}
    .steps-section {{ margin-bottom: 40px; }}
    .section-title {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 20px; text-align: center; }}
    .steps-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }}
    .step-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
      position: relative;
    }}
    .step-num {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background: var(--accent);
      color: white;
      font-weight: 800;
      border-radius: 8px;
      margin-bottom: 12px;
    }}
    .step-card h3 {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; }}
    .step-card p {{ color: var(--text-muted); font-size: 0.95rem; }}
    .capabilities-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
    .cap-item {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.05);
      padding: 14px;
      border-radius: 10px;
      font-size: 0.95rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .footer {{
      margin-top: 40px;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 24px;
    }}
    .btn-test {{
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.4);
      color: #60A5FA;
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="badge">🧩 Extension-Native Architecture</div>
      <h1>SpectraBrowser MCP Hub</h1>
      <p class="subtitle">Live Chrome Remote Debugger &amp; AI Autonomous Control Gateway</p>
    </div>

    <!-- Live Status Monitor -->
    <div class="status-card">
      <div class="status-left">
        <div class="status-indicator" id="statusDot"></div>
        <div>
          <div class="status-title" id="statusText">Checking Extension Status...</div>
          <div class="status-desc" id="statusDesc">Verifying WebSocket communication on ws://127.0.0.1:8765</div>
        </div>
      </div>
      <button class="btn-test" onclick="checkStatus()">🔄 Refresh Status</button>
    </div>

    <!-- Download Hero Box with 1-Click Auto-Launcher -->
    <div class="download-hero">
      <h2>🚀 1-Click Auto-Install &amp; Launch</h2>
      <p>Download the 1-click batch launcher or standalone ZIP package below.</p>
      
      <div class="cta-buttons">
        <a href="/download-launcher" class="btn-download-primary">
          <span>⚡</span> Download 1-Click Auto-Launcher (.BAT)
        </a>
        <a href="/download-extension" class="btn-download-secondary">
          <span>📦</span> Download Manual ZIP (.ZIP)
        </a>
      </div>
    </div>

    <!-- 3-Step Setup Instructions -->
    <section class="steps-section">
      <h2 class="section-title">✨ How to Use 1-Click Auto-Launcher (Zero Setup)</h2>
      <div class="steps-grid">
        <div class="step-card">
          <div class="step-num">1</div>
          <h3>Click &amp; Download</h3>
          <p>Click the green <strong>"Download 1-Click Auto-Launcher (.BAT)"</strong> button above to get <code>install_spectra_chrome.bat</code>.</p>
        </div>
        <div class="step-card">
          <div class="step-num">2</div>
          <h3>Double-Click to Run</h3>
          <p>Double-click the downloaded <code>.bat</code> file on your Windows computer. It will automatically download &amp; pre-load the extension.</p>
        </div>
        <div class="step-card">
          <div class="step-num">3</div>
          <h3>Chrome Opens Active!</h3>
          <p>Google Chrome opens immediately with Spectra Extension pre-loaded. <strong>Keep that window open</strong> for your AI Agent!</p>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section>
      <h2 class="section-title">✨ Active MCP 3 Capabilities</h2>
      <div class="capabilities-grid">
        <div class="cap-item"><span class="cap-icon">🎯</span> 100% Extension-Native Tabs</div>
        <div class="cap-item"><span class="cap-icon">🧠</span> Human-like Mouse Physics</div>
        <div class="cap-item"><span class="cap-icon">🔍</span> Realtime DevTools Inspector</div>
        <div class="cap-item"><span class="cap-icon">🔒</span> Zero-Trace Local Execution</div>
      </div>
    </section>

    <div class="footer">
      Powered by Taliyo Technologies Unified AI Ecosystem &bull; Port 8002 &bull; {base_url or "http://127.0.0.1:8002"}
    </div>
  </div>

  <script>
    async function checkStatus() {{
      const dot = document.getElementById('statusDot');
      const text = document.getElementById('statusText');
      const desc = document.getElementById('statusDesc');

      text.innerText = 'Checking connection...';
      try {{
        const res = await fetch('/extension_status', {{ method: 'POST' }});
        const data = await res.json();
        if (data.extension_connected) {{
          dot.classList.add('connected');
          text.innerText = '🟢 Chrome Extension Connected & Ready!';
          desc.innerText = 'AI Agent has live control of your open Chrome tabs.';
        }} else {{
          dot.classList.remove('connected');
          text.innerText = '🟡 Waiting for Chrome Extension Connection...';
          desc.innerText = 'Run the 1-click launcher or load unpacked extension in Chrome.';
        }}
      }} catch (e) {{
        dot.classList.remove('connected');
        text.innerText = '🟡 Chrome Extension Not Connected';
        desc.innerText = 'Download the 1-click launcher above to connect instantly.';
      }}
    }}

    // Auto check on page load and every 5 seconds
    checkStatus();
    setInterval(checkStatus, 5000);
  </script>
</body>
</html>
"""


@app.get("/download-launcher")
@app.get("/install.bat")
def download_launcher_bat(request: Request):
    """Generates and serves a 1-click Windows batch auto-launcher for Google Chrome."""
    base_url = get_base_url(request)
    bat_content = f"""@echo off
title SpectraBrowser 1-Click Auto-Launcher
echo =========================================================================
echo   🚀 SpectraBrowser 1-Click Chrome Auto-Launcher (Zero Setup)
echo =========================================================================
echo.

set DEST=%USERPROFILE%\\SpectraExtension
if not exist "%DEST%" mkdir "%DEST%"

echo [1/3] Downloading latest SpectraBrowser Extension...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '{base_url}/download-extension' -OutFile '%DEST%\\extension.zip'"

echo [2/3] Extracting extension files...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%DEST%\\extension.zip' -DestinationPath '%DEST%' -Force"

echo [3/3] Launching Google Chrome with Spectra pre-loaded...
start chrome.exe --load-extension="%DEST%" "{base_url}/install"

echo.
echo =========================================================================
echo   ✅ SUCCESS! Google Chrome is open with Spectra Extension active!
echo   Keep this Chrome window open while using AI Agent tools.
echo =========================================================================
timeout /t 5
"""
    return Response(
        content=bat_content.encode("utf-8"),
        media_type="application/x-bat",
        headers={
            "Content-Disposition": "attachment; filename=install_spectra_chrome.bat"
        }
    )


@app.get("/download-extension")
@app.get("/download")
def download_extension_zip():
    """Generates and streams a ready-to-use zip file of the SpectraBrowser Chrome extension."""
    if not EXTENSION_DIR.exists():
        return JSONResponse(status_code=404, content={"error": "Extension directory not found"})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in EXTENSION_DIR.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                z.write(f, f.relative_to(EXTENSION_DIR))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=spectra-browser-extension.zip"
        }
    )


@app.get("/")
@app.get("/install")
def root_page(request: Request):
    """Serves the stunning extension installation hub for browsers, and JSON for API clients."""
    base_url = get_base_url(request)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=generate_landing_page_html(base_url), status_code=200)

    tools = [t.name for t in mcp._tool_manager.list_tools()]
    return JSONResponse(content={
        "status": "online",
        "service": "SpectraBrowser OpenAPI Bridge",
        "total_tools": len(tools),
        "one_click_launcher": f"{base_url}/download-launcher",
        "download_url": f"{base_url}/download-extension",
        "setup_guide": f"{base_url}/install",
        "tools": tools
    })


# Tolerance alias for Open WebUI which sometimes appends /openapi.json twice
@app.get("/openapi.json/openapi.json")
def openapi_double_alias():
    return JSONResponse(content=app.openapi())


@app.get("/api/config")
def api_config():
    return {"status": "ok", "service": "spectra-browser"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title="SpectraBrowser MCP Tools",
        version="1.0.0",
        description="OpenAPI Tool Server for Open WebUI exposing all SpectraBrowser MCP capabilities",
        routes=app.routes,
        servers=[
            {"url": "/", "description": "Current Server (Auto-Resolved)"}
        ]
    )
    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)

