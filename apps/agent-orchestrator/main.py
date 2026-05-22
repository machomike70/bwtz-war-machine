"""
Bwtz War Machine — Growth & Utility Engine for Bear Witness $BWTZ (Xtreme Ripple Protocol)

- Serves the beautiful copy-to-clipboard daily dashboard at /
- Exposes /daily JSON (used by gateway proxy, worker scheduler, external clients)
- Prefers persisted posts from Postgres (written by the worker) when available for "today"
- Fallback to high-quality static templates (the original brand voices)
- Future: /generate, status updates, integration with x-twitter-bot for queuing
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from datetime import date
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

COMMUNITY_LINK = "https://x.com/i/communities/2027587775332290785"
CTA = f"\n\nJoin the TextRp community today 👇\n{COMMUNITY_LINK}"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_stack:change-me@postgres:5432/ai_stack")

app = FastAPI(title="Bwtz War Machine", description="Growth & Utility Engine for Bear Witness $BWTZ | Xtreme Ripple Protocol")


# ----------------------------- DB helpers -----------------------------

def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def get_todays_posts_from_db() -> Dict[str, List[Dict[str, Any]]]:
    """Return today's posts grouped by account, preferring DB over templates."""
    today = date.today()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT account_handle, content, status, source
                    FROM daily_posts
                    WHERE scheduled_for = %s
                    ORDER BY account_handle, id
                    """,
                    (today,)
                )
                rows = cur.fetchall()

        if not rows:
            return {}

        grouped: Dict[str, List[Dict]] = {}
        for r in rows:
            h = r["account_handle"]
            if h not in grouped:
                grouped[h] = []
            grouped[h].append({
                "content": r["content"],
                "status": r["status"],
                "source": r["source"]
            })
        return grouped
    except Exception as e:
        # DB not ready or down → graceful fallback to static generation
        return {}


# ----------------------------- Static template generator (fallback) -----------------------------

def _base_posts_for_account(handle: str) -> List[str]:
    if handle == "@textrpsms":
        return [
            f"Good morning everyone. The TextRp community is a great place to connect, ask questions, and learn more about the platform.{CTA}",
            f"Platform update: TextRp Launch Packs are the keys to the kingdom — granting access to all current and future features, feature pack airdrops, rev share participation, and multipliers on all reward engines.{CTA}",
            f"Quick note: If you're new to TextRp, our community is open and welcoming. Feel free to join and connect with others who are building together.{CTA}",
            f"Evening check-in: Another solid day in the TextRp community. Lots of good conversations and support happening.{CTA}",
            f"Good night. The TextRp community remains a hub for onboarding and mutual support. Rest well — more updates coming soon.{CTA}",
        ]
    elif handle == "@bwtzbearwitness":
        return [
            f"Good morning. Another day of sharing the real story — redemption, survival, and building after 32 years inside. Art and life continue.{CTA}",
            f"From prison to freedom at 51. The chaos, the art, the redemption — this is my story being told day by day. BWTZ NFTs help build the tattoo shop and the life I love through art.{CTA}",
            f"Quick update from the real world: Life after release is wild. Grateful for every lesson and every new beginning.{CTA}",
            f"Love the support and conversations. The story continues — survival, art, and second chances.{CTA}",
            f"Good night. Reflecting on another day of telling the real story. Tomorrow brings more art and more life.{CTA}",
        ]
    elif handle == "@btckillas":
        return [
            f"Good morning Killas. BTCK on XRPL — pure meme with real transparency. Check the wallet tracking page.{CTA}",
            f"BTCK is built for fun and transparency. Token + NFT staking is live. 589M tokens set to burn. BTCK NFTs are stakeable and add to liquidity and value.{CTA}",
            f"Quick update: The BTCK community is growing. Full transparency on the wallet — no games. Affiliated with Spray The Chain.{CTA}",
            f"Love the energy in the BTCK replies. Meme culture with real utility on XRPL.{CTA}",
            f"Good night Killas. Another fun day in the BTCK ecosystem. Transparency and burns continue.{CTA}",
        ]
    elif handle == "@getoffmylawn70":
        return [
            f"Good morning. Get Off My Lawn with Grammy Tammy is back soon. Non-scripted, real conversations.{CTA}",
            f"Upcoming space alert: Get Off My Lawn is all about real talk — no script, just good conversation.{CTA}",
            f"Quick note: Our spaces are growing. Come hang with us and Grammy Tammy.{CTA}",
            f"Love the energy from the last space. Get Off My Lawn is where real conversations happen.{CTA}",
            f"Good night. Another great week of spaces with Grammy Tammy. Real talk, real people.{CTA}",
        ]
    else:  # @Mmozley70
        return [
            f"Hey all, can I get a GM? Working across all projects and building new community partnerships.{CTA}",
            f"Good morning. Focused on growing the ecosystem and supporting the communities I've built.{CTA}",
            f"Quick update: New partnerships and conversations happening across the projects.{CTA}",
            f"Love the support and energy from everyone. Building in public and connecting with great people.{CTA}",
            f"Good night. Another productive day building and connecting. Rest up — more coming tomorrow.{CTA}",
        ]


def generate_static_schedule() -> Dict[str, List[str]]:
    accounts = ["@Mmozley70", "@bwtzbearwitness", "@btckillas", "@getoffmylawn70", "@textrpsms"]
    schedule = {}
    for a in accounts:
        posts = _base_posts_for_account(a)
        schedule[a] = [p + f" #XRP #XRPL #MEMES #NFTs #ART #UTILITY" for p in posts]
    return schedule


# ----------------------------- API Endpoints -----------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    """Beautiful dark-mode dashboard — the main daily tool for the team."""
    html = """
    <html>
    <head>
        <title>Bwtz War Machine • Bear Witness $BWTZ</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Space+Grotesk:wght@500;600&amp;display=swap');
            
            :root {
                --bg: #0a0a0a;
                --card: #111111;
                --accent: #00ff9d;
            }
            
            body { 
                font-family: 'Inter', system_ui, sans-serif; 
                margin: 0; 
                background: var(--bg); 
                color: #ddd; 
                line-height: 1.5;
            }
            .container { max-width: 1100px; margin: 40px auto; padding: 0 20px; }
            h1 { 
                font-family: 'Space Grotesk', sans-serif; 
                color: #fff; 
                font-size: 2.4rem; 
                margin: 0 0 8px;
                letter-spacing: -1px;
            }
            .subtitle { color: #666; margin-bottom: 32px; font-size: 1.05rem; }
            
            .account { 
                margin: 24px 0; 
                padding: 22px 26px; 
                background: var(--card); 
                border-radius: 16px; 
                border: 1px solid #222;
            }
            .account-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 14px;
            }
            .handle { 
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.35rem; 
                color: #fff; 
                font-weight: 600;
            }
            .post-count { 
                font-size: 0.8rem; 
                background: #1f1f1f; 
                padding: 2px 10px; 
                border-radius: 999px; 
                color: #888;
            }
            
            .post {
                background: #1a1a1a;
                padding: 14px 18px;
                border-radius: 10px;
                margin: 10px 0;
                font-size: 0.95rem;
                position: relative;
                transition: all 0.1s ease;
            }
            .post:hover {
                background: #222;
                transform: translateY(-1px);
            }
            .post button {
                background: var(--accent);
                color: #000;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                font-size: 0.85rem;
                margin-top: 8px;
            }
            .post button:hover { background: #00cc7a; }
            
            .status {
                font-size: 0.7rem;
                padding: 1px 7px;
                border-radius: 4px;
                margin-left: 8px;
            }
            .status.pending { background: #3a2f00; color: #ffcc00; }
            .status.posted { background: #003322; color: #00ff9d; }
            
            .tip {
                background: #111;
                border: 1px solid #222;
                padding: 14px 20px;
                border-radius: 12px;
                font-size: 0.9rem;
                color: #888;
            }
            
            .header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;
            }
            .logo {
                width: 42px;
                height: 42px;
                background: linear-gradient(135deg, #00ff9d, #00cc7a);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #000;
                font-weight: 800;
                font-size: 1.4rem;
            }

            /* Additional styles for operational dashboard actions */
            #trigger-btn {
                background: #222;
                color: #ddd;
                border: 1px solid #444;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 0.82rem;
                cursor: pointer;
                white-space: nowrap;
                transition: all 0.1s;
            }
            #trigger-btn:hover:not(:disabled) {
                background: #333;
                border-color: #00ff9d;
                color: #fff;
            }
            #trigger-btn:disabled {
                opacity: 0.6;
                cursor: wait;
            }

            .post .copy-btn {
                background: var(--accent);
                color: #000;
            }
            .post .mark-btn {
                background: #2a2a2a;
                color: #ddd;
                border: 1px solid #555;
            }
            .post .mark-btn:hover {
                background: #3a3a3a;
                border-color: #888;
            }
            .post button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .post .action-row button {
                margin-top: 0;
            }
            .action-row {
                margin-top: 8px;
                display: flex;
                gap: 8px;
                align-items: center;
                flex-wrap: wrap;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">T</div>
                <div style="flex:1">
                    <h1>Bwtz War Machine</h1>
                    <div class="subtitle">Bwtz War Machine • Bear Witness $BWTZ • Xtreme Ripple Protocol</div>
                </div>
                <button id="trigger-btn" title="Ask worker to regenerate today's posts (may require worker restart for immediate effect in Phase 1)">🔄 Regenerate / Trigger Now</button>
            </div>

            <div id="controls" style="margin: 8px 0 16px; display:flex; gap:8px; align-items:center;">
                <span id="trigger-msg" style="font-size:0.8rem; color:#666;"></span>
            </div>

            <div id="posts"></div>

            <!-- X Safe Posting Queue Panel (Phase 1-2 human-in-the-loop via x-twitter-bot) -->
            <div id="x-queue-panel" style="margin-top: 32px; padding: 18px; background: #111; border: 1px solid #222; border-radius: 12px;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; gap:12px;">
                    <div style="font-weight:600; color:#00ccff;">🛡️ X Posting Queue — Dry-Run + Explicit Confirm (No auto-posting)</div>
                    <button onclick="loadXQueue()" style="background:#1da1f2;color:#fff;border:none;padding:5px 11px;border-radius:6px;cursor:pointer;font-size:0.8rem;">↻ Refresh X Queue</button>
                </div>
                <div id="x-queue-list" style="min-height:60px; font-size:0.85rem; color:#bbb; line-height:1.4;">(Queue empty or loading... Use "Post via X (dry run)" buttons on posts below to populate.)</div>
            </div>

            <div class="tip" style="margin-top: 40px;">
                <strong>Safe X Workflow (Phase 1-2):</strong> Review → <strong>Post via X (dry run)</strong> button (preview + auto-queue) → review result → use <strong>CONFIRM &amp; POST</strong> in the X Queue panel above to actually publish via the real X API. 
                Every real post requires your explicit confirmation. Powered by x-twitter-bot service.
                <br><br>
                <strong>Manual path still available:</strong> Copy + paste directly to X + Mark as Posted.
                <br><br>
                <strong>Accounts:</strong> @Mmozley70 • @bwtzbearwitness (BWTZ) • @btckillas (BTCK) • @getoffmylawn70 • @textrpsms
            </div>
        </div>

        <script>
            // Global store for current schedule (rich objects) — avoids putting raw content into onclick/attrs (XSS-safe)
            let scheduleData = {};

            function escapeHtml(text) {
                if (text == null) return '';
                return String(text)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            }

            async function loadPosts() {
                const res = await fetch('/daily');
                const data = await res.json();
                const container = document.getElementById('posts');
                scheduleData = data.daily_schedule || {};
                let html = '';

                for (const acc in scheduleData) {
                    const posts = scheduleData[acc] || [];
                    html += `
                        <div class="account">
                            <div class="account-header">
                                <div class="handle">${escapeHtml(acc)}</div>
                                <div class="post-count">${posts.length} posts</div>
                            </div>
                    `;
                    
                    posts.forEach((post, idx) => {
                        // post is always rich object now: {content, status, source}
                        const content = post.content !== undefined ? post.content : post;
                        const status = (post.status || 'pending').toLowerCase();
                        const source = post.source || '';
                        const isPosted = status === 'posted';
                        
                        // Safe data attrs only (no raw content in event handlers)
                        html += `
                            <div class="post" data-acc="${escapeHtml(acc)}" data-idx="${idx}">
                                <div>${escapeHtml(content).replace(/\n/g, '<br>')}</div>
                                <div class="action-row" style="margin-top:8px; display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
                                    <button onclick="copyCurrent(this)" class="copy-btn">Copy</button>
                                    ${isPosted 
                                        ? `<span class="status posted">posted ✓</span>` 
                                        : `<button onclick="markCurrent(this)" class="mark-btn">Mark as Posted</button>`
                                    }
                                    ${!isPosted && acc.toLowerCase().includes('bwtz') ? `<button onclick="startXPostFlow(this)" class="x-btn" style="background:#1da1f2;color:#fff;border:none;padding:4px 9px;border-radius:6px;font-size:0.78rem;cursor:pointer;">Post via X (dry run)</button>` : ''}
                                    <span class="status ${status}">${status}</span>
                                    ${source ? `<small style="margin-left:4px; color:#555; font-size:0.7rem;">(${escapeHtml(source)})</small>` : ''}
                                </div>
                            </div>
                        `;
                    });
                    
                    html += `</div>`;
                }
                
                container.innerHTML = html || '<p style="color:#666">No posts for today yet. The worker will generate them shortly (check worker logs or hit Regenerate).</p>';
            }

            function getPostFromEl(el) {
                const postDiv = el.closest('.post');
                if (!postDiv) return null;
                const acc = postDiv.dataset.acc;
                const idx = parseInt(postDiv.dataset.idx, 10);
                const arr = scheduleData[acc];
                return (arr && arr[idx]) ? arr[idx] : null;
            }

            function copyCurrent(btn) {
                const p = getPostFromEl(btn);
                if (!p) return;
                const text = p.content !== undefined ? p.content : p;
                navigator.clipboard.writeText(text).then(() => {
                    const original = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.style.background = '#00cc7a';
                    setTimeout(() => {
                        btn.textContent = original;
                        btn.style.background = '';
                    }, 1400);
                }).catch(() => {
                    // Fallback
                    alert('Copy failed — select & copy manually:\n\n' + text);
                });
            }

            function markCurrent(btn) {
                const p = getPostFromEl(btn);
                if (!p) return;
                const postDiv = btn.closest('.post');
                const acc = postDiv.dataset.acc;
                const content = p.content !== undefined ? p.content : p;

                btn.disabled = true;
                btn.textContent = 'Marking...';

                fetch('/mark-posted', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account: acc, content: content })
                })
                .then(r => r.json())
                .then(res => {
                    if (res.status === 'success' || res.updated > 0) {
                        btn.textContent = 'Marked!';
                        // Refresh the whole list to show updated badge + hide button
                        setTimeout(loadPosts, 300);
                    } else {
                        alert('Could not mark: ' + (res.message || JSON.stringify(res)));
                        btn.disabled = false;
                        btn.textContent = 'Mark as Posted';
                    }
                })
                .catch(err => {
                    alert('Network error marking post: ' + err);
                    btn.disabled = false;
                    btn.textContent = 'Mark as Posted';
                });
            }

            // ==================== X Posting Integration (calls x-twitter-bot via gateway) ====================
            const X_GATEWAY_BASE = window.location.origin;  // Works both locally (via gateway on :8000) and in production (Caddy on 80/443)

            async function startXPostFlow(btn) {
                const p = getPostFromEl(btn);
                if (!p) return;
                const postDiv = btn.closest('.post');
                const acc = postDiv.dataset.acc;
                const content = p.content !== undefined ? p.content : p;

                const orig = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Previewing...';

                try {
                    // 1. Dry-run preview
                    const previewRes = await fetch(`${X_GATEWAY_BASE}/x/post/preview`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ account_handle: acc, content: content })
                    });
                    const preview = await previewRes.json();

                    if (!previewRes.ok) {
                        alert('Preview failed: ' + (preview.detail || JSON.stringify(preview)));
                        btn.disabled = false;
                        btn.textContent = orig;
                        return;
                    }

                    // Show preview result to human
                    const previewMsg = [
                        `DRY RUN for ${acc}`,
                        `Length: ${preview.length || '?'} / 280`,
                        preview.valid ? 'Valid ✓' : 'INVALID',
                        preview.duplicate_warning ? '⚠ ' + preview.duplicate_warning : '',
                        '',
                        'Content preview:',
                        (content || '').slice(0, 140) + (content.length > 140 ? '...' : ''),
                        '',
                        'Would post to: ' + (preview.would_post_url || 'N/A'),
                        '',
                        'Safety: This is ONLY a preview. Nothing posted yet.'
                    ].join('\n');

                    if (!confirm(previewMsg + '\n\nProceed to QUEUE this post for later explicit confirmation?')) {
                        btn.disabled = false;
                        btn.textContent = orig;
                        return;
                    }

                    // 2. Queue it (human chose to proceed)
                    btn.textContent = 'Queuing...';
                    const queueRes = await fetch(`${X_GATEWAY_BASE}/x/post/queue`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ account_handle: acc, content: content })
                    });
                    const queued = await queueRes.json();

                    if (!queueRes.ok) {
                        alert('Queue failed: ' + (queued.detail || JSON.stringify(queued)));
                        btn.disabled = false;
                        btn.textContent = orig;
                        return;
                    }

                    alert(`✅ Queued successfully!\nQueue ID: ${queued.queue_id}\n\nGo to the X Queue panel at top of page and click "CONFIRM & POST" for that item to publish to X for real.\n\n(You can queue multiple; confirms are one-by-one.)`);

                    // Refresh queue panel
                    loadXQueue();
                    btn.textContent = 'Queued ✓';
                    setTimeout(() => {
                        if (btn && btn.parentNode) {
                            btn.textContent = 'Re-queue?';
                            btn.disabled = false;
                        }
                    }, 2500);

                } catch (e) {
                    console.error(e);
                    alert('X flow error (is gateway + x-twitter-bot running on localhost:8000/8008?): ' + e);
                    btn.disabled = false;
                    btn.textContent = orig;
                }
            }

            async function loadXQueue() {
                const container = document.getElementById('x-queue-list');
                if (!container) return;
                container.innerHTML = 'Loading X queue from x-twitter-bot...';

                try {
                    const r = await fetch(`${X_GATEWAY_BASE}/x/post/queue`);
                    const items = await r.json();

                    if (!Array.isArray(items) || items.length === 0) {
                        container.innerHTML = '<em style="color:#777">No pending items in X queue. Use the blue "Post via X (dry run)" buttons on daily posts to add some.</em>';
                        return;
                    }

                    let h = '';
                    items.forEach(item => {
                        const short = (item.content || '').slice(0, 90).replace(/\n/g, ' ') + ((item.content || '').length > 90 ? '...' : '');
                        const isFinal = item.status === 'posted' || item.status === 'failed';
                        h += `
                            <div style="background:#1a1a1a; padding:8px 10px; margin:6px 0; border-radius:8px; border:1px solid #222;">
                                <div><strong>${escapeHtml(item.account_handle)}</strong> <span style="color:#888;font-size:0.7rem;">#${item.id} • ${item.status}</span></div>
                                <div style="font-size:0.8rem; color:#ddd; margin:3px 0;">${escapeHtml(short)}</div>
                                ${item.post_url ? `<a href="${item.post_url}" target="_blank" style="color:#1da1f2; font-size:0.75rem;">View on X →</a>` : ''}
                                ${item.error_message ? `<div style="color:#f66; font-size:0.7rem;">Error: ${escapeHtml(item.error_message)}</div>` : ''}
                                ${!isFinal ? `
                                    <button onclick="confirmXPost(${item.id}, this)" 
                                            style="margin-top:4px; background:#ffcc00; color:#000; border:none; padding:3px 8px; border-radius:4px; font-size:0.75rem; cursor:pointer;">
                                        CONFIRM &amp; POST TO X
                                    </button>
                                ` : `<span style="font-size:0.7rem; color:#0a0;">${item.status.toUpperCase()}</span>`}
                            </div>
                        `;
                    });
                    container.innerHTML = h;
                } catch (e) {
                    container.innerHTML = `<span style="color:#a66">Failed to load X queue (gateway/x-twitter-bot down?): ${e}</span>`;
                }
            }

            async function confirmXPost(queueId, btn) {
                if (!confirm(`CONFIRM REAL POST for queue #${queueId}?\n\nThis will call the X API and publish the tweet for real. There is no undo.`)) {
                    return;
                }

                const orig = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Posting to X...';

                try {
                    const r = await fetch(`${X_GATEWAY_BASE}/x/post/confirm`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ queue_id: queueId })
                    });
                    const res = await r.json();

                    if (res.status === 'posted' || res.tweet_id) {
                        alert(`✅ SUCCESSFULLY POSTED TO X!\n\nTweet ID: ${res.tweet_id}\nURL: ${res.post_url || ''}\n\nThe post is now live. Queue item updated.`);
                        loadXQueue();
                        // Also refresh daily to pick up any mark-posted side-effect
                        setTimeout(loadPosts, 800);
                    } else if (res.status === 'already_posted') {
                        alert('Already posted: ' + (res.post_url || ''));
                        loadXQueue();
                    } else {
                        alert('Confirm result: ' + JSON.stringify(res));
                        btn.disabled = false;
                        btn.textContent = orig;
                    }
                } catch (e) {
                    alert('Confirm/post failed: ' + e);
                    btn.disabled = false;
                    btn.textContent = orig;
                }
            }

            // Auto-load X queue once on start (lightweight)
            function initXQueue() {
                setTimeout(loadXQueue, 1200);
            }

            async function triggerNow() {
                const btn = document.getElementById('trigger-btn');
                const msg = document.getElementById('trigger-msg');
                const origText = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Triggering...';
                msg.textContent = 'Contacting orchestrator...';

                try {
                    const r = await fetch('/trigger-daily', { method: 'POST' });
                    const j = await r.json();
                    msg.textContent = j.message || 'Triggered.';
                    msg.style.color = '#0a0';
                    // Give worker a moment, then refresh posts (in case it immediately persisted)
                    setTimeout(() => {
                        loadPosts();
                        setTimeout(() => { msg.textContent = ''; msg.style.color = '#666'; }, 4000);
                    }, 1200);
                } catch (e) {
                    msg.textContent = 'Trigger failed (see console).';
                    msg.style.color = '#a33';
                    console.error(e);
                } finally {
                    btn.disabled = false;
                    btn.textContent = origText;
                    setTimeout(() => { if (msg.textContent.includes('failed')) msg.textContent = ''; }, 6000);
                }
            }

            // Wire up trigger button (after DOM ready via script load)
            function initTrigger() {
                const tbtn = document.getElementById('trigger-btn');
                if (tbtn) tbtn.addEventListener('click', triggerNow);
            }

            // Initial load + periodic refresh
            loadPosts();
            setInterval(loadPosts, 60000);

            // Init after first paint
            setTimeout(initTrigger, 50);
            setTimeout(initXQueue, 800);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/daily")
