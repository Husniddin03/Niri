#!/usr/bin/env bash
# ==============================================================================
# Quick AI Module
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🤖 Quick AI yordamchisi sozlanmoqda...${NC}"

AI_DIR="$HOME/.config/quick-ai"
mkdir -p "$AI_DIR"

if [ ! -f "$AI_DIR/config.json" ]; then
    cat > "$AI_DIR/config.json" << 'EOF'
{
  "api_key": "YOUR_GEMINI_OR_OPENAI_API_KEY",
  "provider": "gemini",
  "model": "gemini-1.5-flash"
}
EOF
    echo -e "${YELLOW}⚠️  $AI_DIR/config.json yaratildi. API kalitingizni kiritib qo'ying.${NC}"
else
    echo -e "${GREEN}✓ $AI_DIR/config.json mavjud.${NC}"
fi

echo -e "${GREEN}✓ Quick AI moduli yakunlandi.${NC}"
