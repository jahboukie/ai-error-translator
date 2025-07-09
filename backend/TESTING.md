# Testing Guide

This document explains how to run tests for the AI Error Translator backend.

## Test Structure

The test suite is organized into three levels:

### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Fast execution, no external dependencies
- Mock external services and databases
- Examples: `test_auth_service.py`, `test_jwt_middleware.py`

### Integration Tests (`tests/integration/`)
- Test components working together
- Use real FastAPI TestClient
- May use test databases or mock services
- Examples: `test_auth_endpoints.py`

### End-to-End Tests (`tests/e2e/`)
- Test complete user workflows
- Test real API endpoints with authentication
- Simulate real user interactions
- Examples: `test_auth_flow.py`

## Prerequisites

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set Environment Variables
For testing, you can use default values or set:
```bash
export JWT_SECRET_KEY="test_jwt_secret_key_for_testing_only"
export API_SECRET_KEY="test_api_secret_key_for_testing_only"
export API_DEBUG=true
```

## Running Tests

### Using the Test Runner Script
```bash
# Run all tests
./run_tests.sh all

# Run specific test types
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh e2e

# Run quick tests (unit only)
./run_tests.sh quick

# Run security tests
./run_tests.sh security

# Generate test report
./run_tests.sh report

# Clean test artifacts
./run_tests.sh clean
```

### Using pytest directly
```bash
# Run all tests
pytest

# Run specific test files
pytest tests/unit/test_auth_service.py

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run with markers
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"

# Run specific test methods
pytest tests/unit/test_auth_service.py::TestAuthService::test_create_access_token
```

## Test Configuration

### pytest.ini
The `pytest.ini` file contains:
- Test discovery patterns
- Coverage settings
- Custom markers
- Environment variables for testing

### Custom Markers
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.slow` - Slow tests

## Test Development

### Writing Unit Tests
```python
import pytest
from app.services.auth_service import AuthService

class TestAuthService:
    def setup_method(self):
        self.auth_service = AuthService()
    
    def test_create_access_token(self):
        data = {"user_id": "test_user", "tier": "pro"}
        token = self.auth_service.create_access_token(data)
        assert token is not None
```

### Writing Integration Tests
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAuthEndpoints:
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_validate_token_endpoint(self):
        response = self.client.post("/auth/validate", headers={"Authorization": "Bearer token"})
        assert response.status_code in [200, 401]
```

### Async Tests
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Test Coverage

### Coverage Goals
- Unit tests: 90%+ coverage
- Integration tests: 80%+ coverage
- Overall: 85%+ coverage

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Coverage Exclusions
Add to `.coveragerc` to exclude files:
```ini
[run]
omit = 
    */tests/*
    */venv/*
    */migrations/*
```

## Continuous Integration

### GitHub Actions
Example workflow:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: ./run_tests.sh all
```

## Test Data Management

### Test Fixtures
Use pytest fixtures for reusable test data:
```python
@pytest.fixture
def auth_service():
    return AuthService()

@pytest.fixture
def test_user_token(auth_service):
    return auth_service.create_api_key("test_user", "pro")
```

### Test Database
For tests requiring database:
```python
@pytest.fixture
def test_db():
    # Setup test database
    db = create_test_database()
    yield db
    # Cleanup
    db.drop_all()
```

## Mocking

### Mock External Services
```python
from unittest.mock import patch, Mock

@patch('app.services.stripe_service.stripe.checkout.Session.create')
def test_checkout_session(mock_create):
    mock_create.return_value = Mock(id="test_session")
    # Test code here
```

### Mock Environment Variables
```python
@patch.dict(os.environ, {'API_DEBUG': 'true'})
def test_debug_mode():
    # Test code here
```

## Performance Testing

### Load Testing
```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load/test_auth_load.py
```

### Memory Testing
```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler tests/unit/test_auth_service.py
```

## Security Testing

### Authentication Tests
All authentication flows are tested:
- Token creation and validation
- Token refresh
- Token expiration
- Invalid token handling
- Tier-based access control

### Security Checks
```bash
# Run security tests
./run_tests.sh security

# Check for secrets
../check-secrets.sh
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure app is in Python path
   export PYTHONPATH="${PYTHONPATH}:./app"
   ```

2. **Module Not Found**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Test Failures**
   ```bash
   # Run with verbose output
   pytest -v -s
   ```

4. **Coverage Issues**
   ```bash
   # See what's not covered
   pytest --cov=app --cov-report=term-missing
   ```

### Debug Mode
```bash
# Run tests with debug output
pytest -v -s --tb=long

# Run single test with debugging
pytest tests/unit/test_auth_service.py::TestAuthService::test_create_access_token -v -s
```

## Best Practices

1. **Test Naming**: Use descriptive test names
2. **Test Independence**: Each test should be independent
3. **Test Data**: Use fixtures for test data
4. **Assertions**: Use specific assertions
5. **Coverage**: Aim for high coverage but focus on important paths
6. **Performance**: Keep tests fast
7. **Documentation**: Document complex test scenarios

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Python Testing 101](https://realpython.com/python-testing/)