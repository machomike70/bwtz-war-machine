# Secret Cleanup Playbook — Bwtz War Machine (Xtreme Ripple Protocol)

**Date of Audit**: 2026-05-21 (initial comprehensive Desktop secret sprawl review)  
**Severity**: CRITICAL  
**Status**: Discovered + Tools Provided + Hardening Applied. User action required for rotation + deletion.

---

## Executive Summary

During a full repository + host audit, **severe secret sprawl** was identified **directly on the user's Desktop** (outside the AI STACK repository).

### What Was Found (Plaintext, No Encryption)

- **X / Twitter API credentials** (full Consumer Key + Secret + Access Token + Secret) in:
  - `Desktop\X API\`
  - `Desktop\X API SECRETS\` (duplicate copy)
  - Filenames themselves often contained the actual key values (e.g. `Consumer Key   sSyZFWZ4...txt`)

- **Xaman (XRPL) API keys + Wallet Seeds** (direct control of XRP funds and accounts) in:
  - `api for Xaman\`
  - `developer Xaman Seed and Secret for White Label Staking Platform\`
  - `xaman api secret`
  - `wallet created by staking platform\`
  - `quantzilla wallet seed\`
  - `joey key\`
  - `$BWTZ Dev wallet seed first ledger` (user home)

- **GitHub Personal Access Token** (`github access token` file) — full repo + workflow compromise risk.

- **TextRP Security Key** (`TextRP Security Key.txt`)

- **Other operational secrets**:
  - `WAR machine API and Secret\`
  - `bear witness fee bot API and Secret`
  - `XtremeHorseRacing_TextRP_Matrix_Native\`
  - `XtremeHorseRacing_TextRP_Telegram_Final\`
  - Various "New folder\", "New Text Document.txt" containing credentials

**Risks**:
- Complete loss of XRP funds in affected wallets
- Full takeover of all TextRp X accounts (@bwtzbearwitness, @btckillas, @getoffmylawn70, etc.)
- GitHub repository and CI/CD compromise
- Reputational and operational damage to the entire TextRp / XtremeRippleProtocol ecosystem

**Positive note**: The AI STACK repository itself was **clean** — no real secrets were committed (thanks to existing `.gitignore` patterns). The `.env` on disk contained only development placeholders.

---

## Immediate Goals

1. **Discover** every exposed secret (use the helper script).
2. **Rotate** every single credential at the source **before** putting anything new into the system.
3. **Migrate** only fresh values into the AI STACK `.env` (or a real secrets manager).
4. **Securely destroy** or archive the Desktop plaintext copies.
5. **Harden** the project so this never happens again.
6. **Adopt** a proper secrets management workflow for the future.

---

## Step-by-Step Secret Cleanup Playbook

### Phase 0: Preparation (5 minutes)

1. Make sure you are in the AI STACK directory:
   ```powershell
   cd "C:\Users\Dell\Desktop\AI STACK"
   ```

2. Update the local tools (we added these during the agent run):
   - `scripts/migrate-secrets.py` (new)
   - `.env.example` (strengthened)
   - `.gitignore` (expanded patterns)
   - `.dockerignore` (new)
   - `docs/SECURITY.md` (this file)
   - `docs/RUNBOOK.md` and `README.md` updated

3. **Do not run the bot with any current keys yet.**

### Phase 1: Discovery (Run the Helper)

```powershell
python scripts\migrate-secrets.py --scan-all --output-proposal .env.proposed
# Optional JSON for records:
python scripts\migrate-secrets.py --scan-all --json-report secret-audit-report.json
```

The script:
- Only reads directory listings and tiny files for classification
- **Never prints actual secret values** (always redacted or "inspect source yourself")
- Produces a mapping proposal and a safe `.env.proposed` template
- Lists every file that needs manual review

**Review the output carefully.** Note the exact full paths.

### Phase 2: Rotation (Most Important Step — Do Not Skip)

**Never reuse an exposed secret.** The Desktop files have been sitting in plaintext for an unknown period.

#### X API Keys (developer.x.com)
1. Log into https://developer.x.com/
2. For each affected app (you likely have several):
   - Regenerate **Consumer Key & Secret**
   - Regenerate **Access Token & Secret** (or create new user context)
3. Record the **four new values** for each brand account.
4. In the X developer portal, **revoke the old tokens**.

#### xAI / Grok Key
- Regenerate at the xAI / Grok console.
- Old key is burned.

#### GitHub PAT
1. Go to https://github.com/settings/tokens
2. Delete/revoke all old tokens that were in the "github access token" file.
3. Create a **new fine-grained Personal Access Token** with only the minimum required scopes (e.g. `repo` read/write for this repo only, short expiration).
4. Never use classic tokens with broad scopes again.

#### Xaman + XRPL Wallet Seeds (Highest Financial Risk)
1. In the Xaman app / developer tools, **invalidate** any exposed API keys/secrets.
2. **Create brand new wallets** for every affected account (BWTZ, QuantZilla, Joey, Staking platform, Matrix, etc.).
3. Transfer any remaining XRP from the old (compromised) wallets to the new ones.
4. **Never import the old seeds again.** The old seeds are permanently tainted.
5. Store the **new** seeds only in a password manager or secrets vault.

#### TextRP Security Key / Other Brand Bots (Bear Witness, WAR Machine, Matrix, Telegram)
- Regenerate each key/token inside the respective service or admin panel.
- Update any other systems that used the old values.

**Document the new values** in a secure location (password manager note or Doppler project). Do **not** write them on paper or in new Desktop .txt files.

### Phase 3: Safe Migration into AI STACK

1. Copy `.env.example` → `.env` (if you haven't already).
2. Open the generated `.env.proposed` (or the script output).
3. For each suggested variable, paste the **brand new rotated value** (never the old Desktop one).
4. Fill the rest of the normal variables (DATABASE_URL, scheduler times, etc.).
5. Save `.env`.

**Validate** (safe — compose shows redacted form):
```powershell
docker compose config
```

### Phase 4: Test the Stack with New Credentials

```powershell
docker compose down -v
docker compose up -d --build postgres agent-orchestrator worker gateway-api
docker compose logs -f worker
```

Visit http://localhost:8001 and verify the daily tool still works.

When you later enable real X posting (`x-twitter-bot` service), the new X API keys will be used.

### Phase 5: Secure Destruction / Archival of Old Files

**Only after**:
- New keys are live and tested
- Old keys have been revoked at every provider
- You have confirmed the bot is posting/operating with the new credentials

**Then**:

**Recommended**:
- Create an encrypted archive:
  ```powershell
  # Using 7-Zip (install if needed) or Windows built-in with EFS + strong password
  7z a -p"EXTREMELY-STRONG-PASSPHRASE-HERE" -mhe=on C:\secure-backup\old-secrets-2026-05-21.7z "C:\Users\Dell\Desktop\X API" "C:\Users\Dell\Desktop\X API SECRETS" ...
  ```
- Then **secure-delete** the originals.

**Windows secure delete** (free Sysinternals `sdelete` or built-in):
```powershell
cipher /w:"C:\Users\Dell\Desktop\X API"
# Repeat for every folder and the loose files
```
Or use `sdelete -p 3 -s "C:\Users\Dell\Desktop\X API"` (multiple passes).

**Physical security**: If the machine is ever sold, stolen, or repurposed, the old files must not be recoverable.

After archival + secure delete, update any personal notes that the Desktop sprawl has been resolved.

---

## How to Run the Bot Without Leaking Credentials

- The only official way: `docker compose up ...` (it automatically loads `.env` via Compose).
- Never run `type .env`, `cat .env`, `Get-Content .env` in a shared screen, Zoom, or recorded terminal.
- When sharing logs or screenshots, always redact `X_API_*`, `XAI_*`, `GITHUB_PAT`, wallet seeds, etc.
- `docker compose config` is your friend — it shows the interpolated config safely for validation.
- In the future, when adding CI/CD, store secrets in GitHub Actions secrets / repository secrets (never in the repo).
- For local development with teammates: use Doppler or 1Password CLI:
  ```powershell
  doppler run -- docker compose up -d
  # or
  op run -- docker compose up -d
  ```

**Never**:
- Email secrets
- Paste into ChatGPT / public AI chats
- Store in Google Drive / OneDrive unencrypted
- Commit even temporarily

---

## Long-Term Secret Management Recommendations

| Environment | Recommended Tool                  | How to Use with AI STACK                          | Benefit |
|-------------|-----------------------------------|---------------------------------------------------|---------|
| Local Dev   | 1Password / Bitwarden CLI        | `op run -- docker compose up` or export to temp `.env` | Never store plaintext on disk |
| Team / CI   | Doppler                           | `doppler run -- docker compose ...`               | Centralized, auditable, easy rotation |
| Production  | Docker Secrets (Swarm) / Kubernetes Secrets / Vault | Mount as files or env at runtime only            | Ephemeral, never on host FS |
| All         | GitHub Secret Scanning + TruffleHog | Enable on repo + pre-commit hook                 | Catch mistakes before commit |

**Migration path for this project**:
- Today: `.env` (gitignored) + password manager
- Next: Doppler or 1Password for the whole team
- Production deployments: remove `.env` from hosts entirely, use secret injection

---

## Hardening Already Applied to the AI STACK (by this agent run)

- `.env.example` now contains a massive top-level warning banner + dedicated high-risk sections for Xaman/wallets/GitHub/TextRP.
- `.gitignore` expanded with many more Desktop credential patterns.
- `.dockerignore` added (prevents secrets and Desktop junk from entering image builds).
- `scripts/migrate-secrets.py` created (safe discovery + proposal tool).
- `docs/SECURITY.md` (this playbook) and updated `RUNBOOK.md`.
- Prominent warning added to `README.md`.
- Confirmed no real secrets were ever committed to git history.

---

## Prevention & Ongoing Hygiene

1. **Secret Scanning (enable now)**

   **Local** (recommended pre-commit):
   ```powershell
   # TruffleHog (best for this)
   pip install trufflehog
   trufflehog filesystem . --only-verified --fail
   # or
   trufflehog git file://. --since-commit HEAD~10
   ```

   **GitHub** (free for public repos, part of GHAS for private):
   - Repo → Settings → Security → Code security & analysis → Enable "Secret scanning" and "Push protection".

   Alternatives: `git-secrets`, `detect-secrets`, `gitleaks`.

2. **Pre-commit hook** (create `.pre-commit-config.yaml` later if desired).

3. **Never create new "API and Secret" folders on Desktop.** All future credentials go straight into the password manager or Doppler.

4. **Quarterly audit**: Re-run `python scripts/migrate-secrets.py --scan-all` and `trufflehog`.

5. **Principle**: If a secret ever touches a plaintext file on an end-user machine, rotate it.

---

## Appendix: Full List of Locations Audited (2026-05-21)

(Paths relative to `C:\Users\Dell\`)

**Desktop level folders**:
- `Desktop\X API\`
- `Desktop\X API SECRETS\`
- `Desktop\api for Xaman\`
- `Desktop\developer Xaman Seed and Secret for White Label Staking Platform\`
- `Desktop\joey key\`
- `Desktop\New folder\` (and subfolders)
- `Desktop\quantzilla wallet seed\`
- `Desktop\wallet created by staking platform\`
- `Desktop\WAR machine API and Secret\`
- `Desktop\XtremeHorseRacing_TextRP_Matrix_Native\`
- `Desktop\XtremeHorseRacing_TextRP_Telegram_Final\`

**Desktop level files**:
- `Desktop\bear witness fee bot API and Secret`
- `Desktop\github access token`
- `Desktop\TextRP Security Key.txt`
- `Desktop\xaman api secret`

**User root level**:
- `$BWTZ Dev wallet seed first ledger`

Many of the `.txt` files had the secret values embedded directly in their filenames — an especially dangerous anti-pattern.

**Inside the AI STACK repo**: Clean (verified via content search for key patterns; only placeholders and code words like "seed accounts" were present).

---

## When You Are Done

You should be able to say:

- "All old secrets have been rotated at the providers."
- "Only fresh values live in `.env` (or Doppler)."
- "The old Desktop folders have been encrypted + securely deleted."
- "Secret scanning is enabled on GitHub + locally."
- "Future credentials will never be stored in plaintext .txt files again."

At that point, update this document with the completion date and mark the incident closed.

---

**Maintained by the Security & Secret Hygiene agent process.**  
If you discover any additional files during cleanup, add them to the list above and re-run the migration script.

Stay safe. The TextRp ecosystem depends on it.
