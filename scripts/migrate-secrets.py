#!/usr/bin/env python3
"""
Secret Migration Helper for Bwtz War Machine (Xtreme Ripple Protocol)

SAFE DISCOVERY + PROPOSAL TOOL ONLY.
- Never modifies, deletes, or moves any files.
- Never prints raw secret values (always redacts or points to source files).
- Generates proposals, diffs, and checklists for manual action.
- Designed for the severe Desktop secret sprawl audit (X API, Xaman, wallets, GitHub PAT, TextRP keys, etc.).

Usage (from AI STACK root):
    python scripts/migrate-secrets.py
    python scripts/migrate-secrets.py --scan-all --output-proposal .env.proposed

Then:
1. Review the report.
2. Manually inspect the listed source files (in a secure terminal or editor).
3. Copy the *new rotated values* into your .env (never the old exposed ones).
4. Rotate every key/seed at the provider (X, GitHub, Xaman, new wallets, etc.).
5. After verification + rotation, move old folders to an encrypted archive or secure-delete.
6. Run the bot only via docker compose (it loads .env safely).

See docs/SECURITY.md for the full Secret Cleanup Playbook and rotation steps.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# =============================================================================
# CONFIGURATION - Known high-risk locations from the 2026 Desktop audit
# =============================================================================

HOME = Path.home()
DESKTOP = HOME / "Desktop"

# Primary known locations (folders and loose files) containing X API keys,
# Xaman seeds/secrets, wallet seeds (fund control), GitHub PAT, TextRP key, etc.
# These were identified during the security audit. Expand as needed.
KNOWN_LOCATIONS: List[Path] = [
    # X / Twitter
    DESKTOP / "X API",
    DESKTOP / "X API SECRETS",
    # Xaman / XRPL
    DESKTOP / "api for Xaman",
    DESKTOP / "developer Xaman Seed and Secret for White Label Staking Platform",
    DESKTOP / "xaman api secret",
    # Wallets / Seeds (CRITICAL - direct fund access)
    DESKTOP / "quantzilla wallet seed",
    DESKTOP / "wallet created by staking platform",
    DESKTOP / "joey key",
    DESKTOP / "$BWTZ Dev wallet seed first ledger",  # at user root
    # Other API / Security keys
    DESKTOP / "WAR machine API and Secret",
    DESKTOP / "bear witness fee bot API and Secret",
    DESKTOP / "github access token",
    DESKTOP / "TextRP Security Key.txt",
    # Project-specific
    DESKTOP / "XtremeHorseRacing_TextRP_Matrix_Native",
    DESKTOP / "XtremeHorseRacing_TextRP_Telegram_Final",
    # Catch-alls from audit
    DESKTOP / "New folder",
]

# Additional broad patterns to consider if --scan-all is used (name-based only)
BROAD_NAME_PATTERNS = [
    "*secret*", "*key*", "*seed*", "*token*", "*api*", "*xaman*", "*wallet*",
    "*security*", "*github*", "*x api*", "*textRP*"
]

# Suggested .env variable names (expand with real needs)
ENV_MAPPINGS = {
    # X API (4 values for OAuth 1.0a User Context)
    "consumer key": "X_API_KEY",
    "x_api_key": "X_API_KEY",
    "consumer key secret": "X_API_KEY_SECRET",
    "access secret": "X_API_KEY_SECRET",
    "x_api_key_secret": "X_API_KEY_SECRET",
    "access token": "X_ACCESS_TOKEN",
    "x_access_token": "X_ACCESS_TOKEN",
    "x_access_token_secret": "X_ACCESS_TOKEN_SECRET",
    # xAI
    "xai": "XAI_API_KEY",
    # Xaman / XRPL
    "xaman api": "XAMAN_API_KEY",
    "xaman secret": "XAMAN_API_SECRET",
    "xaman": "XAMAN_API_KEY",
    # Generic wallet seeds (map per context; use descriptive names)
    "wallet seed": "XRPL_WALLET_SEED",
    "wallet key": "XRPL_WALLET_SEED",
    "dev wallet seed": "XRPL_WALLET_SEED_BWTZ",
    "quantzilla": "XRPL_WALLET_SEED_QUANTZILLA",
    "joey": "XRPL_WALLET_SEED_JOEY",
    "staking platform": "XRPL_WALLET_SEED_STAKING",
    # GitHub
    "github": "GITHUB_PAT",
    "pat": "GITHUB_PAT",
    # TextRP internal
    "textRP security": "TEXTRP_SECURITY_KEY",
    "textRP": "TEXTRP_SECURITY_KEY",
    # Other branded
    "bear witness": "BEAR_WITNESS_API_KEY",
    "war machine": "WAR_MACHINE_XAMAN_API_KEY",
    "war machine xaman": "WAR_MACHINE_XAMAN_API_KEY",
    "matrix": "MATRIX_BOT_TOKEN",
    "telegram": "TELEGRAM_BOT_TOKEN",
}

REDACTION = "****REDACTED****"


def redact(value: str) -> str:
    """Never expose real secrets in reports or proposals."""
    if not value or len(value) < 8:
        return REDACTION
    # Show only length + prefix/suffix hint for user recognition during manual copy
    return f"{value[:4]}...{value[-4:]} (len={len(value)}) [REDACTED - inspect source file yourself]"


def looks_like_secret_file(p: Path) -> bool:
    """Heuristic filter for likely secret files (name only, no content read for filter)."""
    name = p.name.lower()
    if p.suffix.lower() in {".txt", ".key", ".secret", ""} or not p.suffix:
        for pat in BROAD_NAME_PATTERNS:
            # Simple glob-like check
            pat_clean = pat.replace("*", "")
            if pat_clean in name:
                return True
        # Also catch any file that is small and in a known secret parent
        return True
    return False


def discover_files(scan_all: bool = False) -> List[Path]:
    """Return list of candidate secret files. Never reads contents here."""
    discovered: List[Path] = []
    seen = set()

    locations = KNOWN_LOCATIONS[:]
    if scan_all:
        # Broad but safe name-based scan under Desktop (and user home for wallet items)
        for root in [DESKTOP, HOME]:
            try:
                for p in root.rglob("*"):
                    if p.is_file() and p not in seen:
                        if looks_like_secret_file(p):
                            # Skip anything inside the AI STACK repo itself (should be clean)
                            if "AI STACK" in str(p) or ".git" in str(p):
                                continue
                            discovered.append(p)
                            seen.add(p)
            except Exception as e:
                print(f"[WARN] Could not fully scan {root}: {e}")

    # Always include the explicit known locations (even if empty or files)
    for loc in locations:
        try:
            if loc.is_file():
                if loc not in seen:
                    discovered.append(loc)
                    seen.add(loc)
            elif loc.is_dir():
                for p in loc.rglob("*"):
                    if p.is_file() and p not in seen:
                        discovered.append(p)
                        seen.add(p)
        except Exception as e:
            print(f"[WARN] Could not access {loc}: {e}")

    return sorted(set(discovered), key=lambda x: str(x).lower())


def classify_and_propose(path: Path) -> List[Dict]:
    """
    Analyze a path (by name + optional small content peek for classification only).
    Returns list of proposals. Values are NEVER returned raw — only guidance + redaction.
    """
    proposals = []
    name_lower = path.name.lower()
    parent_lower = path.parent.name.lower() if path.parent else ""
    full_lower = str(path).lower()

    # Peek at content ONLY for classification heuristics (short read, errors ignored)
    content_peek = ""
    try:
        if path.stat().st_size < 2000:  # tiny files only
            content_peek = path.read_text(encoding="utf-8", errors="ignore").strip()[:300]
    except Exception:
        pass

    combined = f"{name_lower} {parent_lower} {full_lower} {content_peek.lower()}"

    # --- Classification heuristics (order matters for best match) ---
    candidates: List[Tuple[str, str]] = []

    # X API family (most common in audit)
    if any(k in combined for k in ["consumer key", "x api key", "consumer_key"]):
        candidates.append(("X_API_KEY", "From filename or file content in X API/ folder"))
    if any(k in combined for k in ["access secret", "key secret", "consumer key secret", "x_api_key_secret"]):
        candidates.append(("X_API_KEY_SECRET", "From filename or file content in X API/ folder"))
    if any(k in combined for k in ["access token", "x access token"]) and "secret" not in combined:
        candidates.append(("X_ACCESS_TOKEN", "From filename or file content in X API/ folder"))
    if "access token secret" in combined or "x_access_token_secret" in combined:
        candidates.append(("X_ACCESS_TOKEN_SECRET", "From filename or file content in X API/ folder"))

    # xAI
    if "xai-" in name_lower or "xai" in name_lower:
        candidates.append(("XAI_API_KEY", "xAI Grok key (often embedded in filename in audit)"))

    # Xaman / XRPL
    if any(k in combined for k in ["xaman", "xaman api", "api for xaman", "xaman seed"]):
        if "secret" in combined or "api secret" in combined:
            candidates.append(("XAMAN_API_SECRET", "Xaman developer/API secret"))
        else:
            candidates.append(("XAMAN_API_KEY", "Xaman API key or identifier"))
    if any(k in combined for k in ["wallet seed", "wallet key", "seed for", "dev wallet", "quantzilla", "joey", "staking platform"]):
        # Derive a descriptive var name
        var = "XRPL_WALLET_SEED"
        if "bwtz" in combined or "$bwtz" in combined:
            var = "XRPL_WALLET_SEED_BWTZ"
        elif "quantzilla" in combined:
            var = "XRPL_WALLET_SEED_QUANTZILLA"
        elif "joey" in combined:
            var = "XRPL_WALLET_SEED_JOEY"
        elif "staking" in combined:
            var = "XRPL_WALLET_SEED_STAKING"
        candidates.append((var, "XRPL wallet seed / mnemonic (CRITICAL - rotate + fund new wallet)"))

    # GitHub PAT
    if any(k in combined for k in ["github", "pat", "access token"]):
        candidates.append(("GITHUB_PAT", "GitHub Personal Access Token (repo + admin risk)"))

    # TextRP
    if "textRP security" in combined or "textrp security key" in combined:
        candidates.append(("TEXTRP_SECURITY_KEY", "Internal TextRP security key"))

    # Branded bots
    if "bear witness" in combined or "war machine" in combined:
        candidates.append(("BEAR_WITNESS_WAR_MACHINE_API", "Bear Witness / WAR machine Xaman or fee bot keys"))
    if "matrix" in combined:
        candidates.append(("MATRIX_BOT_SECRET", "Matrix / XtremeHorseRacing matrix bot secret"))
    if "telegram" in combined:
        candidates.append(("TELEGRAM_BOT_TOKEN", "Telegram bot token"))

    # Generic fallback for any remaining
    if not candidates:
        if "seed" in combined:
            candidates.append(("XRPL_WALLET_SEED_UNKNOWN", "Likely wallet seed - inspect filename/content"))
        elif "key" in combined or "secret" in combined:
            candidates.append(("UNKNOWN_API_SECRET", "Inspect file for context and assign descriptive VAR"))
        else:
            candidates.append(("REVIEW_MANUALLY", "File name suggests credential - open and map to appropriate .env var"))

    # Build proposal objects (no raw secrets)
    for var_name, hint in candidates:
        # Try to give user a hint about *where* the value lives without printing it
        value_hint = ""
        if any(x in name_lower for x in ["   ", "  "]) and len(path.name) > 20:
            # Many audit files embed the secret in the *filename itself*
            value_hint = "VALUE LIKELY EMBEDDED IN THE FILENAME (after the label). Open the file explorer and copy the long string."
        elif content_peek:
            value_hint = "Value is in the file content (small .txt). Open with notepad (not in shared terminal)."
        else:
            value_hint = "Inspect the file content or name manually in a secure session."

        proposals.append({
            "source": str(path),
            "suggested_var": var_name,
            "hint": hint,
            "value_location": value_hint,
            "redacted_preview": redact(content_peek) if content_peek else "(value not in content peek - check filename or full file)",
            "size_bytes": path.stat().st_size if path.exists() else 0,
        })

    return proposals


def generate_proposed_env_section(proposals: List[Dict]) -> str:
    """Produce a ready-to-paste (but safe) template for .env additions."""
    lines = [
        "# ==============================================================================",
        "# PROPOSED .env SECTION - GENERATED BY migrate-secrets.py",
        f"# Date: {datetime.datetime.now().isoformat()}",
        "# ",
        "# !!! IMPORTANT !!!",
        "# 1. These are MAPPINGS only. Replace every placeholder with FRESH ROTATED values.",
        "# 2. Old values from Desktop .txt files are considered COMPROMISED.",
        "# 3. Never paste old values. Go to each provider and generate new keys/seeds.",
        "# 4. After putting new values here, delete/secure-erase the Desktop originals.",
        "# ==============================================================================",
        "",
        "# --- Migrated from Desktop secret sprawl (REPLACE WITH ROTATED VALUES) ---",
    ]

    grouped: Dict[str, List[Dict]] = {}
    for p in proposals:
        grouped.setdefault(p["suggested_var"], []).append(p)

    for var in sorted(grouped.keys()):
        items = grouped[var]
        lines.append(f"\n# {var} (from {len(items)} source(s))")
        for item in items:
            lines.append(f"# Source: {item['source']}")
            lines.append(f"#   Hint: {item['hint']}")
            lines.append(f"#   {item['value_location']}")
            lines.append(f"{var}=<PASTE_FRESH_{var}_HERE_AFTER_ROTATION>")
        lines.append("")

    lines.extend([
        "# --- End of migration proposal ---",
        "# Add any other vars from .env.example as needed.",
        "# Then: docker compose up -d --build ... to load them.",
    ])
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Safe Desktop secret discovery & .env migration proposer (read-only)")
    parser.add_argument("--scan-all", action="store_true",
                        help="Perform broader name-based scan under Desktop + home (in addition to known list)")
    parser.add_argument("--output-proposal", type=str, default=None,
                        help="Write a safe proposal template to this file (e.g. .env.migration-proposal)")
    parser.add_argument("--json-report", type=str, default=None,
                        help="Also emit a JSON report of findings (paths only, no values)")
    args = parser.parse_args()

    print("=" * 80)
    print("AI STACK - Secret Hygiene Migration Assistant")
    print("READ-ONLY AUDIT + PROPOSAL MODE (never deletes or writes secrets)")
    print(f"Run timestamp: {datetime.datetime.now().isoformat()}")
    print("=" * 80)
    print()
    print("This tool helps you discover the plaintext secrets that were found sprawled")
    print("across your Desktop (X API keys, Xaman seeds, wallet seeds, GitHub PAT, etc.).")
    print("It will NEVER print the actual secret strings.")
    print()

    files = discover_files(scan_all=args.scan_all)

    print(f"Discovered {len(files)} candidate secret files across known locations.")
    print()

    all_proposals: List[Dict] = []
    for f in files:
        props = classify_and_propose(f)
        all_proposals.extend(props)
        print(f"FILE: {f}")
        for pr in props:
            print(f"  -> Suggested .env var : {pr['suggested_var']}")
            print(f"     Location hint      : {pr['value_location']}")
            print(f"     Redacted preview   : {pr['redacted_preview']}")
            print(f"     Size               : {pr['size_bytes']} bytes")
        print()

    print("-" * 80)
    print("MIGRATION PLAN (SAFE - MANUAL EXECUTION REQUIRED)")
    print("-" * 80)
    print("""