def daily_schedule():
    """
    JSON endpoint used by the gateway, the worker scheduler, and external tools.
    In Phase 1: prefers persisted DB posts when they exist for today.
    Falls back to the original high-quality static templates.
    """
    db_posts = get_todays_posts_from_db()
    
    if db_posts:
        # Return DB-backed posts as rich objects (content + status + source) for dashboard badges + workflow
        return {
            "status": "success",
            "source": "database",
            "date": str(date.today()),
            "daily_schedule": db_posts,
            "tip": "Posts loaded from database (generated by worker). Human review + mark-as-posted recommended before/after posting on X.",
            "powered_by": "XtremeRippleProtocol LLC"
        }
    
    # Fallback to static (original behavior) — normalized to rich objects so JS always sees {content, status, source}
    static = generate_static_schedule()
    rich_schedule = {}
    for handle, contents in static.items():
        rich_schedule[handle] = [
            {"content": c, "status": "pending", "source": "template"}
            for c in contents
        ]
    return {
        "status": "success",
        "source": "template",
        "date": str(date.today()),
        "daily_schedule": rich_schedule,
        "tip": "Static templates (worker has not persisted today's batch yet or DB is unavailable).",
        "powered_by": "XtremeRippleProtocol LLC"
    }


@app.get("/healthz")
def health():
    return {"ok": True, "service": "agent-orchestrator", "phase": "1"}


