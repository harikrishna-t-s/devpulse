#!/bin/bash

# devpulse-manage: Management script for the devpulse tool
# Handles installation, updates, backups, and rollbacks.

set -e

APP_NAME="devpulse"
INSTALL_DIR="$HOME/.devpulse"
BACKUP_DIR="$INSTALL_DIR/backups"
DB_FILE="$INSTALL_DIR/devpulse.db"
CONFIG_FILE="$INSTALL_DIR/config.yaml"
REPO_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}ℹ $1${NC}"; }
echo_success() { echo -e "${GREEN}✔ $1${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
echo_error() { echo -e "${RED}✘ $1${NC}"; }

show_help() {
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install  - Install the tool locally (editable mode)"
    echo "  update   - Pull latest changes and reinstall"
    echo "  backup   - Backup the database and configuration"
    echo "  rollback - Restore the most recent backup"
    echo "  status   - Show installation status"
    echo "  help     - Show this help message"
}

do_install() {
    echo_info "Installing $APP_NAME..."
    mkdir -p "$INSTALL_DIR/saved"
    mkdir -p "$BACKUP_DIR"
    
    # Check if inside the git repo
    if [ ! -f "pyproject.toml" ]; then
        echo_error "Run this script from the root of the $APP_NAME repository."
        exit 1
    fi

    pip install --user -e .
    
    # Add to PATH if not present
    LOCAL_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        echo_warning "$LOCAL_BIN is not in your PATH. Adding to .bashrc..."
        echo "export PATH=\"\$PATH:$LOCAL_BIN\"" >> "$HOME/.bashrc"
        echo_info "Please run 'source ~/.bashrc' or restart your terminal."
    fi
    
    echo_success "$APP_NAME installed successfully."
}

do_backup() {
    echo_info "Creating backup..."
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    BKP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
    mkdir -p "$BKP_PATH"

    if [ -f "$DB_FILE" ]; then
        cp "$DB_FILE" "$BKP_PATH/"
    fi
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$BKP_PATH/"
    fi

    echo_success "Backup created at $BKP_PATH"
}

do_rollback() {
    LATEST_BKP=$(ls -td "$BACKUP_DIR"/backup_* 2>/dev/null | head -1)
    if [ -z "$LATEST_BKP" ]; then
        echo_error "No backups found."
        exit 1
    fi

    echo_warning "Rolling back to $LATEST_BKP..."
    if [ -f "$LATEST_BKP/devpulse.db" ]; then
        cp "$LATEST_BKP/devpulse.db" "$DB_FILE"
    fi
    if [ -f "$LATEST_BKP/config.yaml" ]; then
        cp "$LATEST_BKP/config.yaml" "$CONFIG_FILE"
    fi
    echo_success "Rollback complete."
}

do_update() {
    echo_info "Updating $APP_NAME..."
    do_backup
    
    if [ -d ".git" ]; then
        git pull
    else
        echo_warning "Not a git repository. Skipping git pull."
    fi
    
    pip install --user -e .
    echo_success "Update complete."
}

do_status() {
    echo_info "Status for $APP_NAME:"
    which devpulse || echo_warning "devpulse command not found in PATH"
    [ -d "$INSTALL_DIR" ] && echo "Data directory: $INSTALL_DIR"
    [ -f "$DB_FILE" ] && echo "Database size: $(du -sh "$DB_FILE" | cut -f1)"
    echo "Backup count: $(ls -d "$BACKUP_DIR"/backup_* 2>/dev/null | wc -l)"
}

case "$1" in
    install) do_install ;;
    update) do_update ;;
    backup) do_backup ;;
    rollback) do_rollback ;;
    status) do_status ;;
    help|*) show_help ;;
esac
