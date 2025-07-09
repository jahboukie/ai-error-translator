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
from app.routes.auth import router as auth_router
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

# Include authentication routes
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

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
            "vision": await vision_service.health_check(),
            "ai_services": ai_service.get_service_status()
        }
    }

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
        
        result = await error_analyzer.analyze_error(request, user_tier)
        
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
    return {
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
