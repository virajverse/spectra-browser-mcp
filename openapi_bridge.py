"""OpenAPI Bridge Server exposing Browser QA MCP capabilities to Open WebUI."""

import sys
from pathlib import Path

# Ensure browser-qa-mcp src is in path
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR / "src"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from browser_qa.server import mcp

app = FastAPI(
    title="Browser QA & Network Intelligence Tools",
    description="OpenAPI Tool Server exposing all Browser QA & Network Intelligence MCP capabilities",
    version="1.0.0"
)

# Enable CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_tool_endpoint(tool_obj):
    async def endpoint_handler(request: Request):
        kwargs = {}
        # Parse JSON body if present
        try:
            body = await request.json()
            if isinstance(body, dict):
                kwargs.update(body)
        except Exception:
            pass

        # Also support query parameters
        kwargs.update(dict(request.query_params))

        try:
            import asyncio
            res = await asyncio.to_thread(tool_obj.fn, **kwargs)
            return res
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return endpoint_handler


# Register all MCP tools as FastAPI POST endpoints
for tool in mcp._tool_manager.list_tools():
    app.post(
        f"/{tool.name}",
        summary=tool.name,
        description=tool.description
    )(create_tool_endpoint(tool))


@app.get("/")
def root():
    tools = mcp._tool_manager.list_tools()
    return {
        "status": "online",
        "service": "Browser QA OpenAPI Bridge",
        "total_tools": len(tools),
        "tools": [t.name for t in tools]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
