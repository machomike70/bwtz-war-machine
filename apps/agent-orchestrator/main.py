from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict

COMMUNITY_LINK = "https://x.com/i/communities/2027587775332290785"
CTA = f"\n\nJoin the TextRp community today 👇\n{COMMUNITY_LINK}"

app = FastAPI(title="XtremeRippleProtocol X Growth Bot")

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "agent-orchestrator",
        "company": "XtremeRippleProtocol LLC",
        "white_label_service": True,
        "pricing": {
            "Free": "Limited to 5 posts/day",
            "Basic": "6 XRP per month - Unlimited posts & replies",
            "Pro": "12 XRP per month - Full features + daily batch generation"
        }
    }

class OrchestrateRequest(BaseModel):
    task: str
    account: Optional[str] = None
    context: Optional[str] = None
    client_brand: Optional[str] = None
    plan: Optional[str] = "Free"

@app.post("/orchestrate")
def orchestrate(request: OrchestrateRequest):
    task_lower = request.task.lower()
    acc = request.account or "@Mmozley70"
    brand = request.client_brand or "XtremeRippleProtocol LLC"
    plan = request.plan or "Free"

    if any(word in task_lower for word in ["daily", "batch", "5 posts"]):
        if plan == "Free":
            return {
                "status": "limited",
                "message": "Daily batch generation is a Pro feature (12 XRP/month). Upgrade for 5 ready posts per day.",
                "powered_by": brand
            }
        
        # Pro users get full schedule
        schedule = {}
        accounts = ["@Mmozley70", "@bwtzbearwitness", "@btckillas", "@getoffmylawn70", "@textrpsms"]
        for a in accounts:
            if a == "@textrpsms":
                posts = [
                    f"Good morning everyone. The TextRp community is a great place to connect, ask questions, and learn more about the platform.{CTA}",
                    f"Platform update: TextRp Launch Packs are the keys to the kingdom — granting access to all current and future features, feature pack airdrops, rev share participation, and multipliers on all reward engines.{CTA}",
                    f"Quick note: If you're new to TextRp, our community is open and welcoming. Feel free to join and connect with others who are building together.{CTA}",
                    f"Evening check-in: Another solid day in the TextRp community. Lots of good conversations and support happening.{CTA}",
                    f"Good night. The TextRp community remains a hub for onboarding and mutual support. Rest well — more updates coming soon.{CTA}"
                ]
            elif a == "@bwtzbearwitness":
                posts = [
                    f"Good morning. Another day of sharing the real story — redemption, survival, and building after 32 years inside. Art and life continue.{CTA}",
                    f"From prison to freedom at 51. The chaos, the art, the redemption — this is my story being told day by day. BWTZ NFTs help build the tattoo shop and the life I love through art.{CTA}",
                    f"Quick update from the real world: Life after release is wild. Grateful for every lesson and every new beginning.{CTA}",
                    f"Love the support and conversations. The story continues — survival, art, and second chances.{CTA}",
                    f"Good night. Reflecting on another day of telling the real story. Tomorrow brings more art and more life.{CTA}"
                ]
            elif a == "@btckillas":
                posts = [
                    f"Good morning Killas. BTCK on XRPL — pure meme with real transparency. Check the wallet tracking page.{CTA}",
                    f"BTCK is built for fun and transparency. Token + NFT staking is live. 589M tokens set to burn. BTCK NFTs are stakeable and add to liquidity and value.{CTA}",
                    f"Quick update: The BTCK community is growing. Full transparency on the wallet — no games. Affiliated with Spray The Chain.{CTA}",
                    f"Love the energy in the BTCK replies. Meme culture with real utility on XRPL.{CTA}",
                    f"Good night Killas. Another fun day in the BTCK ecosystem. Transparency and burns continue.{CTA}"
                ]
            elif a == "@getoffmylawn70":
                posts = [
                    f"Good morning. Get Off My Lawn with Grammy Tammy is back soon. Non-scripted, real conversations.{CTA}",
                    f"Upcoming space alert: Get Off My Lawn is all about real talk — no script, just good conversation.{CTA}",
                    f"Quick note: Our spaces are growing. Come hang with us and Grammy Tammy.{CTA}",
                    f"Love the energy from the last space. Get Off My Lawn is where real conversations happen.{CTA}",
                    f"Good night. Another great week of spaces with Grammy Tammy. Real talk, real people.{CTA}"
                ]
            else:  # @Mmozley70
                posts = [
                    f"Hey all, can I get a GM? Working across all projects and building new community partnerships.{CTA}",
                    f"Good morning. Focused on growing the ecosystem and supporting the communities I've built.{CTA}",
                    f"Quick update: New partnerships and conversations happening across the projects.{CTA}",
                    f"Love the support and energy from everyone. Building in public and connecting with great people.{CTA}",
                    f"Good night. Another productive day building and connecting. Rest up — more coming tomorrow.{CTA}"
                ]
            schedule[a] = [p + f" #XRP #XRPL #MEMES #NFTs #ART #UTILITY" for p in posts]
        return {
            "status": "success",
            "daily_schedule": schedule,
            "tip": "Pro plan active — full daily batch with GM/GN framing.",
            "powered_by": "XtremeRippleProtocol LLC"
        }

    # Free / Basic fallback
    return {"status": "success", "message": "Use /daily for the full schedule (Pro plan)."}

