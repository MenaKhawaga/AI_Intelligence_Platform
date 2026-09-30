"""Direct Python entrypoint for the AI Intelligence Platform."""
from __future__ import annotations

import uvicorn

from app.api.app import app
from app.core.config import settings

def main() -> None:
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)


if __name__ == "__main__":
    main()
