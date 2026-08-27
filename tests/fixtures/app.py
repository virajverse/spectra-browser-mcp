"""Local deterministic test fixture server providing HTTP, WebSocket, SSE, and error endpoints."""

import asyncio
import time
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Browser QA Local Test Fixture")


class OrderPayload(BaseModel):
    item: str
    quantity: int


@app.get("/test-page", response_class=HTMLResponse)
def get_test_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Browser QA Test Lab</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .btn { padding: 8px 16px; margin: 6px; cursor: pointer; }
            .danger { background-color: #ff4d4f; color: white; }
        </style>
    </head>
    <body>
        <h1>Test Dashboard</h1>
        <h2>Operational Controls</h2>
        <p id="status-text">Ready for testing.</p>

        <div>
            <button id="btn-ok" class="btn" onclick="fetchOk()">Fetch OK</button>
            <button id="btn-err" class="btn" onclick="trigger500()">Trigger 500 Error</button>
            <button id="btn-js-err" class="btn" onclick="triggerJsError()">Throw JS Exception</button>
            <button id="btn-delete" class="btn danger" onclick="deleteAccount()">Delete Account</button>
        </div>

        <h3>Authentication Form</h3>
        <form id="login-form" action="/api/login" method="POST">
            <div>
                <label>Email: <input type="email" id="email-input" name="email" placeholder="user@example.com"></label>
            </div>
            <div style="margin-top: 8px;">
                <label>Password: <input type="password" id="pwd-input" name="password" placeholder="Enter password"></label>
            </div>
            <div style="margin-top: 8px;">
                <button type="submit" id="submit-login" class="btn">Sign In</button>
            </div>
        </form>

        <script>
            console.log("Test Lab initialized successfully");

            function fetchOk() {
                fetch('/api/ok')
                    .then(r => r.json())
                    .then(d => { document.getElementById('status-text').innerText = 'Fetch OK succeeded'; });
            }

            function trigger500() {
                console.error("Initiating failing transaction /api/error");
                fetch('/api/error')
                    .then(r => {
                        if (!r.ok) {
                            document.getElementById('status-text').innerText = 'HTTP 500 error received';
                            throw new Error("HTTP 500 Server Error encountered in UI");
                        }
                    });
            }

            function triggerJsError() {
                console.error("Deliberate JS TypeError triggered");
                window.nonExistentObject.nonExistentMethod();
            }

            function deleteAccount() {
                document.getElementById('status-text').innerText = 'Account deletion requested';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/ok")
def get_ok():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/error")
def get_error():
    raise HTTPException(status_code=500, detail="Internal simulated database transaction failure")


@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    # Schema drift demo: user 123 has price as float, user 124 has price as string
    if user_id == 123:
        return {"id": 123, "name": "Alice", "price": 49.99}
    return {"id": user_id, "name": "Bob", "price": "50.00"}


@app.post("/api/login")
def post_login(payload: dict):
    return {"status": "authenticated", "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.sig"}


@app.get("/events")
async def sse_events():
    async def event_generator():
        for i in range(3):
            await asyncio.sleep(0.1)
            yield f"event: test_event\ndata: {{\"count\": {i}}}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
