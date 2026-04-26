#!/bin/bash
cd "/Users/cb/CLAUDE FREE/free-claude-code"
exec uv run uvicorn server:app --host 0.0.0.0 --port 8082
