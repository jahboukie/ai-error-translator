from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class ErrorType(str, Enum):
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    REFERENCE_ERROR = "reference_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    ATTRIBUTE_ERROR = "attribute_error"
    KEY_ERROR = "key_error"
    VALUE_ERROR = "value_error"
    INDEX_ERROR = "index_error"
    COMPILATION_ERROR = "compilation_error"
    UNKNOWN = "unknown"

class ErrorContext(BaseModel):
    errorText: str = Field(..., description="The error text or message")
    language: str = Field(default="unknown", description="Programming language")
    filePath: Optional[str] = Field(None, description="Path to the file with the error")
    lineNumber: Optional[int] = Field(None, description="Line number where error occurred")
    surroundingCode: Optional[str] = Field(None, description="Code context around the error")
    projectStructure: Optional[List[str]] = Field(None, description="Project file structure")
    recentChanges: Optional[str] = Field(None, description="Recent git changes")
    dependencies: Optional[Dict[str, Any]] = Field(None, description="Project dependencies")
    userContext: Optional[str] = Field(None, description="User-provided context")

class TranslationRequest(BaseModel):
    errorText: str = Field(..., description="The error text to translate")
    context: ErrorContext = Field(..., description="Context information about the error")

class Solution(BaseModel):
    title: str = Field(..., description="Brief title of the solution")
    description: str = Field(..., description="Detailed description of the solution")
    code: Optional[str] = Field(None, description="Code snippet to fix the error")
    filePath: Optional[str] = Field(None, description="File path where to apply the fix")
    lineNumber: Optional[int] = Field(None, description="Line number where to apply the fix")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this solution")
    steps: List[str] = Field(default_factory=list, description="Step-by-step instructions")
    relatedDocs: Optional[List[str]] = Field(None, description="Links to relevant documentation")

class TranslationResponse(BaseModel):
    explanation: str = Field(..., description="Human-readable explanation of the error")
    solutions: List[Solution] = Field(..., description="List of potential solutions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in the analysis")
    errorType: ErrorType = Field(..., description="Categorized error type")
    language: str = Field(..., description="Detected programming language")
    severity: str = Field(default="medium", description="Error severity: low, medium, high, critical")
    estimatedFixTime: Optional[str] = Field(None, description="Estimated time to fix")
    preventionTips: Optional[List[str]] = Field(None, description="Tips to prevent similar errors")

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")