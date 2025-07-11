from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import logging
from typing import Optional

from app.models.requests import TranslationRequest, TranslationResponse
from app.services.vision_service import VisionService
from app.services.ai_service import AIService, SubscriptionTier
from app.services.error_analyzer import ErrorAnalyzer
from app.services.stripe_service import StripeService
from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.jwt_authentication import JWTAuthenticationMiddleware, get_current_user
from app.middleware.usage_logging import UsageLoggingMiddleware
from app.middleware.compression import CompressionMiddleware
from app.monitoring.middleware import MonitoringMiddleware, SecurityMonitoringMiddleware, HealthCheckMiddleware
from app.monitoring.logging import setup_logging
from app.monitoring.error_tracking import setup_error_tracking
from app.monitoring.metrics import setup_metrics_endpoint
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.database.connection import db_manager
from app.services.cache_service import cache_service
from app.config import settings

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup structured logging early
setup_logging()

app = FastAPI(
    title="AI Error Translator API",
    description="API for translating programming errors using AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include authentication routes
app.include_router(auth_router)
app.include_router(users_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Create middleware instances
rate_limit_middleware = RateLimitMiddleware(app)
compression_middleware = CompressionMiddleware(app)

app.add_middleware(CompressionMiddleware)  # Should be first for best compression
app.add_middleware(MonitoringMiddleware)
app.add_middleware(SecurityMonitoringMiddleware)
app.add_middleware(HealthCheckMiddleware)
app.add_middleware(UsageLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthenticationMiddleware)

security = HTTPBearer()

vision_service = VisionService()
ai_service = AIService()
error_analyzer = ErrorAnalyzer(vision_service, ai_service)
stripe_service = StripeService()

@app.get("/")
async def root():
    return {"message": "AI Error Translator API", "version": "1.0.0", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": await db_manager.health_check(),
            "vision": await vision_service.health_check(),
            "ai_services": ai_service.get_service_status(),
            "cache": await cache_service.health_check()
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    try:
        # Setup monitoring
        setup_logging()
        setup_error_tracking()
        
        # Create database tables if they don't exist
        await db_manager.create_tables()
        logger.info("Database initialized successfully")
        
        # Connect to Redis cache
        await cache_service.connect()
        logger.info("Cache service initialized")
        
        # Setup metrics endpoint
        metrics_app = setup_metrics_endpoint()
        app.mount("/metrics", metrics_app)
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        # Don't fail startup, just log the error

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    try:
        await db_manager.close()
        logger.info("Database connections closed")
        
        await cache_service.disconnect()
        logger.info("Cache service disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.post("/translate", response_model=TranslationResponse)
async def translate_error(
    request: TranslationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Translate programming errors using AI analysis
    """
    try:
        logger.info(f"Received translation request from user {current_user['user_id']} for error: {request.errorText[:100]}...")
        
        # Get user tier from JWT token
        user_tier = SubscriptionTier.PRO if current_user["tier"] == "pro" else SubscriptionTier.FREE
        user_tier_str = "pro" if user_tier == SubscriptionTier.PRO else "free"
        
        # Check cache first
        cached_result = await cache_service.get_cached_translation(
            error_text=request.errorText,
            language=request.language,
            user_tier=user_tier_str
        )
        
        if cached_result:
            logger.info(f"Returning cached translation for user {current_user['user_id']}")
            return cached_result
        
        # If not in cache, process the request
        result = await error_analyzer.analyze_error(request, user_tier)
        
        # Cache the result
        await cache_service.cache_translation(
            error_text=request.errorText,
            language=request.language,
            user_tier=user_tier_str,
            translation_result=result.dict()
        )
        
        logger.info(f"Successfully analyzed error for user {current_user['user_id']}, confidence: {result.confidence}")
        return result
        
    except Exception as e:
        logger.error(f"Error during translation for user {current_user['user_id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

# Image upload endpoint removed to avoid feature bloat
# Use text-based error translation instead

@app.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported programming languages
    """
    # Check cache first
    cached_languages = await cache_service.get_cached_api_response("supported-languages", {})
    if cached_languages:
        return cached_languages
    
    # Generate response
    response = {
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
    
    # Cache for 1 hour
    await cache_service.cache_api_response("supported-languages", {}, response)
    
    return response

# Claude API test endpoint removed - using Gemini only

@app.post("/create-checkout-session")
async def create_checkout_session(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe checkout session for subscription"""
    try:
        body = await request.json()
        price_id = body.get("price_id")
        customer_email = body.get("customer_email")
        
        if not price_id or not customer_email:
            raise HTTPException(status_code=400, detail="price_id and customer_email are required")
        
        success_url = f"{settings.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/cancel"
        
        session = stripe_service.create_checkout_session(
            price_id=price_id,
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        logger.info(f"Created checkout session for user {current_user['user_id']}")
        return session
    except Exception as e:
        logger.error(f"Error creating checkout session for user {current_user['user_id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")

@app.post("/create-portal-session")
async def create_portal_session(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a customer portal session for billing management"""
    try:
        body = await request.json()
        customer_id = body.get("customer_id")
        
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id is required")
        
        return_url = f"{settings.FRONTEND_URL}/account"
        
        session = stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=return_url
        )
        
        logger.info(f"Created portal session for user {current_user['user_id']}")
        return session
    except Exception as e:
        logger.error(f"Error creating portal session for user {current_user['user_id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")

@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
        event = stripe_service.verify_webhook(payload, signature)
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            logger.info(f"Checkout session completed: {session['id']}")
            # TODO: Update user subscription in database
            
        elif event['type'] == 'customer.subscription.created':
            subscription = event['data']['object']
            logger.info(f"Subscription created: {subscription['id']}")
            # TODO: Activate user subscription
            
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            logger.info(f"Subscription updated: {subscription['id']}")
            # TODO: Update user subscription status
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            logger.info(f"Subscription deleted: {subscription['id']}")
            # TODO: Deactivate user subscription
            
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

@app.get("/pricing")
async def get_pricing():
    """Get pricing information"""
    # Check cache first
    cached_pricing = await cache_service.get_cached_api_response("pricing", {})
    if cached_pricing:
        return cached_pricing
    
    # Generate response
    response = {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "translations": 20,
                "features": ["20 translations/month", "Gemini AI", "Basic support"]
            },
            {
                "name": "Pro",
                "price": 12,
                "translations": 250,
                "features": ["250 translations/month", "Enhanced AI analysis", "Priority support"],
                "stripe_price_id": "price_1RixTQELGHd3NbdJfRUwyjY5"
            },
            {
                "name": "Add-on",
                "price": 5,
                "translations": 50,
                "features": ["50 additional translations", "One-time purchase"],
                "stripe_price_id": "price_1RixTVELGHd3NbdJ3IZHmDhb"
            }
        ]
    }
    
    # Cache for 30 minutes
    await cache_service.cache_api_response("pricing", {}, response)
    
    return response

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return await cache_service.get_cache_stats()

@app.get("/database/stats")
async def get_database_stats():
    """Get database connection pool statistics"""
    return await db_manager.get_pool_stats()

@app.get("/rate-limit/stats")
async def get_rate_limit_stats():
    """Get rate limiting statistics"""
    return await rate_limit_middleware.get_rate_limit_stats()

@app.get("/compression/stats")
async def get_compression_stats():
    """Get compression middleware statistics"""
    return compression_middleware.get_compression_stats()

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