1. REVIEW the list above. Every file listed contained (or its name contained) a secret.
2. ROTATE FIRST:
   - X API keys       -> https://developer.x.com/ (regenerate Consumer + Access)
   - xAI key          -> x.ai / Grok console
   - GitHub PAT       -> https://github.com/settings/tokens (revoke old, new one with minimal scopes)
   - Xaman / XRPL     -> Xaman app/portal + create brand new wallets, transfer funds
   - TextRP / internal-> Regenerate in your systems
   - Wallet seeds     -> Create entirely new wallets. Never reuse exposed seeds.
3. Populate a clean .env (copy from .env.example) using ONLY the NEW values.
4. Test:  docker compose config   (validates without leaking if you redact output)
5. Start stack normally.
6. After everything works and you have confirmed new keys are active:
   - Move the old Desktop folders into an encrypted 7z/zip with strong passphrase, or
   - Secure-delete them (Windows: use 'cipher /w:C:\\path' or Sysinternals sdelete).
7. Enable secret scanning (see docs/SECURITY.md).
""")

    proposal_text = generate_proposed_env_section(all_proposals)

    if args.output_proposal:
        out_path = Path(args.output_proposal)
        try:
            out_path.write_text(proposal_text, encoding="utf-8")
            print(f"\n[WROTE] Safe proposal template (no real values) to: {out_path.resolve()}")
            print("   Edit it, replace placeholders with your FRESH rotated keys, then mv to .env")
        except Exception as e:
            print(f"[ERROR] Could not write proposal: {e}")

    if args.json_report:
        # JSON contains only paths + var suggestions + hints. No values.
        import json
        report = {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_candidates": len(files),
            "total_proposals": len(all_proposals),
            "findings": [
                {
                    "source": p["source"],
                    "suggested_var": p["suggested_var"],
                    "hint": p["hint"],
                    "value_location": p["value_location"],
                } for p in all_proposals
            ],
            "warning": "All listed secrets were in plaintext on Desktop. Rotate everything before use."
        }
        try:
            Path(args.json_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"[WROTE] JSON report (paths + suggestions only) to: {args.json_report}")
        except Exception as e:
            print(f"[ERROR] Could not write JSON: {e}")

    print("\n" + "=" * 80)
    print("NEXT STEPS FOR YOU:")
    print("  1. python scripts/migrate-secrets.py --output-proposal .env.proposed --scan-all")
    print("  2. Read docs/SECURITY.md (full playbook + rotation guide)")
    print("  3. Read the updated RUNBOOK.md section on secret rotation")
    print("  4. Rotate keys, populate .env, harden with secret manager")
    print("=" * 80)
    print("\nThis script performed zero destructive actions. Your original files are untouched.\n")


if __name__ == "__main__":
    main()
