import uvicorn
from src.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print("=" * 50)
    print(f"Starting {settings.APP_NAME}")
    print("=" * 50)
    print(f"Server: http://localhost:8000")
    print(f"Docs: http://localhost:8000/api/docs")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"],
        log_level="info",
        access_log=True
    )