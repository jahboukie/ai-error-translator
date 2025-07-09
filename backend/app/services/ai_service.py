import logging
from typing import Dict, Any, Optional
from enum import Enum
from .claude_service import ClaudeService
from .gemini_service import GeminiService

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    FREE = "free"
    PRO = "pro"

class AIService:
    def __init__(self):
        self.claude_service = ClaudeService()
        self.gemini_service = GeminiService()
        
    def get_primary_service(self, tier: SubscriptionTier):
        """Get the primary AI service based on subscription tier"""
        # Use Gemini for both free and pro tiers (Claude has connection issues)
        return self.gemini_service
    
    def get_fallback_service(self, tier: SubscriptionTier):
        """Get the fallback AI service"""
        # Use Gemini for both primary and fallback (Claude has connection issues)
        return self.gemini_service
    
    async def analyze_error(self, 
                          error_text: str, 
                          context = None,
                          user_tier: SubscriptionTier = SubscriptionTier.FREE) -> Dict[str, Any]:
        """
        Analyze error using appropriate AI service based on user tier
        with automatic fallback if primary service fails
        """
        
        primary_service = self.get_primary_service(user_tier)
        fallback_service = self.get_fallback_service(user_tier)
        
        # Try primary service first
        try:
            if primary_service.is_available():
                logger.info(f"Using primary service for {user_tier.value} tier")
                result = primary_service.analyze_error(error_text, context)
                result["service_used"] = "gemini"
                return result
            else:
                logger.warning(f"Primary service not available for {user_tier.value} tier")
        except Exception as e:
            logger.error(f"Primary service failed for {user_tier.value} tier: {e}")
            logger.exception("Full traceback:")
        
        # Fallback to secondary service
        try:
            if fallback_service.is_available():
                logger.info(f"Using fallback service for {user_tier.value} tier")
                result = fallback_service.analyze_error(error_text, context)
                result["service_used"] = "gemini"
                result["fallback_used"] = True
                return result
            else:
                logger.error(f"Fallback service also not available for {user_tier.value} tier")
        except Exception as e:
            logger.error(f"Fallback service also failed for {user_tier.value} tier: {e}")
            logger.exception("Full fallback traceback:")
        
        # If both services fail, return error
        raise Exception("Both AI services are currently unavailable. Please try again later.")
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all AI services"""
        return {
            "claude_available": self.claude_service.is_available(),
            "gemini_available": self.gemini_service.is_available()
        }