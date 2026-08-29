# HexForge fleet (canonical v6.5)

Source of truth: GitHub `adibirzu/hexforge` (HexForge v6.5).
This is an independent product that reused early HexStrike history; it is **not** `0x4m4/hexstrike-ai`.

Do **not** merge, copy, or restart anything under `/home/adi/GitHub/hexstrike-ai`. That tree is the live QLoRA training clone (`qlora_train_aetheropstral.py`).

## Hosts named in this repo

Only these destinations are documented. Do not invent remotes.

| Role | Host | Notes |
|---|---|---|
| Operator | `adi1` (this machine) | Runs the API. Canonical process is HexForge v6.5 from this repo. |
| KaliVM execution host | `kali.cyber-sec.ro` | Tool bootstrap + inventory via `deploy/`. User `adi`, jump `adi@adi1`, key `~/.ssh/kali_pentest_ed25519`. |

## Operator (adi1)

- Start: `deploy/run-operator.sh` from a checkout of **this** repo (worktree, firstmate clone, or `/home/adi/GitHub/hexstrike-ai-enhanced` mirror).
- Identity: `GET /health/identity` and `GET /health` must report `product=HexForge`, `version=6.5.0`, `edition=hexforge`, and `enhanced_modules` for persistence, rag, checkpoint, optimizer, evolution, reporting. Legacy HexStrike v6.0 reports `version=6.0.0` and has no `/api/v2/*` routes.
- MCP client: `HEXSTRIKE_URL` or `HEXSTRIKE_PORT` (see `hexstrike_mcp.py`).

### Port cutover (2026-08-29)

v6.0 from `/home/adi/GitHub/hexstrike-ai` was already bound to `0.0.0.0:8888`. Captain order: do not take that listener down as the first step, and do not stop the QLoRA job.

| Listener | Tree | Version (health) | Action this change |
|---|---|---|---|
| `:8888` | `/home/adi/GitHub/hexstrike-ai` `hexstrike_server.py` | `6.0.0` | Left running. Taking it down is a captain `needs-decision`. |
| `:8889` | this repo (`HEXSTRIKE_PORT=8889`) | `product=HexForge` `6.5.0` / `edition=hexforge` | Canonical HexForge on adi1 until `:8888` is released. |

`deploy/run-operator.sh` never kills a bound port. If `:8888` is occupied and `HEXSTRIKE_PORT` is unset, it binds `8889`.

After captain approval to retire `:8888`, restart v6.5 with `HEXSTRIKE_PORT=8888` from this repo (still never from the training clone).

## KaliVM

```bash
KALI_USER=adi KALI_HOST=kali.cyber-sec.ro KALI_JUMP_HOST=adi@adi1 \
  KALI_SSH_KEY=~/.ssh/kali_pentest_ed25519 deploy/remote-run.sh deploy/bootstrap-kali.sh

KALI_USER=adi KALI_HOST=kali.cyber-sec.ro KALI_JUMP_HOST=adi@adi1 \
  KALI_SSH_KEY=~/.ssh/kali_pentest_ed25519 deploy/remote-run.sh deploy/kali-inventory.sh \
  > deploy/kali-tools-$(date +%F).json
```

`bootstrap-kali.sh` is idempotent (apt skip-if-installed, PATH repairs, pinned Go tools).

### Access status (2026-08-29)

Inventory/bootstrap from adi1 failed: `~/.ssh/kali_pentest_ed25519` is absent on the operator account, and `ssh` reported `Host key verification failed` for `kali.cyber-sec.ro`. Last committed snapshot remains `deploy/kali-tools-2026-08-25.json`. Re-run the commands above once the documented key (and known_hosts entry) are in place. Do not hunt other credentials.

## GPU / QLoRA

The operator server must not steal the training GPU. `deploy/run-operator.sh` leaves `CUDA_VISIBLE_DEVICES` empty unless the operator sets it. Do not load `sentence-transformers` embeddings on adi1 while QLoRA is running; RAG still imports and `/health` reports `rag_backends.embeddings=false` in that case.
