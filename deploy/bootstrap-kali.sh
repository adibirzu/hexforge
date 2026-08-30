#!/usr/bin/env bash
# Idempotent prerequisite bootstrap for the KaliVM execution host.
#
# Brings every pentest tool HexForge and AetherOps depend on
# "in place": apt packages first, symlink fixes second, pinned Go tools last.
# Safe to re-run; already-present tools are skipped in seconds.
#
# Run this ON the KaliVM (root or sudo-capable user):
#   sudo ./bootstrap-kali.sh
# Or drive it remotely through the jump chain (run from an operator host):
#   KALI_USER=adi KALI_HOST=kali.cyber-sec.ro KALI_JUMP_HOST=adi@adi1 \
#     KALI_SSH_KEY=~/.ssh/kali_pentest_ed25519 deploy/remote-run.sh bootstrap
#
# Every location is a variable. Override anything via environment:
#   GO_BIN_DIR=/opt/go-bin SUDO="" INSTALL_OPTIONAL=0 ./bootstrap-kali.sh

set -euo pipefail

# ── Configurable locations & identities (no hardcoded paths) ──────────
SUDO="${SUDO:-sudo}"
export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"

BIN_DIR="${GO_BIN_DIR:-/usr/local/bin}"

APT_UPDATE="${APT_UPDATE:-1}"          # 1 = refresh apt indexes first
INSTALL_OPTIONAL="${INSTALL_OPTIONAL:-1}"  # heavier extras (rustscan et al)

# ── Tool sets ─────────────────────────────────────────────────────────
# Core recon/web/exploit-adjacent CLI available from Kali repos.
APT_TOOLS=(
  nmap masscan nuclei sqlmap nikto gobuster ffuf whatweb wpscan
  hydra john hashcat amass dirb wfuzz sslscan enum4linux smbclient
  # note: searchsploit ships inside the "exploitdb" package; ncat inside "nmap"
  exploitdb responder tshark tcpdump socat proxychains4
  wafw00f dnsrecon fierce theharvester spiderfoot legion
  dirsearch testssl.sh bettercap seclists subfinder httpx-toolkit
  feroxbuster autorecon arjun eyewitness sherlock assetfinder dnsx crlfuzz
  # platform prereqs for HexForge server & Go builds
  python3 python3-pip python3-venv git curl unzip ca-certificates golang
)

# Pinned Go tools absent from Kali repos (arch-independent source builds).
GO_TOOLS_PINNED=(
  "katana=github.com/projectdiscovery/katana/cmd/katana@v1.1.1"
  "dalfox=github.com/hahwul/dalfox/v2@v2.11.2"
  "gau=github.com/lc/gau/v2@v2.2.4"
  "waybackurls=github.com/tomnomnom/waybackurls@v0.1.0"
)

