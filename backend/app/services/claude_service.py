import anthropic
import logging
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the Claude API client"""
        try:
            if not settings.CLAUDE_API_KEY:
                logger.warning("Claude API key not provided")
                return
                
            self.client = anthropic.Anthropic(
                api_key=settings.CLAUDE_API_KEY
            )
            logger.info("Claude API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Claude service is available"""
        return self.client is not None
    
    def analyze_error(self, error_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze error using Claude API"""
        if not self.client:
            raise Exception("Claude API client not initialized")
        
        try:
            # Enhanced prompt for better debugging
            prompt = f"""
You are an expert software engineer specializing in debugging and error analysis. 
Analyze this programming error and provide comprehensive solutions.

ERROR: {error_text}

CONTEXT:
{context or "No additional context provided"}

Please provide:
1. A clear explanation of what this error means
2. The most likely causes
3. Step-by-step solutions with code examples
4. Best practices to prevent this error

Response format should be JSON with:
- explanation: Clear explanation of the error
- error_type: Type of error (syntax, runtime, type, etc.)
- solutions: Array of solution objects with title, description, code, and steps
- confidence: Confidence score (0.0-1.0)
"""
            
            logger.info("Sending request to Claude API...")
            
            response = self.client.messages.create(
                model=settings.PRO_TIER_MODEL,
                max_tokens=1000,
                timeout=30.0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response content
            content = response.content[0].text
            
            # Parse JSON response (Claude is generally good at following JSON format)
            try:
                import json
                result = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = {
                    "explanation": content,
                    "error_type": "unknown",
                    "solutions": [{
                        "title": "Claude Analysis",
                        "description": content,
                        "code": "",
                        "steps": ["Review the analysis above"],
                        "confidence": 0.9
                    }],
                    "confidence": 0.9
                }
            
            logger.info(f"Successfully analyzed error with Claude. Confidence: {result.get('confidence', 0.9)}")
            return result
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise Exception(f"Claude API error: {str(e)}")