# ----------------------------- Phase 1 operational endpoints -----------------------------

class MarkPostedRequest(BaseModel):
    account: str
    content: str


@app.post("/mark-posted")
def mark_posted(req: MarkPostedRequest):
    """Real implementation: mark a specific post as posted by updating the DB row for today."""
    today = date.today()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE daily_posts
                    SET status = 'posted', posted_at = NOW()
                    WHERE account_handle = %s
                      AND content = %s
                      AND scheduled_for = %s
                    """,
                    (req.account, req.content, today)
                )
                updated = cur.rowcount
        if updated > 0:
            return {
                "status": "success",
                "updated": updated,
                "message": "Post marked as posted successfully."
            }
        else:
            return {
                "status": "not_found",
                "updated": 0,
                "message": "No matching pending post found for today (content must match exactly)."
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class TriggerRequest(BaseModel):
    pass  # no body needed


@app.post("/trigger-daily")
def trigger_daily():
    """
    Bonus: Trigger endpoint for dashboard "Regenerate / Trigger Now" button.
    Stub for Phase 1 — acknowledges the request. Real wiring would signal the worker
    (e.g. via Redis pub/sub, HTTP callback to worker, or shared queue).
    For immediate effect now: restart the worker container (it runs scheduled_job on boot).
    """
    return {
        "status": "accepted",
        "message": "Trigger received. The worker will generate/persist a fresh batch on its next scheduled run (or restart the worker service for immediate regeneration).",
        "date": str(date.today()),
        "note": "Dashboard will auto-refresh posts shortly."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)