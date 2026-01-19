#!/bin/bash
#
# Babel Tool - Install script
#
# Usage: ./install.sh [--prefix PATH]
#
# Installs babel-tool to an isolated directory with a symlink in PATH.
#
# Default installation:
#   ~/.babel-tool/          - Installation directory
#   ~/.local/bin/babel      - Symlink to executable
#
# GitHub: https://github.com/ktiyab/babel-tool
#

set -e

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

VERSION="0.1.0-alpha.20260119"
DEFAULT_INSTALL_DIR="$HOME/.babel-tool"
DEFAULT_BIN_DIR="$HOME/.local/bin"
INSTALL_DIR=""
BIN_DIR=""
REPO_URL="https://github.com/ktiyab/babel-tool"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where install.sh is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prefix)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --bin-dir)
                BIN_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "Babel Tool Installer"
                echo ""
                echo "Usage: ./install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --prefix PATH    Install to PATH instead of ~/.babel-tool"
                echo "  --bin-dir PATH   Create symlink in PATH instead of ~/.local/bin"
                echo "  --help, -h       Show this help"
                echo ""
                echo "Default installation:"
                echo "  Install directory: ~/.babel-tool/"
                echo "  Symlink location:  ~/.local/bin/babel"
                echo ""
                echo "After installation, run: babel --help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Run './install.sh --help' for usage"
                exit 1
                ;;
        esac
    done

    # Set defaults if not specified
    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    fi
    if [ -z "$BIN_DIR" ]; then
        BIN_DIR="$DEFAULT_BIN_DIR"
    fi
}

# -----------------------------------------------------------------------------
# Dependency checks
# -----------------------------------------------------------------------------

check_python() {
    log_info "Checking Python version..."

    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.9 or higher."
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        log_error "Python 3.9+ required. Found: Python $PYTHON_VERSION"
        exit 1
    fi

    log_success "Python $PYTHON_VERSION found"
}

check_existing_installation() {
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Existing installation found at $INSTALL_DIR"
        read -p "Remove and reinstall? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing installation..."
            rm -rf "$INSTALL_DIR"
        else
            log_info "Installation cancelled"
            exit 0
        fi
    fi
}

# -----------------------------------------------------------------------------
# Installation
# -----------------------------------------------------------------------------

create_venv() {
    log_info "Creating virtual environment..."

    mkdir -p "$INSTALL_DIR"
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"

    log_success "Virtual environment created"
}

install_package() {
    log_info "Installing babel-tool..."

    # Activate venv
    source "$INSTALL_DIR/venv/bin/activate"

    # Upgrade pip
    pip install --upgrade pip -q

    # Install from local source if available, otherwise from the script directory
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        # Installing from source directory
        pip install "$SCRIPT_DIR" -q
        log_success "Installed from source: $SCRIPT_DIR"
    elif [ -f "$SCRIPT_DIR/babel_tool-$VERSION-py3-none-any.whl" ]; then
        # Installing from wheel
        pip install "$SCRIPT_DIR/babel_tool-$VERSION-py3-none-any.whl" -q
        log_success "Installed from wheel"
    else
        log_error "No installable package found in $SCRIPT_DIR"
        log_error "Expected: pyproject.toml or babel_tool-$VERSION-py3-none-any.whl"
        exit 1
    fi

    deactivate
}

create_symlink() {
    log_info "Creating symlink..."

    # Create bin directory if needed
    mkdir -p "$BIN_DIR"

    # Remove existing symlink if present
    if [ -L "$BIN_DIR/babel" ]; then
        rm "$BIN_DIR/babel"
    elif [ -f "$BIN_DIR/babel" ]; then
        log_warn "Non-symlink file exists at $BIN_DIR/babel"
        read -p "Replace it? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$BIN_DIR/babel"
        else
            log_error "Cannot create symlink. Installation incomplete."
            exit 1
        fi
    fi

    # Create symlink
    ln -s "$INSTALL_DIR/venv/bin/babel" "$BIN_DIR/babel"

    log_success "Symlink created: $BIN_DIR/babel"
}

save_version_info() {
    cat > "$INSTALL_DIR/version" << EOF
version=$VERSION
installed=$(date -Iseconds)
install_dir=$INSTALL_DIR
bin_dir=$BIN_DIR
source=$SCRIPT_DIR
EOF
    log_success "Version info saved"
}

check_path() {
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        log_warn "$BIN_DIR is not in your PATH"
        echo ""
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo ""
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
        echo "Then restart your shell or run: source ~/.bashrc"
        echo ""
    fi
}

verify_installation() {
    log_info "Verifying installation..."

    if [ -x "$INSTALL_DIR/venv/bin/babel" ]; then
        INSTALLED_VERSION=$("$INSTALL_DIR/venv/bin/babel" --version 2>/dev/null || echo "unknown")
        log_success "babel executable found: $INSTALLED_VERSION"
    else
        log_error "Installation verification failed"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    parse_args "$@"

    echo ""
    echo "=========================================="
    echo "  Babel Tool Installer v$VERSION"
    echo "=========================================="
    echo ""
    echo "  Repository: $REPO_URL"
    echo "  Install to: $INSTALL_DIR"
    echo "  Symlink:    $BIN_DIR/babel"
    echo ""

    check_python
    check_existing_installation
    create_venv
    install_package
    create_symlink
    save_version_info
    verify_installation

    echo ""
    echo "=========================================="
    echo "  Installation Complete!"
    echo "=========================================="
    echo ""

    check_path

    echo "  Usage:"
    echo "    babel --help          # Show help"
    echo "    babel init \"Project\" # Initialize in a project"
    echo "    babel status          # Check project status"
    echo ""
    echo "  To uninstall:"
    echo "    ./uninstall.sh"
    echo "    # or: $INSTALL_DIR/../babel-tool/uninstall.sh"
    echo ""
}

main "$@"
