#!/bin/bash

# Auction System Test Suite
# =========================
# Unified test runner for end-to-end and UI testing

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:5000"
TESTS_DIR="tests"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Flask app is running
    if curl -s "$BASE_URL" > /dev/null 2>&1; then
        log_success "Flask app is running on $BASE_URL"
    else
        log_error "Flask app not running on $BASE_URL"
        log_info "Please start the Flask app first: python app.py"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found"
        exit 1
    fi
    
    # Check if tests directory exists
    if [ ! -d "$TESTS_DIR" ]; then
        log_error "Tests directory not found: $TESTS_DIR"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Install dependencies
install_dependencies() {
    log_info "Installing test dependencies..."
    
    # Install basic requirements
    pip3 install requests beautifulsoup4 > /dev/null 2>&1 || {
        log_warning "Failed to install basic dependencies"
    }
    
    # Check for optional dependencies
    if [ "$1" = "ui" ] || [ "$1" = "all" ]; then
        log_info "Installing UI testing dependencies..."
        
        # Install Selenium
        pip3 install selenium webdriver-manager > /dev/null 2>&1 && {
            log_success "Selenium installed"
        } || {
            log_warning "Failed to install Selenium"
        }
        
        # Install Playwright
        pip3 install playwright > /dev/null 2>&1 && {
            playwright install chromium > /dev/null 2>&1 && {
                log_success "Playwright installed"
            } || {
                log_warning "Failed to install Playwright browsers"
            }
        } || {
            log_warning "Failed to install Playwright"
        }
        
        # Install PyTest
        pip3 install pytest pytest-html > /dev/null 2>&1 && {
            log_success "PyTest installed"
        } || {
            log_warning "Failed to install PyTest"
        }
    fi
}

# Run E2E tests
run_e2e_tests() {
    log_info "Running End-to-End Tests..."
    echo "================================"
    
    local passed=0
    local total=0
    
    # Simple E2E test
    if [ -f "$TESTS_DIR/test_e2e_simple.py" ]; then
        log_info "Running Simple E2E Test..."
        total=$((total + 1))
        if python3 "$TESTS_DIR/test_e2e_simple.py"; then
            log_success "Simple E2E Test passed"
            passed=$((passed + 1))
        else
            log_error "Simple E2E Test failed"
        fi
        echo ""
    fi
    
    # Advanced E2E test
    if [ -f "$TESTS_DIR/test_e2e_advanced.py" ]; then
        log_info "Running Advanced E2E Test..."
        total=$((total + 1))
        if python3 "$TESTS_DIR/test_e2e_advanced.py"; then
            log_success "Advanced E2E Test passed"
            passed=$((passed + 1))
        else
            log_error "Advanced E2E Test failed"
        fi
        echo ""
    fi
    
    log_info "E2E Tests Summary: $passed/$total passed"
    return $((total - passed))
}

# Run UI tests
run_ui_tests() {
    log_info "Running UI Tests..."
    echo "==================="
    
    local passed=0
    local total=0
    local ui_framework="${1:-selenium}"
    
    case $ui_framework in
        "selenium")
            if [ -f "$TESTS_DIR/test_ui_selenium.py" ]; then
                log_info "Running Selenium UI Tests..."
                total=$((total + 1))
                if python3 "$TESTS_DIR/test_ui_selenium.py"; then
                    log_success "Selenium UI Tests passed"
                    passed=$((passed + 1))
                else
                    log_error "Selenium UI Tests failed"
                fi
                echo ""
            fi
            ;;
        "playwright")
            if [ -f "$TESTS_DIR/test_ui_playwright.py" ]; then
                log_info "Running Playwright UI Tests..."
                total=$((total + 1))
                if python3 "$TESTS_DIR/test_ui_playwright.py"; then
                    log_success "Playwright UI Tests passed"
                    passed=$((passed + 1))
                else
                    log_error "Playwright UI Tests failed"
                fi
                echo ""
            fi
            ;;
        "pytest")
            if [ -f "$TESTS_DIR/test_ui_pytest.py" ]; then
                log_info "Running PyTest UI Tests..."
                total=$((total + 1))
                if cd "$TESTS_DIR" && python3 -m pytest test_ui_pytest.py -v --tb=short; then
                    log_success "PyTest UI Tests passed"
                    passed=$((passed + 1))
                else
                    log_error "PyTest UI Tests failed"
                fi
                cd ..
                echo ""
            fi
            ;;
        "all")
            # Run all UI frameworks
            for framework in selenium playwright pytest; do
                run_ui_tests "$framework"
                local result=$?
                total=$((total + 1))
                if [ $result -eq 0 ]; then
                    passed=$((passed + 1))
                fi
            done
            ;;
    esac
    
    log_info "UI Tests Summary: $passed/$total passed"
    return $((total - passed))
}

