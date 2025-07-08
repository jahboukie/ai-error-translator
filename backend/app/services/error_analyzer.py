import logging
import re
from typing import Dict, List, Optional
import asyncio

from app.models.requests import TranslationRequest, TranslationResponse, Solution, ErrorType
from app.services.vision_service import VisionService
from app.services.ai_service import AIService, SubscriptionTier

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    def __init__(self, vision_service: VisionService, ai_service: AIService):
        self.vision_service = vision_service
        self.ai_service = ai_service
        
        # Error pattern matching for quick categorization
        self.error_patterns = {
            ErrorType.SYNTAX_ERROR: [
                r"SyntaxError",
                r"Invalid syntax",
                r"unexpected token",
                r"missing semicolon",
                r"unterminated string"
            ],
            ErrorType.TYPE_ERROR: [
                r"TypeError",
                r"Cannot read propert(y|ies) of",
                r"is not a function",
                r"is not defined",
                r"has no attribute"
            ],
            ErrorType.REFERENCE_ERROR: [
                r"ReferenceError",
                r"is not defined",
                r"Cannot access before initialization"
            ],
            ErrorType.IMPORT_ERROR: [
                r"ImportError",
                r"ModuleNotFoundError",
                r"Cannot resolve module",
                r"No module named"
            ],
            ErrorType.ATTRIBUTE_ERROR: [
                r"AttributeError",
                r"has no attribute",
                r"object has no attribute"
            ],
            ErrorType.KEY_ERROR: [
                r"KeyError",
                r"key not found"
            ],
            ErrorType.VALUE_ERROR: [
                r"ValueError",
                r"invalid literal",
                r"could not convert"
            ],
            ErrorType.INDEX_ERROR: [
                r"IndexError",
                r"list index out of range",
                r"string index out of range"
            ],
            ErrorType.COMPILATION_ERROR: [
                r"compilation failed",
                r"build failed",
                r"error CS\d+",
                r"error C\d+"
            ]
        }
    
    async def analyze_error(self, request: TranslationRequest, user_tier: SubscriptionTier = SubscriptionTier.FREE) -> TranslationResponse:
        """
        Analyze programming error and generate solutions
        
        Args:
            request: Translation request containing error text and context
            user_tier: User's subscription tier (FREE or PRO)
            
        Returns:
            Comprehensive translation response with solutions
        """
        try:
            logger.info(f"Starting error analysis for: {request.errorText[:100]}...")
            
            # Step 1: Pre-process and categorize error
            error_type = self._categorize_error(request.errorText)
            detected_language = self._detect_language(request)
            
            # Step 2: Get AI analysis using tier-based service
            ai_analysis = await self.ai_service.analyze_error(
                request.errorText, 
                request.context,
                user_tier
            )
            
            # Step 3: Enhance with pattern-based insights
            enhanced_solutions = self._enhance_solutions(
                ai_analysis.get('solutions', []), 
                error_type, 
                detected_language
            )
            
            # Step 4: Calculate overall confidence
            overall_confidence = self._calculate_confidence(
                ai_analysis.get('confidence', 0.5),
                error_type,
                request.context
            )
            
            # Step 5: Build response
            response = TranslationResponse(
                explanation=ai_analysis.get('explanation', 'Error analysis could not be completed'),
                solutions=enhanced_solutions,
                confidence=overall_confidence,
                errorType=ErrorType(ai_analysis.get('errorType', error_type.value)),
                language=ai_analysis.get('language', detected_language),
                severity=ai_analysis.get('severity', 'medium'),
                estimatedFixTime=ai_analysis.get('estimatedFixTime'),
                preventionTips=ai_analysis.get('preventionTips', [])
            )
            
            logger.info(f"Analysis complete. Error type: {response.errorType}, Confidence: {response.confidence}")
            return response
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            # Return fallback response
            return self._create_fallback_response(request, str(e))
    
    def _categorize_error(self, error_text: str) -> ErrorType:
        """
        Categorize error based on pattern matching
        """
        error_text_lower = error_text.lower()
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_text, re.IGNORECASE):
                    logger.info(f"Categorized error as: {error_type.value}")
                    return error_type
        
        logger.info("Could not categorize error, defaulting to unknown")
        return ErrorType.UNKNOWN
    
    def _detect_language(self, request: TranslationRequest) -> str:
        """
        Detect programming language from context and error patterns
        """
        context = request.context
        
        # Check explicit language from context
        if context.language and context.language != "unknown":
            return context.language
        
        # Check file extension
        if context.filePath:
            extension_map = {
                '.js': 'javascript',
                '.ts': 'typescript',
                '.py': 'python',
                '.java': 'java',
                '.cs': 'csharp',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust',
                '.php': 'php',
                '.rb': 'ruby',
                '.swift': 'swift',
                '.kt': 'kotlin'
            }
            
            for ext, lang in extension_map.items():
                if context.filePath.endswith(ext):
                    return lang
        
        # Check error patterns for language hints
        error_text = request.errorText.lower()
        
        if any(keyword in error_text for keyword in ['typeerror', 'referenceerror', 'syntaxerror']):
            if 'cannot read propert' in error_text:
                return 'javascript'
            elif 'has no attribute' in error_text:
                return 'python'
        
        if 'modulenotfounderror' in error_text or 'importerror' in error_text:
            return 'python'
        
        if 'error cs' in error_text:
            return 'csharp'
        
        if 'error c' in error_text and 'cs' not in error_text:
            return 'cpp'
        
        logger.info("Could not detect language, defaulting to unknown")
        return 'unknown'
    
    def _enhance_solutions(
        self, 
        ai_solutions: List[Dict], 
        error_type: ErrorType, 
        language: str
    ) -> List[Solution]:
        """
        Enhance AI-generated solutions with additional insights
        """
        solutions = []
        
        for sol_dict in ai_solutions:
            # Convert dict to Solution model
            solution = Solution(
                title=sol_dict.get('title', 'Solution'),
                description=sol_dict.get('description', ''),
                code=sol_dict.get('code'),
                confidence=sol_dict.get('confidence', 0.5),
                steps=sol_dict.get('steps', []),
                relatedDocs=sol_dict.get('relatedDocs', [])
            )
            
            # Add language-specific documentation links
            if not solution.relatedDocs:
                solution.relatedDocs = self._get_documentation_links(error_type, language)
            
            solutions.append(solution)
        
        # Add pattern-based solutions if AI didn't provide enough
        if len(solutions) < 2:
            pattern_solution = self._get_pattern_based_solution(error_type, language)
            if pattern_solution:
                solutions.append(pattern_solution)
        
        # Sort by confidence
        solutions.sort(key=lambda x: x.confidence, reverse=True)
        
        return solutions[:3]  # Return top 3 solutions
    
    def _get_documentation_links(self, error_type: ErrorType, language: str) -> List[str]:
        """
        Get relevant documentation links based on error type and language
        """
        docs_map = {
            'javascript': {
                ErrorType.TYPE_ERROR: ['https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors'],
                ErrorType.REFERENCE_ERROR: ['https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Not_defined'],
                ErrorType.SYNTAX_ERROR: ['https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Unexpected_token']
            },
            'python': {
                ErrorType.TYPE_ERROR: ['https://docs.python.org/3/library/exceptions.html#TypeError'],
                ErrorType.ATTRIBUTE_ERROR: ['https://docs.python.org/3/library/exceptions.html#AttributeError'],
                ErrorType.IMPORT_ERROR: ['https://docs.python.org/3/library/exceptions.html#ImportError']
            },
            'java': {
                ErrorType.COMPILATION_ERROR: ['https://docs.oracle.com/javase/tutorial/getStarted/problems/'],
                ErrorType.RUNTIME_ERROR: ['https://docs.oracle.com/javase/tutorial/essential/exceptions/']
            }
        }
        
        return docs_map.get(language, {}).get(error_type, [])
    
    def _get_pattern_based_solution(self, error_type: ErrorType, language: str) -> Optional[Solution]:
        """
        Generate a pattern-based solution for common errors
        """
        solutions_map = {
            (ErrorType.TYPE_ERROR, 'javascript'): Solution(
                title="Check Object Properties",
                description="Ensure the object exists and has the property you're trying to access",
                code="if (obj && obj.property) {\n    // Use obj.property safely\n}",
                confidence=0.7,
                steps=[
                    "Check if the object is not null or undefined",
                    "Verify the property exists before accessing it",
                    "Use optional chaining (obj?.property) if available"
                ]
            ),
            (ErrorType.IMPORT_ERROR, 'python'): Solution(
                title="Check Module Installation",
                description="Verify the module is installed and the import path is correct",
                code="pip install module_name",
                confidence=0.8,
                steps=[
                    "Check if the module is installed: pip list | grep module_name",
                    "Install the module if missing: pip install module_name",
                    "Verify the import path and module name spelling"
                ]
            )
        }
        
        return solutions_map.get((error_type, language))
    
    def _calculate_confidence(
        self, 
        ai_confidence: float, 
        error_type: ErrorType, 
        context
    ) -> float:
        """
        Calculate overall confidence based on multiple factors
        """
        confidence = ai_confidence
        
        # Boost confidence for well-categorized errors
        if error_type != ErrorType.UNKNOWN:
            confidence += 0.1
        
        # Boost confidence if we have good context
        if context.surroundingCode:
            confidence += 0.1
        
        if context.language and context.language != "unknown":
            confidence += 0.05
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _create_fallback_response(self, request: TranslationRequest, error_msg: str) -> TranslationResponse:
        """
        Create a fallback response when analysis fails
        """
        error_type = self._categorize_error(request.errorText)
        
        return TranslationResponse(
            explanation=f"I encountered an issue analyzing this error: {error_msg}. Here's what I can tell you based on pattern matching.",
            solutions=[
                Solution(
                    title="Manual Investigation Required",
                    description="The automatic analysis failed. Please review the error manually.",
                    confidence=0.3,
                    steps=[
                        "Copy the exact error message",
                        "Search for it in the official documentation",
                        "Check Stack Overflow for similar issues",
                        "Review recent code changes"
                    ]
                )
            ],
            confidence=0.3,
            errorType=error_type,
            language=self._detect_language(request),
            severity="medium"
        )