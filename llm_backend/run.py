import sys
import uvicorn
import os
from pathlib import Path

from app.core.logger import get_logger
logger = get_logger(service="server")

def start_server():
    os.chdir(Path(__file__).parent)
    logger.info("Starting server...")
    logger.info(f"Working directory: {os.getcwd()}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        access_log=False,
        log_level="error",
        reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    )

if __name__ == "__main__":
    start_server()

