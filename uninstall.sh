#!/bin/bash
#
# Babel Tool - Uninstall script
#
# Usage: ./uninstall.sh [--yes]
#
# Removes babel-tool installation.
#
# Default locations removed:
#   ~/.babel-tool/          - Installation directory
#   ~/.local/bin/babel      - Symlink
#
# NOTE: This does NOT remove your project's .babel/ directories.
#       Those contain your project data and are separate from the tool.
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
SKIP_CONFIRM=false
PLATFORM=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
            --yes|-y)
                SKIP_CONFIRM=true
                shift
                ;;
            --prefix)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --bin-dir)
                BIN_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "Babel Tool Uninstaller"
                echo ""
                echo "Usage: ./uninstall.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --yes, -y        Skip confirmation prompt"
                echo "  --prefix PATH    Uninstall from PATH instead of ~/.babel-tool"
                echo "  --bin-dir PATH   Remove symlink from PATH instead of ~/.local/bin"
                echo "  --help, -h       Show this help"
                echo ""
                echo "This removes:"
                echo "  - Installation directory (~/.babel-tool/)"
                echo "  - Symlink (~/.local/bin/babel)"
                echo ""
                echo "This does NOT remove:"
                echo "  - Your project's .babel/ directories (your data is safe)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Run './uninstall.sh --help' for usage"
                exit 1
                ;;
        esac
    done

    # Try to read from version file if exists
    if [ -z "$INSTALL_DIR" ]; then
        if [ -f "$DEFAULT_INSTALL_DIR/version" ]; then
            source "$DEFAULT_INSTALL_DIR/version" 2>/dev/null || true
            INSTALL_DIR="${install_dir:-$DEFAULT_INSTALL_DIR}"
            BIN_DIR="${bin_dir:-$DEFAULT_BIN_DIR}"
        else
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        fi
    fi

    if [ -z "$BIN_DIR" ]; then
        BIN_DIR="$DEFAULT_BIN_DIR"
    fi
}

# -----------------------------------------------------------------------------
# Uninstallation
# -----------------------------------------------------------------------------

confirm_uninstall() {
    if [ "$SKIP_CONFIRM" = true ]; then
        return 0
    fi

    echo ""
    echo "This will remove:"
    echo "  - $INSTALL_DIR/"
    # Check for both symlink and regular file (wrapper script on Windows)
    if [ -L "$BIN_DIR/babel" ]; then
        echo "  - $BIN_DIR/babel (symlink)"
    elif [ -f "$BIN_DIR/babel" ]; then
        echo "  - $BIN_DIR/babel (wrapper script)"
    fi
    echo ""
    echo "Your project .babel/ directories will NOT be affected."
    echo ""

    read -p "Proceed with uninstall? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
}

remove_symlink() {
    log_info "Removing babel command..."

    if [ -L "$BIN_DIR/babel" ]; then
        # It's a symlink (Linux/macOS, or Windows with symlink support)
        rm "$BIN_DIR/babel"
        log_success "Removed symlink: $BIN_DIR/babel"
    elif [ -f "$BIN_DIR/babel" ]; then
        # It's a regular file (wrapper script on Windows)
        if [ "$PLATFORM" = "windows" ]; then
            # On Windows, this is expected (wrapper script fallback)
            rm "$BIN_DIR/babel"
            log_success "Removed wrapper script: $BIN_DIR/babel"
        else
            # On Linux/macOS, a regular file is unexpected
            log_warn "$BIN_DIR/babel is not a symlink - removing anyway"
            rm "$BIN_DIR/babel"
            log_success "Removed: $BIN_DIR/babel"
        fi
    else
        log_warn "babel command not found: $BIN_DIR/babel"
    fi
}

remove_installation() {
    log_info "Removing installation directory..."

    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed: $INSTALL_DIR/"
    else
        log_warn "Installation directory not found: $INSTALL_DIR/"
    fi
}

get_shell_profile() {
    # Detect the appropriate shell profile file (same logic as install.sh)
    local shell_name
    shell_name=$(basename "${SHELL:-/bin/bash}")

    case "$PLATFORM" in
        windows)
            if [ -f "$HOME/.bash_profile" ]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        macos)
            case "$shell_name" in
                zsh)  echo "$HOME/.zshrc" ;;
                bash)
                    if [ -f "$HOME/.bash_profile" ]; then
                        echo "$HOME/.bash_profile"
                    else
                        echo "$HOME/.profile"
                    fi
                    ;;
                fish) echo "$HOME/.config/fish/config.fish" ;;
                *)    echo "$HOME/.profile" ;;
            esac
            ;;
        linux)
            case "$shell_name" in
                zsh)  echo "$HOME/.zshrc" ;;
                bash) echo "$HOME/.bashrc" ;;
                fish) echo "$HOME/.config/fish/config.fish" ;;
                *)    echo "$HOME/.profile" ;;
            esac
            ;;
        *)
            echo "$HOME/.profile"
            ;;
    esac
}

cleanup_path_config() {
    log_info "Checking PATH configuration..."

    local profile_file
    profile_file=$(get_shell_profile)

    if [ ! -f "$profile_file" ]; then
        return 0
    fi

    # Check if our marker exists in the file
    if grep -q "babel-tool installer" "$profile_file" 2>/dev/null; then
        # Create a temp file and remove our lines
        local temp_file
        temp_file=$(mktemp)

        # Remove the marker line and the PATH line that follows
        # Also remove the blank line before the marker
        sed '/^$/N;/\n# Added by babel-tool installer/d' "$profile_file" | \
        grep -v "# Added by babel-tool installer" | \
        grep -v "export PATH=\"$BIN_DIR:" > "$temp_file"

        # Replace original with cleaned version
        mv "$temp_file" "$profile_file"

        log_success "Removed PATH configuration from $profile_file"
    else
        log_info "No PATH configuration found in $profile_file"
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    parse_args "$@"

    echo ""
    echo "=========================================="
    echo "  Babel Tool Uninstaller"
    echo "=========================================="
    echo ""
    echo "  Platform: $PLATFORM"
    echo ""

    # Check if anything is installed (symlink OR file for Windows wrapper script)
    if [ ! -d "$INSTALL_DIR" ] && [ ! -L "$BIN_DIR/babel" ] && [ ! -f "$BIN_DIR/babel" ]; then
        log_warn "No installation found"
        echo ""
        echo "  Expected locations:"
        echo "    $INSTALL_DIR/"
        echo "    $BIN_DIR/babel"
        echo ""
        exit 0
    fi

    confirm_uninstall
    remove_symlink
    remove_installation
    cleanup_path_config

    echo ""
    echo "=========================================="
    echo "  Uninstall Complete"
    echo "=========================================="
    echo ""
    echo "  Babel tool has been removed."
    echo ""
    echo "  Note: Your project .babel/ directories are preserved."
    echo "  They contain your project data, not the tool."
    echo ""
    echo "  To reinstall: ./install.sh"
    echo ""
}

main "$@"