@app.get("/daily")
def daily_schedule():
    # Same logic as above — kept for direct access
    accounts = ["@Mmozley70", "@bwtzbearwitness", "@btckillas", "@getoffmylawn70", "@textrpsms"]
    schedule: Dict[str, List[str]] = {}
    for a in accounts:
        if a == "@textrpsms":
            posts = [
                f"Good morning everyone. The TextRp community is a great place to connect, ask questions, and learn more about the platform.{CTA}",
                f"Platform update: TextRp Launch Packs are the keys to the kingdom — granting access to all current and future features, feature pack airdrops, rev share participation, and multipliers on all reward engines.{CTA}",
                f"Quick note: If you're new to TextRp, our community is open and welcoming. Feel free to join and connect with others who are building together.{CTA}",
                f"Evening check-in: Another solid day in the TextRp community. Lots of good conversations and support happening.{CTA}",
                f"Good night. The TextRp community remains a hub for onboarding and mutual support. Rest well — more updates coming soon.{CTA}"
            ]
        elif a == "@bwtzbearwitness":
            posts = [
                f"Good morning. Another day of sharing the real story — redemption, survival, and building after 32 years inside. Art and life continue.{CTA}",
                f"From prison to freedom at 51. The chaos, the art, the redemption — this is my story being told day by day. BWTZ NFTs help build the tattoo shop and the life I love through art.{CTA}",
                f"Quick update from the real world: Life after release is wild. Grateful for every lesson and every new beginning.{CTA}",
                f"Love the support and conversations. The story continues — survival, art, and second chances.{CTA}",
                f"Good night. Reflecting on another day of telling the real story. Tomorrow brings more art and more life.{CTA}"
            ]
        elif a == "@btckillas":
            posts = [
                f"Good morning Killas. BTCK on XRPL — pure meme with real transparency. Check the wallet tracking page.{CTA}",
                f"BTCK is built for fun and transparency. Token + NFT staking is live. 589M tokens set to burn. BTCK NFTs are stakeable and add to liquidity and value.{CTA}",
                f"Quick update: The BTCK community is growing. Full transparency on the wallet — no games. Affiliated with Spray The Chain.{CTA}",
                f"Love the energy in the BTCK replies. Meme culture with real utility on XRPL.{CTA}",
                f"Good night Killas. Another fun day in the BTCK ecosystem. Transparency and burns continue.{CTA}"
            ]
        elif a == "@getoffmylawn70":
            posts = [
                f"Good morning. Get Off My Lawn with Grammy Tammy is back soon. Non-scripted, real conversations.{CTA}",
                f"Upcoming space alert: Get Off My Lawn is all about real talk — no script, just good conversation.{CTA}",
                f"Quick note: Our spaces are growing. Come hang with us and Grammy Tammy.{CTA}",
                f"Love the energy from the last space. Get Off My Lawn is where real conversations happen.{CTA}",
                f"Good night. Another great week of spaces with Grammy Tammy. Real talk, real people.{CTA}"
            ]
        else:  # @Mmozley70
            posts = [
                f"Hey all, can I get a GM? Working across all projects and building new community partnerships.{CTA}",
                f"Good morning. Focused on growing the ecosystem and supporting the communities I've built.{CTA}",
                f"Quick update: New partnerships and conversations happening across the projects.{CTA}",
                f"Love the support and energy from everyone. Building in public and connecting with great people.{CTA}",
                f"Good night. Another productive day building and connecting. Rest up — more coming tomorrow.{CTA}"
            ]
        schedule[a] = [p + f" #XRP #XRPL #MEMES #NFTs #ART #UTILITY" for p in posts]
    return {
        "status": "success",
        "daily_schedule": schedule,
        "tip": "Pro plan active — full daily batch with GM/GN framing.",
        "powered_by": "XtremeRippleProtocol LLC"
    }

@app.get("/orchestrate")
def orchestrate_get():
    return {
        "message": "White-label X Growth Bot by XtremeRippleProtocol LLC",
        "pricing": {
            "Free": "Limited",
            "Basic": "6 XRP/month",
            "Pro": "12 XRP/month - Daily batch generation"
        }
    }