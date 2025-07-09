#!/bin/bash

# Test runner script for AI Error Translator backend
# This script runs different types of tests with proper setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if pytest is available
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_error "pytest not found. Please install requirements:"
        echo "pip install -r requirements.txt"
        exit 1
    fi
}

# Function to run specific test type
run_test_type() {
    local test_type=$1
    local test_path=$2
    
    print_status "Running $test_type tests..."
    
    if [ -d "$test_path" ]; then
        pytest "$test_path" -m "$test_type" -v
        if [ $? -eq 0 ]; then
            print_success "$test_type tests passed!"
        else
            print_error "$test_type tests failed!"
            return 1
        fi
    else
        print_warning "No $test_type tests found in $test_path"
    fi
}

# Function to run all tests
run_all_tests() {
    print_status "Running all tests..."
    
    pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
    
    if [ $? -eq 0 ]; then
        print_success "All tests passed!"
        print_status "Coverage report generated in htmlcov/"
    else
        print_error "Some tests failed!"
        return 1
    fi
}

# Function to run quick tests (unit tests only)
run_quick_tests() {
    print_status "Running quick tests (unit tests only)..."
    
    pytest tests/unit/ -v
    
    if [ $? -eq 0 ]; then
        print_success "Quick tests passed!"
    else
        print_error "Quick tests failed!"
        return 1
    fi
}

# Function to run security tests
run_security_tests() {
    print_status "Running security tests..."
    
    # Run auth-related tests
    pytest tests/ -k "auth" -v
    
    if [ $? -eq 0 ]; then
        print_success "Security tests passed!"
    else
        print_error "Security tests failed!"
        return 1
    fi
    
    # Run the secrets check
    if [ -f "../check-secrets.sh" ]; then
        print_status "Running secrets check..."
        cd ..
        ./check-secrets.sh
        cd backend
    fi
}

# Function to generate test report
generate_report() {
    print_status "Generating test report..."
    
    pytest tests/ --html=test_report.html --self-contained-html --cov=app --cov-report=html
    
    if [ $? -eq 0 ]; then
        print_success "Test report generated: test_report.html"
        print_success "Coverage report generated: htmlcov/index.html"
    else
        print_error "Failed to generate test report!"
        return 1
    fi
}

# Function to clean test artifacts
clean_artifacts() {
    print_status "Cleaning test artifacts..."
    
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    rm -f test_report.html
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_success "Test artifacts cleaned!"
}

# Function to show help
show_help() {
    echo "AI Error Translator Backend Test Runner"
    echo "======================================="
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all          Run all tests with coverage"
    echo "  unit         Run unit tests only"
    echo "  integration  Run integration tests only"
    echo "  e2e          Run end-to-end tests only"
    echo "  quick        Run quick tests (unit tests)"
    echo "  security     Run security-related tests"
    echo "  report       Generate detailed test report"
    echo "  clean        Clean test artifacts"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all          # Run all tests"
    echo "  $0 unit         # Run only unit tests"
    echo "  $0 security     # Run security tests"
    echo "  $0 report       # Generate test report"
}

# Main execution
main() {
    local command=${1:-all}
    
    echo "🧪 AI Error Translator Backend Test Runner"
    echo "=========================================="
    echo ""
    
    # Check prerequisites
    check_pytest
    
    case $command in
        all)
            run_all_tests
            ;;
        unit)
            run_test_type "unit" "tests/unit"
            ;;
        integration)
            run_test_type "integration" "tests/integration"
            ;;
        e2e)
            run_test_type "e2e" "tests/e2e"
            ;;
        quick)
            run_quick_tests
            ;;
        security)
            run_security_tests
            ;;
        report)
            generate_report
            ;;
        clean)
            clean_artifacts
            ;;
        help)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"