# Generate test report
generate_report() {
    local e2e_result=$1
    local ui_result=$2
    
    echo ""
    echo "🏁 Test Execution Complete"
    echo "=========================="
    
    if [ $e2e_result -eq 0 ]; then
        log_success "E2E Tests: PASSED"
    else
        log_error "E2E Tests: FAILED ($e2e_result failures)"
    fi
    
    if [ $ui_result -eq 0 ]; then
        log_success "UI Tests: PASSED"
    else
        log_error "UI Tests: FAILED ($ui_result failures)"
    fi
    
    local total_failures=$((e2e_result + ui_result))
    
    if [ $total_failures -eq 0 ]; then
        echo ""
        log_success "🎉 ALL TESTS PASSED!"
        echo ""
        return 0
    else
        echo ""
        log_error "❌ $total_failures test(s) failed"
        echo ""
        return 1
    fi
}

# Show help
show_help() {
    echo "Auction System Test Suite"
    echo "========================="
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  e2e                     Run end-to-end tests only"
    echo "  ui [framework]          Run UI tests (selenium|playwright|pytest|all)"
    echo "  all                     Run all tests (default)"
    echo "  install [type]          Install dependencies (e2e|ui|all)"
    echo "  clean                   Clean up test artifacts"
    echo "  help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all tests"
    echo "  $0 e2e                  # Run only E2E tests"
    echo "  $0 ui selenium          # Run only Selenium UI tests"
    echo "  $0 ui all               # Run all UI test frameworks"
    echo "  $0 install ui           # Install UI testing dependencies"
    echo ""
    echo "Environment Variables:"
    echo "  HEADLESS=true           Run UI tests in headless mode"
    echo "  TEST_BROWSER=firefox    Use specific browser (chrome|firefox)"
    echo ""
}

# Clean up artifacts
clean_artifacts() {
    log_info "Cleaning up test artifacts..."
    
    # Remove temporary files
    rm -f /tmp/*test*.json /tmp/*test*.png /tmp/*test*.html
    
    # Remove test reports
    rm -f tests/report.html tests/.pytest_cache -rf
    
    log_success "Cleanup completed"
}

# Main function
main() {
    echo "🧪 Auction System Test Suite"
    echo "============================"
    echo ""
    
    case "${1:-all}" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "clean")
            clean_artifacts
            exit 0
            ;;
        "install")
            install_dependencies "${2:-all}"
            exit 0
            ;;
        "e2e")
            check_prerequisites
            run_e2e_tests
            exit $?
            ;;
        "ui")
            check_prerequisites
            install_dependencies "ui"
            run_ui_tests "${2:-selenium}"
            exit $?
            ;;
        "all")
            check_prerequisites
            install_dependencies "all"
            
            log_info "Running complete test suite..."
            echo ""
            
            # Run E2E tests
            run_e2e_tests
            e2e_result=$?
            
            # Run UI tests
            run_ui_tests "${2:-selenium}"
            ui_result=$?
            
            # Generate report
            generate_report $e2e_result $ui_result
            exit $?
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"