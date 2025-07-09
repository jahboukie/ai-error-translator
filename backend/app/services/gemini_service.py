import logging
import google.generativeai as genai
from typing import Dict, List, Any
import json
import re

from app.config import settings
from app.models.requests import ErrorContext, Solution, ErrorType

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini API client"""
        try:
            if not settings.GEMINI_API_KEY:
                logger.warning("Gemini API key not found. AI analysis functionality will be limited.")
                return
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini API client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API client: {str(e)}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Gemini service is available"""
        return self.model is not None
    
    def analyze_error(self, error_text: str, context: ErrorContext) -> Dict[str, Any]:
        """
        Analyze programming error using Gemini AI
        
        Args:
            error_text: The error message/text
            context: Additional context about the error
            
        Returns:
            Analysis results with explanation and solutions
        """
        if not self.model:
            raise Exception("Gemini API client not initialized")
        
        try:
            prompt = self._build_analysis_prompt(error_text, context)
            
            logger.info("Sending request to Gemini API...")
            
            # Configure generation settings for better reliability
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if not response.text:
                raise Exception("Empty response from Gemini API")
            
            # Parse the structured response
            analysis = self._parse_response(response.text)
            
            logger.info(f"Successfully analyzed error with Gemini. Confidence: {analysis.get('confidence', 0)}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during Gemini analysis: {str(e)}")
            raise Exception(f"AI analysis failed: {str(e)}")
    
    def _build_analysis_prompt(self, error_text: str, context: ErrorContext) -> str:
        """
        Build a comprehensive prompt for error analysis
        """
        prompt = f"""You are an expert software developer and debugging assistant. Analyze the following programming error and provide a comprehensive solution.

ERROR TEXT:
{error_text}

CONTEXT:
- Programming Language: {context.language}
- File Path: {context.filePath or 'Unknown'}
- Line Number: {context.lineNumber or 'Unknown'}
- User Context: {context.userContext or 'None provided'}

"""
        
        if context.surroundingCode:
            prompt += f"""
SURROUNDING CODE:
```{context.language}
{context.surroundingCode}
```
"""
        
        if context.dependencies:
            prompt += f"""
PROJECT DEPENDENCIES:
{json.dumps(context.dependencies, indent=2)}
"""
        
        if context.projectStructure:
            prompt += f"""
PROJECT STRUCTURE:
{chr(10).join(context.projectStructure[:20])}  # Limit to first 20 files
"""
        
        prompt += """
Please provide your analysis in the following JSON format:

{
  "explanation": "Clear, human-readable explanation of what this error means and why it occurred",
  "errorType": "one of: syntax_error, type_error, reference_error, runtime_error, import_error, attribute_error, key_error, value_error, index_error, compilation_error, unknown",
  "language": "detected programming language",
  "severity": "one of: low, medium, high, critical",
  "confidence": 0.85,
  "estimatedFixTime": "estimated time to fix (e.g., '5 minutes', '1 hour')",
  "solutions": [
    {
      "title": "Brief solution title",
      "description": "Detailed explanation of this solution approach",
      "code": "actual code fix (if applicable)",
      "confidence": 0.9,
      "steps": [
        "Step 1: Description",
        "Step 2: Description"
      ],
      "relatedDocs": ["https://docs.example.com/relevant-doc"]
    }
  ],
  "preventionTips": [
    "Tip 1 to prevent similar errors",
    "Tip 2 to prevent similar errors"
  ]
}

Important guidelines:
1. Provide 1-3 solutions, ranked by likelihood of success
2. Include actual code fixes when possible
3. Be specific about line numbers and file paths when relevant
4. Consider the user's skill level (provide beginner-friendly explanations)
5. Include relevant documentation links
6. Assign realistic confidence scores (0.0 to 1.0)
7. Detect the programming language accurately
8. Categorize the error type correctly

Respond ONLY with valid JSON. Do not include any text before or after the JSON.
"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini response and extract structured data
        """
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove any markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['explanation', 'errorType', 'language', 'confidence', 'solutions']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate confidence scores
            if not 0 <= parsed['confidence'] <= 1:
                parsed['confidence'] = 0.5
            
            for solution in parsed.get('solutions', []):
                if 'confidence' in solution and not 0 <= solution['confidence'] <= 1:
                    solution['confidence'] = 0.5
            
            # Ensure error type is valid
            valid_error_types = [e.value for e in ErrorType]
            if parsed['errorType'] not in valid_error_types:
                parsed['errorType'] = ErrorType.UNKNOWN.value
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {str(e)}")
            logger.error(f"Full response text: {response_text}")
            
            # Try to extract partial JSON if the response was truncated
            try:
                # Find the start and end of JSON
                start_idx = response_text.find('{')
                if start_idx != -1:
                    # Try to find matching closing brace
                    brace_count = 0
                    end_idx = -1
                    for i, char in enumerate(response_text[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx != -1:
                        partial_json = response_text[start_idx:end_idx]
                        logger.info(f"Attempting to parse partial JSON: {partial_json}")
                        return json.loads(partial_json)
            except:
                pass
            
            return self._create_fallback_response(response_text)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return self._create_fallback_response(response_text)
    
    def _create_fallback_response(self, original_response: str) -> Dict[str, Any]:
        """
        Create a fallback response when parsing fails
        """
        return {
            "explanation": f"I encountered an error while parsing the AI response. Raw response: {original_response[:200]}...",
            "errorType": ErrorType.UNKNOWN.value,
            "language": "unknown",
            "severity": "medium",
            "confidence": 0.3,
            "estimatedFixTime": "unknown",
            "solutions": [
                {
                    "title": "Manual Review Required",
                    "description": "The AI analysis encountered an issue. Please review the error manually or try again.",
                    "confidence": 0.3,
                    "steps": [
                        "Review the error message carefully",
                        "Check the official documentation for your programming language",
                        "Search for similar errors online"
                    ]
                }
            ],
            "preventionTips": [
                "Use proper error handling in your code",
                "Write comprehensive tests",
                "Follow coding best practices"
            ]
        }
    
    async def health_check(self) -> Dict[str, str]:
        """
        Check the health of the Gemini service
        """
        try:
            if not self.model:
                return {"status": "unhealthy", "reason": "Client not initialized"}
            
            # Test with a simple prompt
            test_prompt = "Respond with exactly: {'status': 'ok'}"
            response = self.model.generate_content(test_prompt)
            
            if response.text:
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "reason": "Empty response"}
                
        except Exception as e:
            logger.error(f"Gemini service health check failed: {str(e)}")
            return {"status": "unhealthy", "reason": str(e)}