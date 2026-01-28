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

DEFAULT_INSTALL_DIR="$HOME/.babel-tool"
DEFAULT_BIN_DIR="$HOME/.local/bin"
INSTALL_DIR=""
BIN_DIR=""
FORCE_INSTALL="false"
MODIFY_PATH="true"
REPO_URL="https://github.com/ktiyab/babel-tool"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where install.sh is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Platform detection
detect_platform() {
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*|Windows_NT)
            echo "windows"
            ;;
        Darwin*)
            echo "macos"
            ;;
        *)
            echo "linux"
            ;;
    esac
}

PLATFORM=$(detect_platform)

# Platform-specific venv paths
get_venv_bin_dir() {
    if [ "$PLATFORM" = "windows" ]; then
        echo "$INSTALL_DIR/venv/Scripts"
    else
        echo "$INSTALL_DIR/venv/bin"
    fi
}

get_venv_activate() {
    if [ "$PLATFORM" = "windows" ]; then
        echo "$INSTALL_DIR/venv/Scripts/activate"
    else
        echo "$INSTALL_DIR/venv/bin/activate"
    fi
}

get_babel_executable() {
    if [ "$PLATFORM" = "windows" ]; then
        echo "$INSTALL_DIR/venv/Scripts/babel"
    else
        echo "$INSTALL_DIR/venv/bin/babel"
    fi
}

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

get_source_version() {
    # Extract version from babel/__init__.py (single source of truth)
    # Uses portable grep (no -P flag, not available on all platforms)
    local init_file="$SCRIPT_DIR/babel/__init__.py"
    if [ -f "$init_file" ]; then
        grep '__version__' "$init_file" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' || echo "unknown"
    else
        echo "unknown"
    fi
}

get_installed_version() {
    # Get version from installed babel command (platform-aware)
    local babel_exe
    babel_exe=$(get_babel_executable)
    "$babel_exe" --version 2>/dev/null | awk '{print $2}' || echo "unknown"
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
            --force|-f)
                FORCE_INSTALL="true"
                shift
                ;;
            --no-modify-path)
                MODIFY_PATH="false"
                shift
                ;;
            --help|-h)
                echo "Babel Tool Installer"
                echo ""
                echo "Usage: ./install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --prefix PATH      Install to PATH instead of ~/.babel-tool"
                echo "  --bin-dir PATH     Create symlink in PATH instead of ~/.local/bin"
                echo "  --force, -f        Non-interactive mode (auto-yes to prompts)"
                echo "  --no-modify-path   Don't modify shell profile (manual PATH setup)"
                echo "  --help, -h         Show this help"
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
        log_error "Python not found. Please install Python 3.10 or higher."
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        log_error "Python 3.10+ required. Found: Python $PYTHON_VERSION"
        exit 1
    fi

    log_success "Python $PYTHON_VERSION found"
}

check_existing_installation() {
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Existing installation found at $INSTALL_DIR"
        if [ "$FORCE_INSTALL" = "true" ]; then
            log_info "Removing existing installation (--force)..."
            rm -rf "$INSTALL_DIR"
        else
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

    # Activate venv (platform-aware)
    local activate_script
    activate_script=$(get_venv_activate)
    source "$activate_script"

    # Upgrade pip
    pip install --upgrade pip -q

    # Get version for wheel lookup
    local version
    version=$(get_source_version)

    # Install from local source if available, otherwise from the script directory
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        # Installing from source directory
        pip install "$SCRIPT_DIR" -q
        log_success "Installed from source: $SCRIPT_DIR"
    elif [ -f "$SCRIPT_DIR/babel_tool-$version-py3-none-any.whl" ]; then
        # Installing from wheel
        pip install "$SCRIPT_DIR/babel_tool-$version-py3-none-any.whl" -q
        log_success "Installed from wheel"
    else
        log_error "No installable package found in $SCRIPT_DIR"
        log_error "Expected: pyproject.toml or babel_tool-*.whl"
        exit 1
    fi

    deactivate
}

