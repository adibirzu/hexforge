# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Canonical product is HexForge v6.5 (`adibirzu/hexforge`). `/home/adi/GitHub/hexstrike-ai` is the live QLoRA training clone — never write, retarget, or kill it. This repo is not `0x4m4/hexstrike-ai`.
- Named hosts, operator port cutover (`:8888` legacy HexStrike v6.0 vs `:8889` HexForge v6.5), and KaliVM access: `deploy/FLEET.md`. Start on adi1 with `deploy/run-operator.sh`.
- Prove edition via `GET /health/identity` (and `/health`): `product=HexForge`, `version=6.5.0`, `edition=hexforge`, `enhanced_modules`. Identity helpers live in `hexstrike_identity.py`.
- KaliVM jump: `deploy/remote-run.sh` with `KALI_SSH_KEY=~/.ssh/kali_pentest_ed25519`. Missing key is a hard fail (exit 3), not a prompt to hunt credentials.
- Tests: `python3 -m unittest discover -s tests -v` (no Flask server required).

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
