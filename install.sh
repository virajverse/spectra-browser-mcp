#!/bin/bash
set -e

echo "==================================================="
echo "Setting up Browser QA & Network Intelligence MCP"
echo "==================================================="

echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo "Installing Playwright browser binaries..."
python3 -m playwright install chromium

echo "Running verification test suite..."
python3 tests/test_redaction.py
python3 tests/test_schema.py
python3 tests/test_smoke.py
python3 tests/test_bridge.py

echo "==================================================="
echo "Browser QA MCP is ready for use!"
echo "Run 'python3 -m browser_qa.server' for FastMCP"
echo "Run 'python3 openapi_bridge.py' for Open-WebUI Bridge"
echo "==================================================="
