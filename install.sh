#!/bin/bash

# HexForge - Comprehensive Installer
# Supports Persistence, RAG, Evolution, and Reporting

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}🚀 HexForge v6.5 - Installation Script${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Create directory structure
echo -e "\n${YELLOW}[1/6] Creating directory structure...${NC}"
mkdir -p data/projects data/rag/chroma data/evolution schemas reports
touch data/.gitkeep
echo -e "${GREEN}✅ Directories created.${NC}"

# 2. Check for Python 3
echo -e "\n${YELLOW}[2/6] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"

# 3. Setup Virtual Environment
echo -e "\n${YELLOW}[3/6] Setting up virtual environment...${NC}"
VENV_NAME="hexstrike-env"
if [ ! -d "$VENV_NAME" ]; then
    python3 -m venv $VENV_NAME
    echo -e "${GREEN}✅ Virtual environment '$VENV_NAME' created.${NC}"
else
    echo -e "${BLUE}ℹ️  Virtual environment already exists.${NC}"
fi

# 4. Install Dependencies
echo -e "\n${YELLOW}[4/6] Installing Python dependencies...${NC}"
source $VENV_NAME/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed successfully.${NC}"
else
    echo -e "${RED}❌ requirements.txt not found!${NC}"
fi

# 5. Check/Install Core Security Tools (Kali Linux preferred)
echo -e "\n${YELLOW}[5/6] Checking for core security tools...${NC}"
TOOLS=("nmap" "sqlmap" "gobuster" "ffuf" "nuclei" "hydra" "john" "hashcat" "amass" "subfinder")
MISSING_TOOLS=()

for tool in "${TOOLS[@]}"; do
    if command -v $tool &> /dev/null; then
        echo -e "  [${GREEN}OK${NC}] $tool"
    else
        echo -e "  [${RED}MISSING${NC}] $tool"
        MISSING_TOOLS+=($tool)
    fi
done

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    echo -e "\n${YELLOW}⚠️  Some tools are missing. Attempting to install via apt (requires sudo)...${NC}"
    echo -e "${BLUE}Note: This works best on Kali/Debian/Ubuntu.${NC}"
    sudo apt update
    sudo apt install -y "${MISSING_TOOLS[@]}" feroxbuster dirsearch gdb foremost steghide volatility3 ghidra checksec sherlock
fi

# 6. Initialize Database
echo -e "\n${YELLOW}[6/6] Initializing local database...${NC}"
if [ -f "schemas/hexstrike_db.sql" ]; then
    # We use python to initialize since we have the persistence layer
    python3 -c "from hexstrike_persistence import get_persistence; get_persistence()"
    echo -e "${GREEN}✅ Database initialized at data/hexstrike.db${NC}"
else
    echo -e "${RED}❌ Database schema not found!${NC}"
fi

echo -e "\n${BLUE}================================================================${NC}"
echo -e "${GREEN}🎉 HexForge v6.5 installation complete!${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "\n${YELLOW}To start the server:${NC}"
echo -e "  1. source $VENV_NAME/bin/activate"
echo -e "  2. python3 hexstrike_server.py          # or: deploy/run-operator.sh"
echo -e "     If :8888 is already taken by legacy v6.0, use HEXSTRIKE_PORT=8889."
echo -e "\n${YELLOW}To start the MCP client:${NC}"
echo -e "  1. source $VENV_NAME/bin/activate"
echo -e "  2. python3 hexstrike_mcp.py --server http://localhost:8888"
echo -e "     HEXSTRIKE_URL / HEXSTRIKE_PORT override the default (see deploy/FLEET.md)."
echo -e "${BLUE}================================================================${NC}"
