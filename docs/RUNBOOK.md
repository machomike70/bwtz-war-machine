# Bwtz War Machine — Runbook

**Growth & Utility Engine for Bear Witness $BWTZ**  
*Xtreme Ripple Protocol*

Practical operations guide for the Bwtz War Machine.

> **Security First**: A major Desktop secret sprawl incident was discovered and partially mitigated in 2026.  
> Before any key rotation or production use, read **[docs/SECURITY.md](SECURITY.md)** (Secret Cleanup Playbook) and run `python scripts/migrate-secrets.py`.

## Starting the Stack

Recommended minimal command for daily tool (Phase 1):

```bash
docker compose up -d --build postgres agent-orchestrator worker gateway-api
```

Full stack (includes future services + observability):

```bash
docker compose up -d --build
```

View dashboard: http://localhost:8001

## Manual Trigger / Regenerate Today's Posts

The worker performs an **initial generation** on every start/restart.

**Easiest method**:

```bash
docker compose restart worker
```

Watch progress:

```bash
docker compose logs -f worker
```

You will see:
- "Running initial daily generation for today..."
- "Persisted N new daily posts for YYYY-MM-DD"

Alternative (if you add a web endpoint later): POST to a future `/trigger` on worker.

## Viewing & Using Generated Posts (The Daily Tool)

1. Open http://localhost:8001
2. Each account card shows 5 posts (curated voice + community CTA).
3. Click **Copy to clipboard** on any post.
4. Paste directly into X (or a scheduler).
5. Posts are safe to copy multiple times (deduped in DB).

The page auto-refreshes every 60 seconds.

JSON alternative (for scripts/integrations): `http://localhost:8000/daily` or `http://localhost:8001/daily`

## Safe Posting Practices

- **Always review** before posting — the bot is a powerful assistant, not autonomous yet.
- Use the exact text from the dashboard (including the community link) to maintain consistent voice.
- Post at natural times; the two scheduled slots (08:00 / 20:00 UTC) are starting points.
- Never post the same content twice on the same day (the DB unique constraint prevents duplicates).
- When auto-posting is enabled (future):
  - Use dry-run mode first.
  - Respect X rate limits and per-account credential separation.
  - Implement retry + failure alerts.

**Current safety model**: Human-in-the-loop. The operator is the only one who actually hits "Post" on X.

## Troubleshooting

### Dashboard shows "No posts for today yet"

- Worker may still be starting / generating.
- Check logs: `docker compose logs --tail=100 worker`
- Force regeneration: `docker compose restart worker`
- Verify orchestrator is healthy: `curl http://localhost:8001/healthz`

### Worker fails to connect to orchestrator or DB

- Ensure `docker compose up` order respected the `depends_on` + healthchecks.
- Postgres password mismatch? Check `DATABASE_URL` in worker env vs postgres service.
- Restart everything cleanly:

  ```bash
  docker compose down
  docker compose up -d --build postgres
  # wait 10s
  docker compose up -d --build agent-orchestrator worker gateway-api
  ```

### Scheduler not firing at expected times

- Times are **UTC** (see `DAILY_POST_TIMES` in `.env` / compose).
- Verify `SCHEDULER_ENABLED=true`.
- Check worker logs for "Scheduled daily job at ..."

- To change schedule: edit `.env`, then `docker compose restart worker`

### Database issues / schema problems

- The worker creates tables on first run (`init_db`).
- To inspect:

  ```bash
  docker compose exec postgres psql -U ai_stack -d ai_stack
  \dt
  SELECT * FROM daily_posts ORDER BY id DESC LIMIT 20;
  ```

- Full reset (destructive):

  ```bash
  docker compose down -v   # removes postgres_data volume
  # then start again
  ```

### Port conflicts (5432, 8000, 8001, etc.)

- Stop conflicting local services (e.g. local Postgres).
- Or remap in `docker-compose.yml` (advanced).

### Container won't build / requirements error

- After editing `requirements.txt`, always use `--build`.
- Common: missing `psycopg[binary]` or `python-dotenv` in orchestrator (now fixed in this repo).

### High memory / many containers

- Use `docker compose up -d postgres agent-orchestrator worker gateway-api` for daily work (lighter).

## Rotating / Updating Keys & Secrets

> **CRITICAL 2026 UPDATE**: A full Desktop secret sprawl audit discovered dozens of plaintext X API keys, Xaman wallet seeds (fund control), GitHub PAT, "TextRP Security Key", and other credentials in `.txt` files and folders directly on the Desktop. 
> 
> **Old keys are considered compromised.** Always rotate at the provider **before** placing any value into the system.
> 
> **Primary reference**: [docs/SECURITY.md](SECURITY.md) — the complete Secret Cleanup Playbook, migration steps, and long-term recommendations.
> 
> Use `python scripts/migrate-secrets.py --scan-all` to rediscover and map any remaining files.

### X API Keys (when Phase 1+ posting is active)

