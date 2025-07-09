#!/bin/bash

# Check for potential secrets in the codebase
# This script helps prevent accidental commits of sensitive data

set -e

echo "🔍 Checking for potential secrets in codebase..."
echo ""

# Common secret patterns to look for
SECRET_PATTERNS=(
    "api[_-]?key.*=.*['\"][^'\"]{20,}['\"]"
    "secret.*=.*['\"][^'\"]{20,}['\"]"
    "password.*=.*['\"][^'\"]{8,}['\"]"
    "token.*=.*['\"][^'\"]{20,}['\"]"
    "sk_[a-zA-Z0-9]{20,}"
    "pk_[a-zA-Z0-9]{20,}"
    "AIza[0-9A-Za-z-_]{35}"
    "-----BEGIN [A-Z ]+-----"
    "Bearer [A-Za-z0-9_-]{20,}"
)

# Files to exclude from scanning
EXCLUDE_PATTERNS=(
    ".git/"
    "node_modules/"
    ".env.example"
    "check-secrets.sh"
    "*.md"
    "*.log"
    "*.tmp"
)

# Build grep exclude arguments
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-dir=${pattern%/} --exclude=$pattern"
done

# Function to check for secrets
check_secrets() {
    local found_issues=0
    
    for pattern in "${SECRET_PATTERNS[@]}"; do
        echo "🔎 Checking for pattern: ${pattern:0:30}..."
        
        # Use grep to find matches
        if grep -r -i -E --color=never $EXCLUDE_ARGS "$pattern" . 2>/dev/null | grep -v "\.example" | grep -v "PLACEHOLDER" | grep -v "your-.*-here" | head -10; then
            echo "⚠️  Found potential secret with pattern: $pattern"
            found_issues=1
        fi
    done
    
    return $found_issues
}

# Function to check for hardcoded URLs and endpoints
check_hardcoded_urls() {
    echo "🌐 Checking for hardcoded URLs..."
    
    # Look for hardcoded production URLs
    local found_urls=0
    
    if grep -r -i "errortranslator\.com" . --exclude-dir=.git --exclude-dir=node_modules --exclude="*.md" | grep -v "\.example" | head -5; then
        echo "⚠️  Found hardcoded production URLs"
        found_urls=1
    fi
    
    if grep -r -i "ai-error-translator-backend.*\.run\.app" . --exclude-dir=.git --exclude-dir=node_modules --exclude="*.md" | head -5; then
        echo "⚠️  Found hardcoded backend URLs"
        found_urls=1
    fi
    
    return $found_urls
}

# Function to check for debug flags
check_debug_flags() {
    echo "🐛 Checking for debug flags..."
    
    local found_debug=0
    
    if grep -r -i "debug.*=.*true" . --exclude-dir=.git --exclude-dir=node_modules --exclude="*.md" --exclude=".env.example" | head -5; then
        echo "⚠️  Found debug flags set to true"
        found_debug=1
    fi
    
    return $found_debug
}

# Function to check .env files
check_env_files() {
    echo "🔒 Checking for .env files..."
    
    local found_env=0
    
    if find . -name ".env" -not -path "./backend/.env.example" -not -path "./.env.example" 2>/dev/null | head -5; then
        echo "⚠️  Found .env files (should not be committed)"
        found_env=1
    fi
    
    return $found_env
}

# Run all checks
echo "Starting security scan..."
echo "========================="
echo ""

total_issues=0

if check_secrets; then
    ((total_issues++))
fi

echo ""

if check_hardcoded_urls; then
    ((total_issues++))
fi

echo ""

if check_debug_flags; then
    ((total_issues++))
fi

echo ""

if check_env_files; then
    ((total_issues++))
fi

echo ""
echo "========================="

if [ $total_issues -eq 0 ]; then
    echo "✅ No secrets or security issues found!"
    echo "🚀 Safe to commit!"
else
    echo "❌ Found $total_issues potential security issues!"
    echo "🛑 Please review and fix before committing!"
    echo ""
    echo "💡 Tips:"
    echo "- Use environment variables for secrets"
    echo "- Add sensitive files to .gitignore"
    echo "- Use .env.example for templates"
    echo "- Set debug=false in production"
    exit 1
fi