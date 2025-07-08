# AI Error Translator Backend

FastAPI backend service for the AI Error Translator VS Code extension.

## Features

- **Error Analysis**: AI-powered error translation using Google Gemini
- **OCR Support**: Extract text from error screenshots using Google Vision API
- **Rate Limiting**: Built-in request rate limiting
- **Authentication**: API key-based authentication
- **Docker Support**: Containerized deployment
- **Health Monitoring**: Comprehensive health checks

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository (if not already done)
cd backend

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python run_dev.py
```

The API will be available at `http://localhost:8000`

### 3. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or run just the API
docker build -t ai-error-translator-api .
docker run -p 8000:8000 --env-file .env ai-error-translator-api
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT_ID` | Google Cloud project ID | "" |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | "" |
| `GEMINI_API_KEY` | Google Gemini API key | "" |
| `API_SECRET_KEY` | Secret key for JWT signing | "default-secret-key" |
| `API_HOST` | Host to bind to | "0.0.0.0" |
| `API_PORT` | Port to listen on | 8000 |
| `API_DEBUG` | Enable debug mode | false |
| `RATE_LIMIT_REQUESTS` | Requests per window | 100 |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | 3600 |

### Google Cloud Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing

2. **Enable APIs**
   ```bash
   gcloud services enable vision.googleapis.com
   gcloud services enable generativeai.googleapis.com
   ```

3. **Create Service Account**
   ```bash
   gcloud iam service-accounts create ai-error-translator
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:ai-error-translator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/serviceusage.serviceUsageViewer"
   ```

4. **Download Credentials**
   ```bash
   gcloud iam service-accounts keys create credentials.json \
     --iam-account=ai-error-translator@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

5. **Get Gemini API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/)
   - Generate an API key

## API Endpoints

### Core Endpoints

- `POST /translate` - Translate error from text
- `POST /translate-image` - Translate error from image
- `GET /health` - Health check
- `GET /supported-languages` - Get supported languages

### Example Request

```bash
curl -X POST "http://localhost:8000/translate" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "errorText": "TypeError: Cannot read property '\''map'\'' of undefined",
    "context": {
      "errorText": "TypeError: Cannot read property '\''map'\'' of undefined",
      "language": "javascript",
      "surroundingCode": "const result = data.map(item => item.name);"
    }
  }'
```

### Example Response

```json
{
  "explanation": "This error occurs when you're trying to call the 'map' method on a variable that is undefined or null.",
  "solutions": [
    {
      "title": "Add null check before mapping",
      "description": "Ensure the data exists before calling map",
      "code": "const result = data && data.map(item => item.name);",
      "confidence": 0.9,
      "steps": [
        "Check if data is not null or undefined",
        "Use logical AND operator for safe access",
        "Consider providing a default empty array"
      ]
    }
  ],
  "confidence": 0.85,
  "errorType": "type_error",
  "language": "javascript",
  "severity": "medium"
}
```

## Development

### Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models/
│   │   └── requests.py      # Pydantic models
│   ├── services/
│   │   ├── vision_service.py    # Google Vision API
│   │   ├── gemini_service.py    # Google Gemini API
│   │   └── error_analyzer.py   # Error analysis logic
│   └── middleware/
│       ├── authentication.py   # Auth middleware
│       └── rate_limiting.py    # Rate limiting
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service setup
└── run_dev.py             # Development server
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### API Documentation

When running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Deployment

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ai-error-translator-api

# Deploy to Cloud Run
gcloud run deploy ai-error-translator-api \
  --image gcr.io/YOUR_PROJECT_ID/ai-error-translator-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT_ID=YOUR_PROJECT_ID
```

### Other Platforms

- **Heroku**: Use `Procfile` with `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **AWS ECS**: Use the Dockerfile with ECS task definition
- **Azure Container Instances**: Deploy using the Docker image

## Monitoring

### Health Checks

- `/health` - Overall service health
- Service-specific health checks for Vision and Gemini APIs

### Logging

Logs are structured and include:
- Request/response times
- Error details
- Rate limiting events
- Authentication attempts

### Metrics

Consider adding:
- Prometheus metrics
- Request/error rates
- Response times
- API usage by client

## Security

- **Authentication**: API key-based auth
- **Rate Limiting**: Configurable per-client limits
- **CORS**: Configurable allowed origins
- **Input Validation**: Pydantic model validation
- **Error Handling**: No sensitive data in error responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details