1. **Rotate first** at https://developer.x.com/ (regenerate Consumer + Access tokens for each brand app and **revoke the old ones**).
2. Update the four values in `.env`:
   - `X_API_KEY`
   - `X_API_KEY_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
3. Restart affected services:

   ```bash
   docker compose restart x-twitter-bot worker
   ```

4. Never store keys in code or git. Use `.env` (gitignored) only.

### Xaman / XRPL Wallet Seeds & API Keys (Highest Risk)

These control real funds. If they ever lived in a Desktop `.txt`:

1. Invalidate old Xaman API keys in the Xaman portal/app.
2. **Create entirely new wallets** for every affected brand/account.
3. Transfer balances from old (exposed) wallets to the new ones.
4. Store the **new** seeds only via password manager or Doppler — never in `.env` long-term if possible.
5. Map them in `.env` using the naming convention from `.env.example` (e.g. `XRPL_WALLET_SEED_BWTZ`).

See the dedicated high-risk section in `docs/SECURITY.md`.

### GitHub PAT

1. Revoke the old token at https://github.com/settings/tokens.
2. Create a new fine-grained token with the narrowest possible scopes and short expiry.
3. Update `GITHUB_PAT` (or equivalent) in your secrets store / `.env`.

### TextRP Security Key & Other Brand Secrets (Bear Witness, WAR Machine, Matrix, Telegram, etc.)

Regenerate each at the source system. Update the corresponding `*_API_KEY`, `*_SECRET`, or `*_TOKEN` variables.

### Database Password

- Change in two places for consistency:
  1. `docker-compose.yml` under the `postgres` service (`POSTGRES_PASSWORD`)
  2. `DATABASE_URL` in `.env` and in the worker/orchestrator `environment:` blocks
- Then `docker compose down -v && docker compose up -d --build`

For production, move to Docker secrets or external secret manager.

### xAI / Grok Key

- Rotate in the xAI console first.
- Update `XAI_API_KEY` in `.env`
- Will be picked up when AI generation code is wired (no restart needed if services read at call time).

### General Secret Hygiene

- After any change: `docker compose config` (validates compose without exposing values in most outputs).
- Audit with: `git diff .env.example` (never diff real `.env` or commit it).
- Consider `.env.local` for machine-specific overrides (also gitignored).
- **Always run the migration helper** after any suspected Desktop activity:
  `python scripts/migrate-secrets.py`

**Production rule**: Move away from `.env` files entirely. Use Doppler, 1Password CLI, Docker secrets, or Vault. See SECURITY.md for the full comparison.

---

## Running the Bot Without Leaking Credentials

- **Official & safe method**: Always start with `docker compose up -d --build ...`. Compose automatically loads the (gitignored) `.env`.
- **Validation without leaks**: `docker compose config` (inspect the rendered config safely).
- **Never** execute `cat .env`, `type .env`, `Get-Content .env`, or `env | grep -i api` while screensharing, recording, or in a shared terminal.
- When pasting logs or error messages publicly or in tickets, **redact** every credential (`X_API_*`, `XAI_*`, `GITHUB_*`, `XRPL_WALLET_SEED*`, etc.).
- For team workflows: adopt `doppler run -- docker compose up` or `op run -- docker compose up` so that even the `.env` file can eventually be removed from developer machines.
- In any future CI/CD pipelines: store secrets exclusively in the platform's secret store (GitHub Actions secrets, etc.). Never bake them into images or repo files.

**If you ever suspect a leak**:
1. Rotate the affected credential(s) immediately.
2. Re-run the full Desktop audit + `trufflehog`.
3. Update this runbook with lessons learned.

See the "How to Run the Bot Without Leaking Credentials" and "Long-Term Secret Management Recommendations" sections in `docs/SECURITY.md` for deeper guidance and tool comparisons.

### Quick Secret Hygiene Commands

```powershell
# Re-audit Desktop for stray files
python scripts\migrate-secrets.py --scan-all

# Validate compose can see your .env (safe)
docker compose config --quiet

# View only non-secret parts of config
docker compose config | Select-String -Pattern "DATABASE_URL|SCHEDULER|DAILY"   # PowerShell
# or on bash: docker compose config | grep -E 'DATABASE|SCHEDULER|DAILY'
```

## Common Maintenance Commands

```bash
# Tail all logs
docker compose logs -f

# Specific service
docker compose logs -f worker

# Restart one piece
docker compose restart worker

# Rebuild after code change
docker compose up -d --build worker

# Full clean slate (including DB data)
docker compose down -v

# Check resource usage
docker stats

# Enter DB shell
docker compose exec postgres psql -U ai_stack -d ai_stack

# View today's posts directly in DB
docker compose exec postgres psql -U ai_stack -d ai_stack -c \
  "SELECT account_handle, left(content, 60) || '...' as preview, status FROM daily_posts WHERE scheduled_for = CURRENT_DATE ORDER BY account_handle;"
```

## Backup & Recovery

- Postgres data lives in Docker volume `postgres_data`.
- To backup:

  ```bash
  docker compose exec postgres pg_dump -U ai_stack ai_stack > backup-$(date +%F).sql
  ```

- Restore: stop services, recreate volume, import dump, restart.

## When to Escalate

- Repeated scheduler failures → check orchestrator reachability + DB connectivity.
- X posting errors (future) → verify credentials, app permissions on developer.x.com, and check rate-limit headers.
- Dashboard styling / JS issues → inspect browser console; the HTML/JS is self-contained in orchestrator `main.py`.

This runbook + the README should let any team member or new contributor operate the bot independently within minutes.

For architecture diagrams and component details see [ARCHITECTURE.md](ARCHITECTURE.md).
