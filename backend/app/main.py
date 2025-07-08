from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
import logging
from typing import Optional

from app.models.requests import TranslationRequest, TranslationResponse
from app.services.vision_service import VisionService
from app.services.ai_service import AIService, SubscriptionTier
from app.services.error_analyzer import ErrorAnalyzer
from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.authentication import AuthenticationMiddleware
from app.config import settings

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Error Translator API",
    description="API for translating programming errors using AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)

security = HTTPBearer()

vision_service = VisionService()
ai_service = AIService()
error_analyzer = ErrorAnalyzer(vision_service, ai_service)

@app.get("/")
async def root():
    return {"message": "AI Error Translator API", "version": "1.0.0", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "vision": await vision_service.health_check(),
            "ai_services": ai_service.get_service_status()
        }
    }

@app.post("/translate", response_model=TranslationResponse)
async def translate_error(
    request: TranslationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Translate programming errors using AI analysis
    """
    try:
        logger.info(f"Received translation request for error: {request.errorText[:100]}...")
        
        # Determine user tier from token (temporary implementation)
        user_tier = SubscriptionTier.PRO if "pro" in credentials.credentials.lower() else SubscriptionTier.FREE
        
        result = await error_analyzer.analyze_error(request, user_tier)
        
        logger.info(f"Successfully analyzed error, confidence: {result.confidence}")
        return result
        
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.post("/translate-image", response_model=TranslationResponse)
async def translate_error_from_image(
    image: UploadFile = File(...),
    context: Optional[str] = Form(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Translate programming errors from uploaded images
    """
    try:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        logger.info(f"Received image upload: {image.filename}")
        
        image_data = await image.read()
        
        extracted_text = await vision_service.extract_text_from_image(image_data)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text found in image")
        
        logger.info(f"Extracted text from image: {extracted_text[:100]}...")
        
        request = TranslationRequest(
            errorText=extracted_text,
            context={
                "errorText": extracted_text,
                "language": "unknown",
                "userContext": context or ""
            }
        )
        
        result = await error_analyzer.analyze_error(request)
        
        logger.info(f"Successfully analyzed error from image, confidence: {result.confidence}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during image translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image translation failed: {str(e)}")

@app.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported programming languages
    """
    return {
        "languages": [
            "javascript",
            "typescript",
            "python",
            "java",
            "csharp",
            "cpp",
            "c",
            "go",
            "rust",
            "php",
            "ruby",
            "swift",
            "kotlin"
        ]
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", settings.API_PORT))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.API_DEBUG,
        log_level="info"
    )