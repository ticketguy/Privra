#!/bin/bash
# Privra Mail - Universal Deployment Script
# Handles initial setup, fixes, updates, and maintenance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_docker() {
    print_info "Checking Docker installation..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Please install Docker first: https://docs.docker.com/engine/install/"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi

    print_success "Docker is available"
}

check_env_file() {
    print_info "Checking environment configuration..."

    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_warning ".env file not found"

        if [ -f "$PROJECT_DIR/.env.example" ]; then
            print_info "Creating .env from .env.example"
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            print_warning "Please edit .env file with your configuration:"
            echo "  - MAIL_DOMAIN"
            echo "  - MAIL_HOSTNAME"
            echo "  - DB_PASSWORD"
            echo "  - SECRET_KEY"
            echo ""
            echo "Run this script again after editing .env"
            exit 0
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi

    # Check if required variables are set
    source "$PROJECT_DIR/.env"

    local missing=0
    [ -z "$MAIL_DOMAIN" ] && print_warning "MAIL_DOMAIN not set in .env" && missing=1
    [ -z "$MAIL_HOSTNAME" ] && print_warning "MAIL_HOSTNAME not set in .env" && missing=1
    [ -z "$DB_PASSWORD" ] && print_warning "DB_PASSWORD not set in .env" && missing=1
    [ -z "$SECRET_KEY" ] && print_warning "SECRET_KEY not set in .env" && missing=1

    if [ $missing -eq 1 ]; then
        print_error "Please configure all required variables in .env"
        exit 1
    fi

    print_success "Environment configuration OK"
}

check_ssl_certs() {
    print_info "Checking SSL certificates..."

    if [ ! -f "$PROJECT_DIR/certs/mail.crt" ] || [ ! -f "$PROJECT_DIR/certs/mail.key" ]; then
        print_warning "SSL certificates not found in certs/ directory"
        print_info "You'll need to add certificates before HTTPS will work"
        print_info "Place your certificates as:"
        echo "  - certs/mail.crt"
        echo "  - certs/mail.key"
        return 1
    fi

    # Check if certificate needs expansion (intermediate certs)
    if grep -q "CERTIFICATE" "$PROJECT_DIR/certs/mail.crt"; then
        local cert_count=$(grep -c "BEGIN CERTIFICATE" "$PROJECT_DIR/certs/mail.crt")
        if [ "$cert_count" -eq 1 ]; then
            print_warning "Certificate may need intermediate chain"
            print_info "If you have certificate chain issues, the script will fix it"
        fi
    fi

    print_success "SSL certificates found"
    return 0
}

fix_ssl_cert() {
    print_info "Fixing SSL certificate chain..."

    if [ ! -f "$PROJECT_DIR/certs/mail.crt" ]; then
        print_warning "No certificate to fix"
        return
    fi

    # Check if cert is already expanded
    local cert_count=$(grep -c "BEGIN CERTIFICATE" "$PROJECT_DIR/certs/mail.crt" 2>/dev/null || echo "0")

    if [ "$cert_count" -gt 1 ]; then
        print_success "Certificate already has full chain"
        return
    fi

    # Look for intermediate cert
    if [ -f "$PROJECT_DIR/certs/intermediate.crt" ] || [ -f "$PROJECT_DIR/certs/ca-bundle.crt" ] || [ -f "$PROJECT_DIR/certs/chain.crt" ]; then
        print_info "Found intermediate certificate, combining..."

        local intermediate=""
        [ -f "$PROJECT_DIR/certs/intermediate.crt" ] && intermediate="$PROJECT_DIR/certs/intermediate.crt"
        [ -f "$PROJECT_DIR/certs/ca-bundle.crt" ] && intermediate="$PROJECT_DIR/certs/ca-bundle.crt"
        [ -f "$PROJECT_DIR/certs/chain.crt" ] && intermediate="$PROJECT_DIR/certs/chain.crt"

        if [ -n "$intermediate" ]; then
            cp "$PROJECT_DIR/certs/mail.crt" "$PROJECT_DIR/certs/mail.crt.backup"
            cat "$PROJECT_DIR/certs/mail.crt.backup" "$intermediate" > "$PROJECT_DIR/certs/mail.crt"
            print_success "Certificate chain expanded"
        fi
    fi
}

initialize_database() {
    print_info "Initializing database..."

    # Start database first
    docker compose up -d db

    # Wait for database to be ready
    print_info "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker compose exec -T db pg_isready -U "${DB_USER:-privramail}" &> /dev/null; then
            print_success "Database is ready"
            return 0
        fi
        sleep 1
    done

    print_error "Database failed to start"
    docker compose logs db
    return 1
}

rebuild_webmail() {
    print_info "Rebuilding webmail container..."

    docker compose stop webmail 2>/dev/null || true
    docker compose rm -f webmail 2>/dev/null || true
    docker compose build --no-cache webmail
    docker compose up -d webmail

    # Wait for webmail to start
    sleep 5

    if docker compose ps webmail | grep -q "Up"; then
        # Check for errors in logs
        if docker compose logs --tail=20 webmail | grep -i "error\|exception\|traceback" | grep -v "INFO\|DEBUG" > /dev/null 2>&1; then
            print_warning "Webmail started but has errors, checking logs..."
            docker compose logs --tail=30 webmail
            return 1
        else
            print_success "Webmail rebuilt and running"
            return 0
        fi
    else
        print_error "Webmail failed to start"
        docker compose logs --tail=30 webmail
        return 1
    fi
}

