"""OpenAPI Bridge Server exposing SpectraBrowser MCP capabilities to Open WebUI."""

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
    version="1.0.0"
)

# ISSUE-12 FIX: allow_origins=["*"] + allow_credentials=True is a CORS spec violation
# Browsers reject credentialed requests to wildcard origins.
# For local Open WebUI usage, explicitly allow localhost origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def register_tool_endpoint(tool):
    fn = tool.fn
    sig = inspect.signature(fn)
    tool_name = tool.name

    if not sig.parameters:
        def no_param_handler():
            return fn()
        no_param_handler.__name__ = tool_name
        app.post(
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

    def param_handler(payload: ReqModel):
        kwargs = payload.model_dump(exclude_unset=False)
        filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return fn(**filtered)

    param_handler.__name__ = tool_name
    app.post(
        f"/{tool_name}",
        summary=tool_name,
        description=tool.description
    )(param_handler)


# Register all MCP tools dynamically with typed request payload models
for tool in mcp._tool_manager.list_tools():
    register_tool_endpoint(tool)


@app.get("/")
def root():
    tools = [t.name for t in mcp._tool_manager.list_tools()]
    return {
        "status": "online",
        "service": "SpectraBrowser OpenAPI Bridge",
        "total_tools": len(tools),
        "tools": tools
    }


# Tolerance alias for Open WebUI which sometimes appends /openapi.json twice
@app.get("/openapi.json/openapi.json")
def openapi_double_alias():
    return JSONResponse(content=app.openapi())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