create_symlink() {
    log_info "Creating symlink..."

    # Create bin directory if needed
    mkdir -p "$BIN_DIR"

    # Get platform-aware babel executable path
    local babel_exe
    babel_exe=$(get_babel_executable)

    # Remove existing symlink if present
    if [ -L "$BIN_DIR/babel" ]; then
        rm "$BIN_DIR/babel"
    elif [ -f "$BIN_DIR/babel" ]; then
        log_warn "Non-symlink file exists at $BIN_DIR/babel"
        if [ "$FORCE_INSTALL" = "true" ]; then
            rm "$BIN_DIR/babel"
        else
            read -p "Replace it? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm "$BIN_DIR/babel"
            else
                log_error "Cannot create symlink. Installation incomplete."
                exit 1
            fi
        fi
    fi

    # Create symlink (or copy on Windows if symlinks not supported)
    if [ "$PLATFORM" = "windows" ]; then
        # On Windows, symlinks may require elevated privileges
        # Try symlink first, fall back to wrapper script
        if ln -s "$babel_exe" "$BIN_DIR/babel" 2>/dev/null; then
            log_success "Symlink created: $BIN_DIR/babel"
        else
            # Create a wrapper script instead
            cat > "$BIN_DIR/babel" << EOF
#!/bin/bash
"$babel_exe" "\$@"
EOF
            chmod +x "$BIN_DIR/babel"
            log_success "Wrapper script created: $BIN_DIR/babel"
        fi
    else
        ln -s "$babel_exe" "$BIN_DIR/babel"
        log_success "Symlink created: $BIN_DIR/babel"
    fi
}

save_version_info() {
    local installed_version
    installed_version=$(get_installed_version)
    # Use portable date format (date -Iseconds not available on macOS)
    local install_date
    install_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat > "$INSTALL_DIR/version" << EOF
version=$installed_version
installed=$install_date
install_dir=$INSTALL_DIR
bin_dir=$BIN_DIR
platform=$PLATFORM
source=$SCRIPT_DIR
EOF
    log_success "Version info saved"
}

create_config_dir() {
    # Create ~/.babel/ directory for user configuration
    local config_dir="$HOME/.babel"
    if [ ! -d "$config_dir" ]; then
        mkdir -p "$config_dir"
        log_success "Config directory created: $config_dir"
    fi
}

setup_env_config() {
    # Copy .env.example to ~/.babel/.env if it doesn't exist
    local config_dir="$HOME/.babel"
    local env_file="$config_dir/.env"
    local env_example="$SCRIPT_DIR/.env.example"

    # Also copy to install dir for reference
    if [ -f "$env_example" ]; then
        cp "$env_example" "$INSTALL_DIR/.env.example"
        log_success "Configuration reference: $INSTALL_DIR/.env.example"
    fi

    # Create user config if doesn't exist
    if [ -f "$env_file" ]; then
        log_info "Existing .env found at $env_file (preserved)"
        return 0
    fi

    if [ -f "$env_example" ]; then
        cp "$env_example" "$env_file"
        log_success "Configuration created: $env_file"
        log_info "Edit $env_file to add your API key"
    else
        log_warn ".env.example not found in source directory"
    fi
}

