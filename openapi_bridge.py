"""OpenAPI Bridge Server exposing SpectraBrowser MCP capabilities to Open WebUI."""

import sys
from pathlib import Path

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
    description="OpenAPI Tool Server for Open WebUI exposing all 31 SpectraBrowser MCP capabilities",
    version="1.0.0"
)

# Enable CORS so Open WebUI can connect without browser/network restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all MCP tools directly with their actual parameter signatures
for tool in mcp._tool_manager.list_tools():
    app.post(
        f"/{tool.name}",
        summary=tool.name,
        description=tool.description
    )(tool.fn)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "SpectraBrowser OpenAPI Bridge",
        "total_tools": len(mcp._tool_manager.list_tools())
    }


# Tolerance alias for Open WebUI which sometimes appends /openapi.json twice
@app.get("/openapi.json/openapi.json")
def openapi_double_alias():
    return JSONResponse(content=app.openapi())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
