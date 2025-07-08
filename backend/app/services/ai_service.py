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
        if tier == SubscriptionTier.PRO:
            return self.claude_service
        else:  # FREE tier
            return self.gemini_service
    
    def get_fallback_service(self, tier: SubscriptionTier):
        """Get the fallback AI service"""
        if tier == SubscriptionTier.PRO:
            return self.gemini_service  # Fallback to Gemini if Claude fails
        else:  # FREE tier
            return self.claude_service  # Fallback to Claude if Gemini fails
    
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
                result = await primary_service.analyze_error(error_text, context)
                result["service_used"] = "claude" if user_tier == SubscriptionTier.PRO else "gemini"
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
                result = await fallback_service.analyze_error(error_text, context)
                result["service_used"] = "gemini" if user_tier == SubscriptionTier.PRO else "claude"
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