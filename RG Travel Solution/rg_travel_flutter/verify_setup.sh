#!/usr/bin/env bash

# RG Travel Solution - Flutter Verification Script
# Verifies Flutter app structure and dependencies
# Usage: bash verify_flutter_setup.sh

set -e  # Exit on error

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check Flutter installation
check_flutter() {
    print_header "Checking Flutter Installation"
    
    if command -v flutter &> /dev/null; then
        flutter_version=$(flutter --version | head -n1)
        print_success "$flutter_version"
        return 0
    else
        print_error "Flutter not found. Install Flutter from https://flutter.dev"
        return 1
    fi
}

# Check Dart installation
check_dart() {
    print_header "Checking Dart Installation"
    
    if command -v dart &> /dev/null; then
        dart_version=$(dart --version)
        print_success "$dart_version"
        return 0
    else
        print_error "Dart not found"
        return 1
    fi
}

# Check pubspec.yaml
check_pubspec() {
    print_header "Checking pubspec.yaml"
    
    if [ -f "pubspec.yaml" ]; then
        print_success "pubspec.yaml found"
        
        # Check key dependencies
        if grep -q "http:" pubspec.yaml; then
            print_success "http package configured"
        else
            print_warning "http package not found"
        fi
        
        if grep -q "provider:" pubspec.yaml; then
            print_success "provider package configured"
        else
            print_warning "provider package not found"
        fi
        
        if grep -q "flutter_map:" pubspec.yaml; then
            print_success "flutter_map configured"
        else
            print_warning "flutter_map not configured"
        fi
        
        return 0
    else
        print_error "pubspec.yaml not found"
        return 1
    fi
}

# Check directory structure
check_structure() {
    print_header "Checking Project Structure"
    
    dirs=("lib" "test" "android" "ios" "web" "assets")
    all_ok=0
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            print_success "Directory exists: $dir/"
        else
            print_warning "Directory not found: $dir/"
            all_ok=1
        fi
    done
    
    return $all_ok
}

# Check lib structure
check_lib_structure() {
    print_header "Checking lib/ Structure"
    
    if [ ! -d "lib" ]; then
        print_error "lib directory not found"
        return 1
    fi
    
    lib_dirs=("core" "models" "services" "screens" "widgets" "state")
    
    for dir in "${lib_dirs[@]}"; do
        if [ -d "lib/$dir" ]; then
            print_success "lib/$dir/ exists"
        else
            print_warning "lib/$dir/ not found"
        fi
    done
    
    return 0
}

# Check main entry points
check_entry_points() {
    print_header "Checking Entry Points"
    
    files=("lib/main.dart" "lib/app.dart")
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$file exists"
        else
            print_error "$file NOT found"
            return 1
        fi
    done
    
    return 0
}

# Check models
check_models() {
    print_header "Checking Models"
    
    models=("admin_model.dart" "driver_model.dart" "employee_model.dart" "trip_model.dart")
    
    for model in "${models[@]}"; do
        if [ -f "lib/models/$model" ]; then
            print_success "models/$model"
        else
            print_warning "models/$model not found"
        fi
    done
}

# Check services
check_services() {
    print_header "Checking Services"
    
    services=("auth_service.dart" "admin_service.dart" "driver_service.dart" "employee_service.dart")
    
    for service in "${services[@]}"; do
        if [ -f "lib/services/$service" ]; then
            print_success "services/$service"
        else
            print_warning "services/$service not found"
        fi
    done
}

# Check pub get
check_pub_get() {
    print_header "Checking Dependencies"
    
    if [ -d ".dart_tool" ]; then
        print_success "Dependencies cached (.dart_tool exists)"
        return 0
    else
        print_warning ".dart_tool not found - run 'flutter pub get'"
        return 1
    fi
}

# Run flutter doctor
run_flutter_doctor() {
    print_header "Running Flutter Doctor"
    print_info "This checks your Flutter setup..."
    
    if flutter doctor; then
        print_success "Flutter doctor completed"
        return 0
    else
        print_error "Flutter doctor found issues"
        return 1
    fi
}

# Print summary
print_summary() {
    local passed=$1
    local total=$2
    
    print_header "Verification Summary"
    
    echo ""
    echo "Total checks: $total"
    print_success "$passed checks passed"
    
    if [ $passed -eq $total ]; then
        echo -e "\n${GREEN}${BOLD}✓ All checks passed! Flutter app is ready.${NC}"
        echo -e "${BLUE}Next steps:${NC}"
        echo -e "  1. Run 'flutter pub get' to install dependencies"
        echo -e "  2. Run 'flutter run' to start development server"
        echo -e "  3. Connect a device or start an emulator first\n"
        return 0
    else
        echo -e "\n${RED}${BOLD}✗ Some checks failed.${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    local passed=0
    local total=0
    
    echo -e "${BOLD}${BLUE}RG Travel Solution - Flutter Verification${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
    
    # Run checks
    check_flutter && ((passed++)) || true
    ((total++))
    
    check_dart && ((passed++)) || true
    ((total++))
    
    check_pubspec && ((passed++)) || true
    ((total++))
    
    check_structure && ((passed++)) || true
    ((total++))
    
    check_lib_structure && ((passed++)) || true
    ((total++))
    
    check_entry_points && ((passed++)) || true
    ((total++))
    
    check_models && ((passed++)) || true
    ((total++))
    
    check_services && ((passed++)) || true
    ((total++))
    
    check_pub_get && ((passed++)) || true
    ((total++))
    
    # Print summary
    print_summary $passed $total
    
    return $([ $passed -eq $total ] && echo 0 || echo 1)
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
    exit $?
fi
