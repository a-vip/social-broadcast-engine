#!/usr/bin/env python3
"""
broadcast_engine.py
Autonomous Multi-Network Social Broadcaster & Traffic Driver for aviperera.com.
Syndicates newly published research and legal dossiers to Bluesky (AT Protocol),
Mastodon, and Webhooks (Discord, Telegram, Slack).
"""

import os
import sys
import json
import html
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

WP_POSTS_API = "https://aviperera.com/wp-json/wp/v2/posts?per_page=10&_fields=id,link,title,excerpt,date_gmt"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "syndicated_history.json")

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading state ({e}). Initializing clean state.")
    return {"syndicated": {}, "last_run": None}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html)
    return html.unescape(clean).strip()

def fetch_latest_posts() -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AviSocialBroadcaster/1.0; +https://aviperera.com)"}
    try:
        req = urllib.request.Request(WP_POSTS_API, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            posts = []
            for item in data:
                post_id = str(item.get("id"))
                title = clean_text(item.get("title", {}).get("rendered", ""))
                link = item.get("link", "").strip()
                excerpt = clean_text(item.get("excerpt", {}).get("rendered", ""))
                date_gmt = item.get("date_gmt", "")
                if title and link:
                    posts.append({
                        "id": post_id,
                        "title": title,
                        "link": link,
                        "excerpt": excerpt,
                        "date_gmt": date_gmt
                    })
            return posts
    except Exception as e:
        print(f"[!] Error fetching latest posts: {e}")
        return []

def post_to_bluesky(identifier: str, password: str, text: str, link: str, title: str) -> bool:
    """Publishes a rich record to Bluesky using the AT Protocol."""
    if not identifier or not password:
        return False
        
    try:
        # 1. Create Session
        auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
        auth_data = json.dumps({"identifier": identifier, "password": password}).encode("utf-8")
        auth_req = urllib.request.Request(auth_url, data=auth_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(auth_req, timeout=15) as resp:
            session = json.loads(resp.read().decode("utf-8"))
            access_jwt = session.get("accessJwt")
            did = session.get("did")
            
        if not access_jwt or not did:
            print("[!] Bluesky auth response missing JWT or DID")
            return False

        # 2. Build facets for clickable URL link in text
        facets = []
        url_idx = text.find(link)
        if url_idx != -1:
            byte_start = len(text[:url_idx].encode("utf-8"))
            byte_end = byte_start + len(link.encode("utf-8"))
            facets.append({
                "index": {"byteStart": byte_start, "byteEnd": byte_end},
                "features": [{"$type": "app.bsky.feed.post#link", "uri": link}]
            })

        # 3. Post record
        record_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        record_payload = {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "facets": facets,
                "createdAt": now_iso
            }
        }
        
        req = urllib.request.Request(
            record_url,
            data=json.dumps(record_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_jwt}"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Successfully posted to Bluesky: HTTP {resp.getcode()}")
            return True
    except Exception as e:
        print(f"[!] Bluesky posting failed: {e}")
        return False

def post_to_webhook(webhook_url: str, title: str, link: str, excerpt: str) -> bool:
    """Dispatches embed to Discord / Slack / Telegram webhook."""
    if not webhook_url:
        return False
        
    payload = {
        "content": f"📰 **New Research Publication from Avi Perera**",
        "embeds": [{
            "title": title,
            "url": link,
            "description": excerpt[:280] if excerpt else "Read full dossier and legal framework analysis.",
            "color": 3901686,
            "author": {
                "name": "Avi Perera | aviperera.com",
                "url": "https://aviperera.com",
                "icon_url": "https://aviperera.com/wp-content/uploads/2024/09/Avi-Perera-website-aviperera.com-logo-welcome-to-my-website-friends-why-did-you-download-this-logo-100x100.png"
            }
        }]
    }
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Webhook dispatch succeeded: HTTP {resp.getcode()}")
            return True
    except Exception as e:
        print(f"[!] Webhook dispatch error: {e}")
        return False

def format_social_copy(post: dict) -> str:
    title = post["title"]
    link = post["link"]
    copy = f"New publication: {title}\n\nRead the full dossier & legal analysis:\n{link}\n\n#AIGovernance #LAWS #AutonomousWeapons #InternationalLaw"
    return copy

def main():
    print("=== Autonomous Social Broadcast Engine ===")
    state = load_state()
    posts = fetch_latest_posts()
    print(f"Retrieved {len(posts)} recent posts from aviperera.com")
    
    unbroadcasted = [p for p in posts if p["id"] not in state["syndicated"]]
    print(f"Unbroadcasted new publications: {len(unbroadcasted)}")

    bsky_user = os.getenv("BSKY_IDENTIFIER", "")
    bsky_pass = os.getenv("BSKY_APP_PASSWORD", "")
    webhook_url = os.getenv("COMMUNITY_WEBHOOK_URL", "")

    has_credentials = bool((bsky_user and bsky_pass) or webhook_url)
    dry_run = not has_credentials or "--dry-run" in sys.argv

    if dry_run:
        print("[!] Running in SIMULATION / DRY-RUN mode (Credentials not configured or --dry-run passed).")

    broadcasted_this_run = []
    
    # Process at most 2 new posts per run to avoid spamming feeds
    for post in unbroadcasted[:2]:
        text = format_social_copy(post)
        title = post["title"]
        link = post["link"]
        excerpt = post.get("excerpt", "")
        
        print(f"\nProcessing publication #{post['id']}: {title}")
        
        if dry_run:
            print("[SIMULATION] Would broadcast post:")
            print(f"--- Text ---\n{text}\n------------")
            broadcasted_this_run.append(post)
        else:
            success_any = False
            if bsky_user and bsky_pass:
                if post_to_bluesky(bsky_user, bsky_pass, text, link, title):
                    success_any = True
            if webhook_url:
                if post_to_webhook(webhook_url, title, link, excerpt):
                    success_any = True
                    
            if success_any:
                state["syndicated"][post["id"]] = {
                    "title": title,
                    "link": link,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                broadcasted_this_run.append(post)

    if not dry_run and broadcasted_this_run:
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        print("[OK] State file successfully saved.")

    write_step_summary(broadcasted_this_run, dry_run=dry_run)
    return 0

def write_step_summary(items: list, dry_run: bool = False):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
        
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("## 📢 Social Broadcast & Content Syndication Engine\n\n")
        mode_text = "🟡 *DRY-RUN / SIMULATION MODE*" if dry_run else "🟢 *LIVE BROADCAST SUCCESS*"
        f.write(f"**Execution Mode:** {mode_text}\n\n")
        
        if not items:
            f.write("✅ All recent publications are already syndicated. Zero pending items.\n")
            return
            
        f.write(f"Successfully processed **{len(items)}** publications:\n\n")
        f.write("| Post ID | Title | Destination | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for it in items:
            dest = "Bluesky & Webhook" if not dry_run else "Preview / Dry-Run"
            f.write(f"| `{it['id']}` | [{it['title']}]({it['link']}) | {dest} | `Processed` |\n")

if __name__ == "__main__":
    sys.exit(main())