check_dkim() {
    print_info "Checking DKIM configuration..."

    # Check if DKIM keys exist
    if docker compose exec -T postfix test -f /etc/opendkim/keys/default.private &> /dev/null; then
        print_success "DKIM keys found"

        # Get DKIM public key
        print_info "DKIM DNS Record (add this to your DNS):"
        echo ""
        docker compose exec -T postfix cat /etc/opendkim/keys/default.txt 2>/dev/null || \
            print_warning "Could not read DKIM public key"
        echo ""
    else
        print_warning "DKIM keys not found - they will be generated on first start"
    fi
}

start_services() {
    print_info "Starting all services..."

    cd "$PROJECT_DIR"
    docker compose up -d

    print_info "Waiting for services to start..."
    sleep 5

    # Check service status
    local failed=0

    for service in db redis postfix dovecot webmail admin nginx; do
        if docker compose ps $service | grep -q "Up"; then
            print_success "$service is running"
        else
            print_error "$service failed to start"
            failed=1
        fi
    done

    return $failed
}

show_status() {
    print_header "System Status"

    docker compose ps

    echo ""
    print_info "Access Points:"
    source "$PROJECT_DIR/.env"
    echo "  Webmail:     https://${MAIL_HOSTNAME}/"
    echo "  Admin Panel: https://${MAIL_HOSTNAME}/warofbest"
    echo "  SMTP:        ${MAIL_HOSTNAME}:587 (STARTTLS)"
    echo "  IMAP:        ${MAIL_HOSTNAME}:993 (SSL)"
    echo ""
}

show_logs() {
    local service=${1:-}

    if [ -z "$service" ]; then
        print_info "Showing logs for all services..."
        docker compose logs --tail=50
    else
        print_info "Showing logs for $service..."
        docker compose logs --tail=100 -f $service
    fi
}

show_help() {
    cat <<EOF
Privra Mail - Universal Deployment Script

Usage: $0 [command]

Commands:
    deploy       Deploy the mail server (default)
    fix          Fix common issues (rebuild webmail, check DKIM, etc.)
    rebuild      Rebuild and restart all containers
    status       Show service status
    logs         Show logs for all services
    logs <svc>   Show logs for specific service
    stop         Stop all services
    start        Start all services
    restart      Restart all services
    help         Show this help message

Examples:
    $0              # Initial deployment
    $0 deploy       # Same as above
    $0 fix          # Fix issues (webmail, DKIM, SSL)
    $0 rebuild      # Rebuild everything
    $0 status       # Check status
    $0 logs webmail # View webmail logs

EOF
}

# Main deployment function
deploy() {
    print_header "Privra Mail - Deployment"

    cd "$PROJECT_DIR"

    check_docker
    check_env_file
    check_ssl_certs || true

    # Fix SSL if needed
    fix_ssl_cert

    # Initialize database
    initialize_database || exit 1

    # Start all services
    start_services || {
        print_error "Some services failed to start"
        show_status
        exit 1
    }

    # Check DKIM
    check_dkim

    print_header "Deployment Complete!"

    show_status

    print_info "Next Steps:"
    echo "  1. Add DKIM DNS record shown above"
    echo "  2. Access webmail at https://${MAIL_HOSTNAME}/"
    echo "  3. Create users via admin panel"
    echo ""
    print_info "View logs: $0 logs"
    print_info "Check status: $0 status"
}

# Fix function for troubleshooting
fix_issues() {
    print_header "Privra Mail - Fix Issues"

    cd "$PROJECT_DIR"

    check_docker

    # Fix SSL certificate
    fix_ssl_cert

    # Rebuild webmail (common issue)
    print_info "Rebuilding webmail to fix import errors..."
    rebuild_webmail || print_warning "Webmail rebuild had issues"

    # Check DKIM
    check_dkim

    # Restart all services
    print_info "Restarting all services..."
    docker compose restart

    sleep 5

    print_header "Fix Complete"
    show_status
}

# Rebuild all containers
rebuild_all() {
    print_header "Rebuilding All Containers"

    cd "$PROJECT_DIR"

    check_docker

    print_info "Stopping services..."
    docker compose down

    print_info "Rebuilding all containers (this may take a few minutes)..."
    docker compose build --no-cache

    print_info "Starting services..."
    docker compose up -d

    sleep 10

    print_header "Rebuild Complete"
    show_status
}

# Parse command
COMMAND=${1:-deploy}

case "$COMMAND" in
    deploy)
        deploy
        ;;
    fix)
        fix_issues
        ;;
    rebuild)
        rebuild_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    stop)
        docker compose down
        print_success "All services stopped"
        ;;
    start)
        docker compose up -d
        sleep 5
        show_status
        ;;
    restart)
        docker compose restart
        sleep 5
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