get_shell_profile() {
    # Detect the appropriate shell profile file for PATH configuration
    # Returns the best profile file for the current platform and shell

    local shell_name
    shell_name=$(basename "${SHELL:-/bin/bash}")

    case "$PLATFORM" in
        windows)
            # Git Bash on Windows
            if [ -f "$HOME/.bash_profile" ]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        macos)
            # macOS uses zsh by default since Catalina
            case "$shell_name" in
                zsh)
                    echo "$HOME/.zshrc"
                    ;;
                bash)
                    # macOS bash uses .bash_profile for login shells
                    if [ -f "$HOME/.bash_profile" ]; then
                        echo "$HOME/.bash_profile"
                    else
                        echo "$HOME/.profile"
                    fi
                    ;;
                fish)
                    echo "$HOME/.config/fish/config.fish"
                    ;;
                *)
                    echo "$HOME/.profile"
                    ;;
            esac
            ;;
        linux)
            case "$shell_name" in
                zsh)
                    echo "$HOME/.zshrc"
                    ;;
                bash)
                    # Linux bash typically uses .bashrc for interactive shells
                    echo "$HOME/.bashrc"
                    ;;
                fish)
                    echo "$HOME/.config/fish/config.fish"
                    ;;
                *)
                    echo "$HOME/.profile"
                    ;;
            esac
            ;;
        *)
            echo "$HOME/.profile"
            ;;
    esac
}

configure_path() {
    # Configure PATH in shell profile

    # Check if already in PATH
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        log_success "PATH already configured"
        return 0
    fi

    local profile_file
    profile_file=$(get_shell_profile)

    # PATH export line to add
    local path_line="export PATH=\"$BIN_DIR:\$PATH\""
    local marker="# Added by babel-tool installer"

    if [ "$MODIFY_PATH" = "true" ]; then
        # Check if we already added the line (idempotent)
        if [ -f "$profile_file" ] && grep -q "babel-tool installer" "$profile_file" 2>/dev/null; then
            log_info "PATH already configured in $profile_file"
            return 0
        fi

        # Create profile file if it doesn't exist
        if [ ! -f "$profile_file" ]; then
            # For fish, ensure directory exists
            if [[ "$profile_file" == *"fish"* ]]; then
                mkdir -p "$(dirname "$profile_file")"
            fi
            touch "$profile_file"
        fi

        # Add PATH configuration
        {
            echo ""
            echo "$marker"
            echo "$path_line"
        } >> "$profile_file"

        log_success "PATH configured in $profile_file"
        echo ""
        echo "  To use babel now, either:"
        echo "    1. Restart your terminal, or"
        echo "    2. Run: source $profile_file"
        echo ""
    else
        # Manual mode - just warn
        log_warn "$BIN_DIR is not in your PATH"
        echo ""
        echo "  Add this to your shell profile ($profile_file):"
        echo ""
        echo "    $path_line"
        echo ""
        echo "  Then restart your shell or run: source $profile_file"
        echo ""
    fi
}

verify_installation() {
    log_info "Verifying installation..."

    local babel_exe
    babel_exe=$(get_babel_executable)

    if [ -x "$babel_exe" ]; then
        INSTALLED_VERSION=$("$babel_exe" --version 2>/dev/null || echo "unknown")
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

    local source_version
    source_version=$(get_source_version)

    echo ""
    echo "=========================================="
    echo "  Babel Tool Installer v$source_version"
    echo "=========================================="
    echo ""
    echo "  Repository: $REPO_URL"
    echo "  Platform:   $PLATFORM"
    echo ""
    echo "  Directories:"
    echo "    Tool:     $INSTALL_DIR"
    echo "    Config:   $HOME/.babel"
    echo "    Command:  $BIN_DIR/babel"
    echo ""

    check_python
    check_existing_installation
    create_venv
    install_package
    create_symlink
    save_version_info
    create_config_dir
    setup_env_config
    verify_installation

    echo ""
    echo "=========================================="
    echo "  Installation Complete!"
    echo "=========================================="
    echo ""

    configure_path

    echo "  Usage:"
    echo "    babel --help          # Show help"
    echo "    babel init \"Project\" # Initialize in a project"
    echo "    babel status          # Check project status"
    echo ""
    echo "  Configuration:"
    echo "    Edit ~/.babel/.env to add your API key:"
    echo "    nano ~/.babel/.env    # or your preferred editor"
    echo ""
    echo "  To uninstall:"
    echo "    $SCRIPT_DIR/uninstall.sh"
    echo "    # or manually: rm -rf $INSTALL_DIR && rm $BIN_DIR/babel"
    echo ""
}

main "$@"
