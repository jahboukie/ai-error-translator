# Security Guidelines

## Overview
This document outlines security best practices for the AI Error Translator application.

## Secrets Management

### Environment Variables
- All sensitive data must be stored in environment variables
- Never commit `.env` files to version control
- Use `.env.example` as a template for required variables
- Different environments (dev, staging, prod) should have separate configurations

### Production Secrets
For production deployment, use Google Cloud Secret Manager:

1. **Setup secrets using the provided script:**
   ```bash
   cd backend
   ./setup-secrets.sh
   ```

2. **Required secrets:**
   - `gemini-api-key`: Gemini API key for AI services
   - `jwt-secret-key`: JWT secret key (min 64 characters)
   - `api-secret-key`: API secret key (min 32 characters)
   - `stripe-secret-key`: Stripe secret key for billing
   - `stripe-webhook-secret`: Stripe webhook secret

3. **Grant access to Cloud Run:**
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member=serviceAccount:PROJECT_ID-compute@developer.gserviceaccount.com \
     --role=roles/secretmanager.secretAccessor
   ```

### Development
For local development:
1. Copy `backend/.env.example` to `backend/.env`
2. Fill in your development values
3. Never commit the `.env` file

## Authentication

### JWT Tokens
- All API endpoints (except public ones) require JWT authentication
- Tokens expire after 30 minutes
- Refresh tokens are valid for 30 days
- Use strong secret keys (minimum 64 characters for JWT)

### API Keys
- API keys are generated as JWT tokens
- Include user ID and subscription tier
- Validate on every request

### Protected Endpoints
The following endpoints require authentication:
- `/translate` - Error translation
- `/create-checkout-session` - Stripe checkout
- `/create-portal-session` - Stripe portal
- All endpoints except: `/`, `/health`, `/docs`, `/auth/*`, `/webhook`, `/pricing`

## CORS Configuration

### Production
Set `ALLOWED_ORIGINS` environment variable to your domain:
```
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Development
Default development origins are:
- `http://localhost:3000`
- `http://localhost:5173`

## Rate Limiting

### Current Limits
- 100 requests per hour per IP/API key
- Rate limiting applies to all endpoints except health checks

### Configuration
Adjust via environment variables:
```
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

## Input Validation

### Error Text
- Maximum length: 10,000 characters
- HTML/script tags are stripped
- Special characters are sanitized

### Context Data
- File paths are validated
- Code snippets are length-limited
- Language detection is validated against supported languages

## Error Handling

### Security Considerations
- Error messages don't leak sensitive information
- Stack traces are logged but not exposed to users
- Authentication errors use generic messages

### Logging
- All authentication attempts are logged
- Failed requests are tracked
- Sensitive data is not logged

## Dependencies

### Updates
- Regularly update dependencies to patch security vulnerabilities
- Use `npm audit` and `pip-audit` to check for vulnerabilities
- Pin dependency versions in production

### Validation
- All user inputs are validated using Pydantic models
- SQL injection protection (when database is added)
- XSS prevention through proper escaping

## Deployment Security

### Docker
- Use non-root user in containers
- Minimal base images
- Multi-stage builds to reduce attack surface

### Cloud Run
- Uses managed SSL certificates
- Automatic scaling with security patches
- Network isolation

## Monitoring

### Security Events
- Failed authentication attempts
- Rate limit violations
- Suspicious API usage patterns

### Alerting
- Set up alerts for security events
- Monitor for unusual traffic patterns
- Track API key usage

## Incident Response

### If Secrets Are Compromised
1. Immediately rotate all affected secrets
2. Update Secret Manager with new values
3. Redeploy application
4. Monitor for unauthorized access
5. Notify affected users if necessary

### If Vulnerabilities Are Found
1. Assess impact and severity
2. Develop and test fix
3. Deploy fix immediately for critical issues
4. Update documentation
5. Notify users if necessary

## Compliance

### Data Protection
- No sensitive user data is stored
- Error messages are processed but not permanently stored
- Logs are rotated and cleaned regularly

### API Security
- HTTPS only in production
- Proper HTTP security headers
- Input validation and sanitization

## Regular Security Tasks

### Monthly
- Review and rotate secrets
- Update dependencies
- Check for security advisories

### Quarterly
- Security audit of codebase
- Review access controls
- Update security documentation

### Annually
- Penetration testing
- Security architecture review
- Update incident response procedures