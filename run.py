import sys
from pathlib import Path
import uvicorn

# Ensure jester root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings


def main():
    print("=" * 60)
    print("  [*] JESTER - STANDALONE ROYAL COURT CHAT (v0.1) [*]")
    print("=" * 60)
    print(f"  Model        : {settings.llm.model}")
    print(f"  Ollama Host  : {settings.llm.base_url}")
    print(f"  Web UI       : http://{settings.server.host}:{settings.server.port}")
    print(f"  API Docs     : http://{settings.server.host}:{settings.server.port}/docs")
    print("=" * 60)
    print("Starting server... Press Ctrl+C to stop.\n")

    uvicorn.run(
        "backend.app:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
