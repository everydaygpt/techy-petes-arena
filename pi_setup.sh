#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  TECHY PETE'S INVESTMENT APP — Raspberry Pi Setup
#
#  Run this on a fresh Raspberry Pi OS install:
#    curl -sSL https://raw.githubusercontent.com/everydaygpt/techy-petes-arena/main/pi_setup.sh | bash
#
#  Or copy this file to your Pi and run:
#    chmod +x pi_setup.sh && ./pi_setup.sh
# ═══════════════════════════════════════════════════════════════

set -e

echo ""
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║       TECHY PETE'S INVESTMENT APP                    ║"
echo "  ║       Raspberry Pi Auto-Setup                        ║"
echo "  ╚═══════════════════════════════════════════════════════╝"
echo ""

# ─── Step 1: System updates & dependencies ──────────────────
echo "[1/6] Updating system and installing dependencies..."
sudo apt update -y && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git curl

# ─── Step 2: Install GitHub CLI ─────────────────────────────
echo ""
echo "[2/6] Installing GitHub CLI..."
if ! command -v gh &> /dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update -y
    sudo apt install -y gh
    echo "  GitHub CLI installed."
else
    echo "  GitHub CLI already installed."
fi

# ─── Step 3: Install Python packages ────────────────────────
echo ""
echo "[3/6] Installing Python packages..."
pip3 install --break-system-packages yfinance pandas numpy
echo "  Python packages installed."

# ─── Step 4: Clone the repo ─────────────────────────────────
echo ""
echo "[4/6] Cloning Techy Pete's Arena repo..."
INSTALL_DIR="$HOME/techy-petes-arena"
if [ -d "$INSTALL_DIR" ]; then
    echo "  Directory already exists. Pulling latest..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone https://github.com/everydaygpt/techy-petes-arena.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo "  Repo ready at: $INSTALL_DIR"

# ─── Step 5: GitHub authentication ──────────────────────────
echo ""
echo "[5/6] GitHub authentication..."
if gh auth status &> /dev/null; then
    echo "  Already authenticated with GitHub."
else
    echo "  You need to log in to GitHub so the Pi can push dashboard updates."
    echo "  Choose: GitHub.com → HTTPS → Login with a web browser"
    echo ""
    gh auth login
fi

# ─── Step 6: Install systemd service (auto-start on boot) ───
echo ""
echo "[6/6] Installing systemd service for auto-start..."

SERVICE_FILE="/etc/systemd/system/techy-pete.service"
sudo tee "$SERVICE_FILE" > /dev/null << SERVICEEOF
[Unit]
Description=Techy Pete's 5-Bot Trading Arena
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/multi_trader.py --deploy
Restart=on-failure
RestartSec=60
StandardOutput=append:$HOME/techy-pete-bot.log
StandardError=append:$HOME/techy-pete-bot.log

# Give network time to connect after boot
ExecStartPre=/bin/sleep 30

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable techy-pete.service
echo "  Service installed and enabled for auto-start on boot."

# ─── Done ────────────────────────────────────────────────────
echo ""
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║  SETUP COMPLETE!                                     ║"
echo "  ╠═══════════════════════════════════════════════════════╣"
echo "  ║                                                       ║"
echo "  ║  Your bots are installed at:                          ║"
echo "  ║    ~/techy-petes-arena                                ║"
echo "  ║                                                       ║"
echo "  ║  Bot log file:                                        ║"
echo "  ║    ~/techy-pete-bot.log                               ║"
echo "  ║                                                       ║"
echo "  ║  Dashboard:                                           ║"
echo "  ║    everydaygpt.github.io/techy-petes-arena/           ║"
echo "  ║             arena_dashboard.html                      ║"
echo "  ║                                                       ║"
echo "  ║  COMMANDS:                                            ║"
echo "  ║    Start now:   sudo systemctl start techy-pete       ║"
echo "  ║    Stop:        sudo systemctl stop techy-pete        ║"
echo "  ║    Status:      sudo systemctl status techy-pete      ║"
echo "  ║    View log:    tail -f ~/techy-pete-bot.log          ║"
echo "  ║    Test deploy: cd ~/techy-petes-arena &&             ║"
echo "  ║                 python3 multi_trader.py --test         ║"
echo "  ║                                                       ║"
echo "  ║  The bots will auto-start on every reboot and         ║"
echo "  ║  trade during market hours (9:30AM-4PM ET).           ║"
echo "  ╚═══════════════════════════════════════════════════════╝"
echo ""
read -p "  Start the bots now? (yes/no): " START_NOW
if [ "$START_NOW" = "yes" ]; then
    sudo systemctl start techy-pete
    echo "  Bots are running! Check: tail -f ~/techy-pete-bot.log"
fi
echo ""