log()  { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[    ok   ]\033[0m %s\n' "$*"; }
miss() { printf '\033[1;33m[ missing ]\033[0m %s\n' "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

# ── Stage 1: apt layer ────────────────────────────────────────────────
log "Stage 1/4: apt package layer (${#APT_TOOLS[@]} candidates)"

if [ "$APT_UPDATE" = "1" ]; then
  $SUDO apt-get update -qq
fi

to_install=()
for t in "${APT_TOOLS[@]}"; do
  # dpkg owns the check (a tool may exist off-PATH without its package).
  if dpkg-query -W -f='${Status}' "$t" 2>/dev/null | grep -q "install ok installed"; then
    ok "apt: $t already installed"
  else
    miss "apt: $t -> queued"
    to_install+=("$t")
  fi
done

if [ ${#to_install[@]} -gt 0 ]; then
  log "Installing ${#to_install[@]} apt packages: ${to_install[*]}"
  $SUDO apt-get install -y -qq "${to_install[@]}"
else
  log "apt layer complete - nothing to do"
fi

# ── Stage 2: symlink/path repairs ─────────────────────────────────────
log "Stage 2/4: PATH repairs"

# Clean any stale/broken link (e.g. one pointing at the /etc/testssl data dir)
if [ -L "$BIN_DIR/testssl.sh" ] && { [ -d "$BIN_DIR/testssl.sh" ] || [ ! -x "$BIN_DIR/testssl.sh" ]; }; then
  $SUDO rm -f "$BIN_DIR/testssl.sh"
fi

if ! have testssl.sh; then
  # Kali's package installs the entrypoint as /usr/bin/testssl; expose it
  # under the canonical testssl.sh name too.
  ts_binary=""
  for cand in "$(command -v testssl || true)" /usr/bin/testssl /usr/bin/testssl.sh \
    "$(dpkg -L testssl.sh 2>/dev/null | grep -m1 -E '^/usr/(s?bin|lib)/.*testssl\.sh$' || true)"; do
    if [ -n "$cand" ] && [ -f "$cand" ] && [ -x "$cand" ]; then ts_binary="$cand"; break; fi
  done
  if [ -n "$ts_binary" ]; then
    $SUDO ln -sf "$ts_binary" "$BIN_DIR/testssl.sh"
    ok "testssl.sh linked: $ts_binary -> $BIN_DIR/testssl.sh"
  else
    miss "testssl.sh binary not found inside its package; leaving as-is"
  fi
else
  ok "testssl.sh on PATH"
fi

# ── Stage 3: pinned Go tools ──────────────────────────────────────────
log "Stage 3/4: pinned Go tools -> $BIN_DIR"

export GOBIN="$BIN_DIR"
export CGO_ENABLED="${CGO_ENABLED:-0}"
export GOPROXY="${GOPROXY:-https://proxy.golang.org,direct}"

for entry in "${GO_TOOLS_PINNED[@]}"; do
  name="${entry%%=*}"
  module="${entry#*=}"
  if have "$name"; then
    ok "go: $name present"
    continue
  fi
  log "go install: $module"
  if ! $SUDO -E go install -trimpath "$module"; then
    miss "go build failed for $name - continuing (non-fatal)"
  fi
done

# ── Stage 4: optional extras ──────────────────────────────────────────
if [ "$INSTALL_OPTIONAL" = "1" ] && ! have rustscan; then
  log "Stage 4/4: optional extras"
  arch="$(dpkg --print-architecture)"
  case "$arch" in
    amd64|arm64)
      # Probe the latest release for a matching .deb asset instead of
      # guessing names that change between releases.
      url="$(curl -fsSL --max-time 20 "https://api.github.com/repos/RustScan/RustScan/releases/latest" \
        | grep -m1 -oE "https://[^\" ]*rustscan[^\"]*_${arch}\.deb" || true)"
      if [ -n "${url:-}" ]; then
        tmp="$(mktemp --suffix=.deb)"
        if curl -fsSL --max-time 60 -o "$tmp" "$url"; then
          $SUDO dpkg -i "$tmp" >/dev/null 2>&1 || $SUDO apt-get install -y -f -qq >/dev/null
          rm -f "$tmp"
          if have rustscan; then ok "rustscan installed from release deb"; else miss "rustscan deb installed but binary still absent"; fi
        else
          rm -f "$tmp"
          miss "rustscan download failed - skipping (nmap covers it)"
        fi
      else
        miss "no rustscan release asset for $arch today - skipping (nmap covers it)"
      fi
      ;;
    *) miss "rustscan: no packaged asset for $arch - skipping";;
  esac
else
  log "Stage 4/4: optional extras skipped or satisfied"
fi

# ── Summary gate: fail loudly if anything core is still missing ───────
log "Verification sweep"
core=(nmap nuclei sqlmap nikto gobuster ffuf whatweb subfinder httpx-toolkit dnsx feroxbuster dirsearch testssl.sh searchsploit)
fail=0
for t in "${core[@]}"; do
  # testssl.sh counts as present when Kali's native /usr/bin/testssl exists.
  if have "$t" || { [ "$t" = "testssl.sh" ] && have testssl; }; then
    ok "$t"
  else
    miss "$t STILL ABSENT"; fail=$((fail+1))
  fi
done

if [ "$fail" -gt 0 ]; then
  printf '\n[bootstrap] INCOMPLETE: %d core tool(s) missing.\n' "$fail" >&2
  exit 1
fi

printf '\n[bootstrap] All prerequisites in place on %s (%s).\n' "$(hostname)" "$(dpkg --print-architecture)"
printf '[bootstrap] Generate/update the inventory manifest with: sudo deploy/kali-inventory.sh\n'
