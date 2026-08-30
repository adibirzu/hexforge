#!/usr/bin/env bash
# Generates the KaliVM toolchain inventory manifest (JSON) for HexForge.
#
# Captures: OS/kernel/arch, apt package count, Kali metapackages, and a
# versioned presence map of every tool the platform dispatches. Output goes
# to stdout; redirect to deploy/kali-tools-<date>.json to commit an update.
#
# Run ON the KaliVM:
#   ./kali-inventory.sh > kali-tools-$(date +%F).json

set -euo pipefail

TOOLS=(
  nmap masscan nuclei sqlmap nikto gobuster ffuf whatweb wpscan hydra
  john hashcat msfconsole amass dirb dirsearch wfuzz testssl.sh sslscan
  enum4linux smbclient searchsploit responder bettercap tshark tcpdump
  nc socat proxychains4 wafw00f dnsrecon fierce theHarvester spiderfoot
  legion sherlock eyewitness arjun subfinder httpx-toolkit katana dalfox
  crlfuzz gau waybackurls assetfinder dnsx feroxbuster rustscan autorecon
)

version_probe() {
  local t="$1"
  local v=""
  case "$t" in
    nmap)        v="$(nmap --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+[0-9]*' | head -1)" ;;
    nuclei)      v="$(nuclei -version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    sqlmap)      v="$(sqlmap --version 2>/dev/null | tr -d '#stable ' | head -1)" ;;
    gobuster)    v="$(gobuster version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    ffuf)        v="$(ffuf -V 2>/dev/null | grep -oE 'v[0-9][0-9a-z.\-]*' | head -1)" ;;
    whatweb)     v="$(whatweb --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)" ;;
    hydra)       v="$(hydra -V 2>&1 | head -1 | grep -oE 'v[0-9.]+' | head -1)" ;;
    hashcat)     v="$(hashcat --version 2>/dev/null | head -1)" ;;
    sslscan)     v="$(sslscan --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    smbclient)   v="$(smbclient --version 2>/dev/null | head -1)" ;;
    tshark)      v="$(tshark -v 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    tcpdump)     v="$(tcpdump --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    dnsrecon)    v="$(dnsrecon -h 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    subfinder)   v="$(subfinder -version 2>&1 | tail -1)" ;;
    httpx-toolkit) v="$(httpx-toolkit -version 2>&1 | tail -1)" ;;
    dnsx)        v="$(dnsx -version 2>&1 | tail -1)" ;;
    feroxbuster) v="$(feroxbuster --version 2>&1 | tail -1)" ;;
    dirsearch)   v="$(dirsearch --version 2>&1 | tail -1)" ;;
    spiderfoot)  v="$(spiderfoot -l :0 2>/dev/null | head -1 || echo '')" ;;
    katana)      v="$(katana -version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    dalfox)      v="$(dalfox version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    crlfuzz)     v="$(crlfuzz -version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" ;;
    *)           v="$( "$t" --version 2>&1 | LC_ALL=C tr -d '\001-\037' | head -1 | cut -c1-60 )" ;;
  esac
  printf '%s' "${v:-unknown}"
}

emit_tool() {
  local t="$1" p v
  if p="$(command -v "$t" 2>/dev/null)"; then
    # Strip ANSI escapes and other control chars; some tools colorize --version.
    v="$(version_probe "$t" | LC_ALL=C tr -d '\001-\037')"
    printf '    "%s": {"path": "%s", "version": "%s"},\n' "$t" "$p" "${v//\"/\\\"}"
  else
    printf '    "%s": null,\n' "$t"
  fi
}

metapackages() {
  dpkg -l 2>/dev/null \
    | awk '$2 ~ /^kali-(meta|linux|tools|defaults|top10)/ && $1=="ii" {print $2}' \
    | sed 's/^/    "/; s/$/"/' \
    | paste -sd, -
}

{
  printf '{\n'
  printf '  "generated": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "hostname": "%s",\n' "$(hostname)"
  printf '  "os_pretty_name": "%s",\n' "$( (. /etc/os-release && echo "$PRETTY_NAME") 2>/dev/null || uname -s)"
  printf '  "kernel": "%s",\n' "$(uname -r)"
  printf '  "arch": "%s",\n' "$(dpkg --print-architecture)"
  printf '  "apt_packages_installed": %s,\n' "$(dpkg -l | grep -c '^ii')"
  printf '  "kali_metapackages": [%s],\n' "$(metapackages)"
  printf '  "tools": {\n'
  for t in "${TOOLS[@]}"; do emit_tool "$t"; done | sed '$ s/,$//'
  printf '  }\n}\n'
}
