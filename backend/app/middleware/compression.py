"""
Response compression middleware for AI Error Translator
"""

import gzip
import brotli
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for compressing HTTP responses
    Supports gzip and brotli compression
    """
    
    def __init__(self, app, min_size: int = 500, compression_level: int = 6):
        super().__init__(app)
        self.min_size = min_size
        self.compression_level = compression_level
        
        # Content types that should be compressed
        self.compressible_types = {
            'application/json',
            'application/javascript',
            'application/xml',
            'text/html',
            'text/css',
            'text/javascript',
            'text/plain',
            'text/xml',
            'application/atom+xml',
            'application/rss+xml',
            'application/xhtml+xml',
            'image/svg+xml'
        }
        
        # Skip compression for certain paths
        self.skip_paths = {
            '/health',
            '/metrics',
            '/docs',
            '/redoc',
            '/openapi.json'
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip compression for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Get the response
        response = await call_next(request)
        
        # Check if we should compress this response
        if not self._should_compress(request, response):
            return response
        
        # Determine compression algorithm
        compression_type = self._get_compression_type(request)
        
        if compression_type == 'br':
            return await self._compress_brotli(response)
        elif compression_type == 'gzip':
            return await self._compress_gzip(response)
        
        return response
    
    def _should_compress(self, request: Request, response: Response) -> bool:
        """
        Determine if response should be compressed
        """
        # Check if client accepts compression
        accept_encoding = request.headers.get('accept-encoding', '').lower()
        if not ('gzip' in accept_encoding or 'br' in accept_encoding):
            return False
        
        # Check if response is already compressed
        if response.headers.get('content-encoding'):
            return False
        
        # Check content type
        content_type = response.headers.get('content-type', '').split(';')[0].lower()
        if content_type not in self.compressible_types:
            return False
        
        # Check response size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) < self.min_size:
            return False
        
        # Check status code
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        return True
    
    def _get_compression_type(self, request: Request) -> Optional[str]:
        """
        Get the best compression type based on client support
        """
        accept_encoding = request.headers.get('accept-encoding', '').lower()
        
        # Prefer brotli over gzip if supported
        if 'br' in accept_encoding:
            return 'br'
        elif 'gzip' in accept_encoding:
            return 'gzip'
        
        return None
    
    async def _compress_brotli(self, response: Response) -> Response:
        """
        Compress response using brotli
        """
        try:
            # Get response content
            content = self._get_response_content(response)
            if not content:
                return response
            
            # Compress content
            compressed_content = brotli.compress(content, quality=self.compression_level)
            
            # Create new response with compressed content
            compressed_response = Response(
                content=compressed_content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # Update headers
            compressed_response.headers['content-encoding'] = 'br'
            compressed_response.headers['content-length'] = str(len(compressed_content))
            
            # Remove vary header conflicts
            if 'vary' in compressed_response.headers:
                vary_values = compressed_response.headers['vary'].split(',')
                vary_values = [v.strip() for v in vary_values]
                if 'accept-encoding' not in [v.lower() for v in vary_values]:
                    vary_values.append('Accept-Encoding')
                compressed_response.headers['vary'] = ', '.join(vary_values)
            else:
                compressed_response.headers['vary'] = 'Accept-Encoding'
            
            logger.debug(f"Brotli compression: {len(content)} -> {len(compressed_content)} bytes "
                        f"({((len(content) - len(compressed_content)) / len(content) * 100):.1f}% reduction)")
            
            return compressed_response
            
        except Exception as e:
            logger.error(f"Brotli compression failed: {e}")
            return response
    
    async def _compress_gzip(self, response: Response) -> Response:
        """
        Compress response using gzip
        """
        try:
            # Get response content
            content = self._get_response_content(response)
            if not content:
                return response
            
            # Compress content
            compressed_content = gzip.compress(content, compresslevel=self.compression_level)
            
            # Create new response with compressed content
            compressed_response = Response(
                content=compressed_content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # Update headers
            compressed_response.headers['content-encoding'] = 'gzip'
            compressed_response.headers['content-length'] = str(len(compressed_content))
            
            # Update vary header
            if 'vary' in compressed_response.headers:
                vary_values = compressed_response.headers['vary'].split(',')
                vary_values = [v.strip() for v in vary_values]
                if 'accept-encoding' not in [v.lower() for v in vary_values]:
                    vary_values.append('Accept-Encoding')
                compressed_response.headers['vary'] = ', '.join(vary_values)
            else:
                compressed_response.headers['vary'] = 'Accept-Encoding'
            
            logger.debug(f"Gzip compression: {len(content)} -> {len(compressed_content)} bytes "
                        f"({((len(content) - len(compressed_content)) / len(content) * 100):.1f}% reduction)")
            
            return compressed_response
            
        except Exception as e:
            logger.error(f"Gzip compression failed: {e}")
            return response
    
    def _get_response_content(self, response: Response) -> Optional[bytes]:
        """
        Extract content from response
        """
        try:
            if hasattr(response, 'body'):
                # For FastAPI Response objects
                if isinstance(response.body, bytes):
                    return response.body
                elif isinstance(response.body, str):
                    return response.body.encode('utf-8')
                elif hasattr(response.body, 'read'):
                    # For file-like objects
                    return response.body.read()
            
            # For streaming responses or other types
            if hasattr(response, 'content'):
                if isinstance(response.content, bytes):
                    return response.content
                elif isinstance(response.content, str):
                    return response.content.encode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return None
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """
        Get compression statistics
        """
        return {
            "middleware": "compression",
            "algorithms": ["gzip", "brotli"],
            "min_size": self.min_size,
            "compression_level": self.compression_level,
            "compressible_types": list(self.compressible_types),
            "skip_paths": list(self.skip_paths)
        }


class GZipMiddleware(BaseHTTPMiddleware):
    """
    Simplified GZip-only compression middleware
    More compatible with existing FastAPI applications
    """
    
    def __init__(self, app, minimum_size: int = 500, compresslevel: int = 6):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
    
    async def dispatch(self, request: Request, call_next):
        # Skip compression for certain paths
        if request.url.path in ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get('accept-encoding', '').lower()
        if 'gzip' not in accept_encoding:
            return await call_next(request)
        
        # Get response
        response = await call_next(request)
        
        # Check if we should compress
        if not self._should_compress(response):
            return response
        
        # Compress if possible
        try:
            return await self._compress_response(response)
        except Exception as e:
            logger.error(f"GZip compression failed: {e}")
            return response
    
    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed"""
        # Already compressed
        if response.headers.get('content-encoding'):
            return False
        
        # Wrong status code
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        # Check content type
        content_type = response.headers.get('content-type', '').split(';')[0].lower()
        compressible_types = {
            'application/json',
            'text/html',
            'text/plain',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/xml',
            'text/xml'
        }
        
        return content_type in compressible_types
    
    async def _compress_response(self, response: Response) -> Response:
        """Compress the response"""
        # This is a simplified implementation
        # In production, you might want to use FastAPI's built-in GZipMiddleware
        return response