#!/usr/bin/env bash
# Skill Factory — Hermes Installation Script
# ==========================================
# Installs the Skill Factory meta-skill and plugin into your Hermes config.

set -euo pipefail

HERMES_DIR="${HERMES_DIR:-$HOME/.hermes}"
SKILLS_DIR="$HERMES_DIR/skills"
PLUGINS_DIR="$HERMES_DIR/plugins"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[skill-factory]${NC} $*"; }
warn()    { echo -e "${YELLOW}[skill-factory]${NC} $*"; }
error()   { echo -e "${RED}[skill-factory]${NC} $*" >&2; exit 1; }

# ------------------------------------------------------------------
# Pre-flight checks
# ------------------------------------------------------------------

if [ ! -d "$HERMES_DIR" ]; then
  error "Hermes config directory not found at $HERMES_DIR. Is Hermes installed?"
fi

# ------------------------------------------------------------------
# Install the meta-skill (SKILL.md)
# ------------------------------------------------------------------

SKILL_DEST="$SKILLS_DIR/meta/skill-factory"
mkdir -p "$SKILL_DEST"

if [ -f "$SKILL_DEST/SKILL.md" ]; then
  warn "SKILL.md already exists at $SKILL_DEST/SKILL.md — overwriting."
fi

cp skills/skill-factory/SKILL.md "$SKILL_DEST/SKILL.md"
info "Installed: $SKILL_DEST/SKILL.md"

# ------------------------------------------------------------------
# Install the plugin
# ------------------------------------------------------------------

mkdir -p "$PLUGINS_DIR"

if [ -f "$PLUGINS_DIR/skill_factory.py" ]; then
  warn "plugin already exists at $PLUGINS_DIR/skill_factory.py — overwriting."
fi

cp plugins/skill_factory.py "$PLUGINS_DIR/skill_factory.py"
info "Installed: $PLUGINS_DIR/skill_factory.py"

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------

echo ""
info "✅ Skill Factory installed successfully!"
echo ""
echo "  Skills dir:  $SKILL_DEST/"
echo "  Plugin:      $PLUGINS_DIR/skill_factory.py"
echo ""
echo "  Next steps:"
echo "    1. Restart Hermes or run: hermes skills reload"
echo "    2. Activate the skill:    hermes skills enable skill-factory"
echo "    3. Start a session and let Skill Factory watch"
echo "    4. Run: /skill-factory propose   — to surface detected skills"
echo ""
