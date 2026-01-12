from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from src.routers import auth
from src.utils.response import APIResponse
from src.config import get_settings
import time
import uuid

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Complete Identity and Authentication Service",
    version="1.0.0",
    docs_url="/api/docs", 
    redoc_url="/api/redoc",
)

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def add_process_time_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    
    if process_time > 1.0:
        print(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001", 
        settings.FRONTEND_URL,  
    ],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")
    
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse.error(
            user_message="Invalid input data. Please check your request.",
            developer_message="; ".join(errors),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_ref_id=request_id,
            data={"validation_errors": exc.errors()}
        )
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    print(f"Database Error [{request_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            user_message="A database error occurred. Please try again later.",
            developer_message="Database operation failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_ref_id=request_id
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    print(f"Unhandled Error [{request_id}]: {str(exc)}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            user_message="An unexpected error occurred. Please try again later.",
            developer_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_ref_id=request_id
        )
    )

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    return APIResponse.success(
        data={
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0"
        },
        user_message="Service is running",
        developer_message="Health check passed"
    )


@app.get("/")
async def root():
    return APIResponse.success(
        data={
            "message": f"Welcome to {settings.APP_NAME}",
            "version": "1.0.0",
            "documentation": "/api/docs",
            "endpoints": {
                "health": "/health",
            }
        },
        user_message=f"Welcome to {settings.APP_NAME}",
        developer_message="API root endpoint"
    )
@app.on_event("startup")
async def startup_event():
    print("Application starting...")
    print(f"Service: {settings.APP_NAME}")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    print("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutting down...")
    print("Cleanup completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )