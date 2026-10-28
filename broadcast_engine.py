#!/usr/bin/env python3
"""
broadcast_engine.py
Autonomous Multi-Network Social Broadcaster & Traffic Driver for aviperera.com.
Syndicates newly published research and essays to Bluesky (AT Protocol)
and Mastodon (ActivityPub/REST API), plus optional Community Webhooks.
"""

import os
import sys
import json
import html
import re
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from content_classifier import classify_content, build_utm_link

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

RSS_FEED_URL = "https://aviperera.com/feed/"
WP_POSTS_API = "https://aviperera.com/wp-json/wp/v2/posts?per_page=10&_fields=id,link,title,excerpt,date_gmt,categories"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "syndicated_history.json")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*",
    "Accept-Language": "en-US,en;q=0.9"
}

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "syndicated" not in data:
                    data["syndicated"] = {}
                return data
        except Exception as e:
            print(f"[!] Warning reading state ({e}). Initializing clean state.")
    return {"syndicated": {}, "last_run": None}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

from urllib.parse import urlparse

def normalize_mastodon_url(raw_url: str) -> str:
    """Normalizes any Mastodon input (domain, profile link, or subpath) to https://<domain>."""
    if not raw_url:
        return "https://mastodon.social"
    clean = raw_url.strip()
    if not clean.startswith("http://") and not clean.startswith("https://"):
        clean = "https://" + clean
    try:
        parsed = urlparse(clean)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    except Exception:
        pass
    return "https://mastodon.social"

def clean_xml_namespaces(xml_str: str) -> str:
    """Strips XML prefixes (e.g. content:encoded -> encoded) to prevent 'unbound prefix' parse errors."""
    return re.sub(r"</?([a-zA-Z0-9_-]+):", lambda m: "</" if m.group(0).startswith("</") else "<", xml_str)

def clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    # Normalize whitespaces & unescape HTML entities
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def fetch_from_rss() -> List[Dict[str, Any]]:
    """Primary ingestion: Fetches posts from WordPress RSS feed (bypasses WAF blocks)."""
    try:
        req = urllib.request.Request(RSS_FEED_URL, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
            clean_xml = clean_xml_namespaces(raw_xml)
            root = ET.fromstring(clean_xml)
            posts = []
            for item in root.findall(".//item"):
                guid_elem = item.find("guid")
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else ""
                
                title_elem = item.find("title")
                title = clean_text(title_elem.text) if title_elem is not None and title_elem.text else ""
                
                link_elem = item.find("link")
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                
                content_elem = item.find("encoded")
                content = content_elem.text if content_elem is not None and content_elem.text else ""
                
                desc_elem = item.find("description")
                desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                
                excerpt = clean_text(desc if desc else content)[:350]
                
                categories = []
                for cat in item.findall("category"):
                    if cat.text:
                        categories.append(clean_text(cat.text))

                # Use guid or link as unique ID
                post_id = guid if guid else link
                if title and link:
                    posts.append({
                        "id": post_id,
                        "title": title,
                        "link": link,
                        "excerpt": excerpt,
                        "content": content,
                        "categories": categories,
                        "source": "rss"
                    })
            return posts
    except Exception as e:
        print(f"[!] Primary RSS ingestion encountered: {e}")
        return []

def fetch_from_wp_api() -> List[Dict[str, Any]]:
    """Secondary fallback: Fetches posts via WordPress REST API."""
    try:
        req = urllib.request.Request(WP_POSTS_API, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            posts = []
            for item in data:
                post_id = str(item.get("id"))
                title = clean_text(item.get("title", {}).get("rendered", ""))
                link = item.get("link", "").strip()
                excerpt = clean_text(item.get("excerpt", {}).get("rendered", ""))
                if title and link:
                    posts.append({
                        "id": f"wp_{post_id}",
                        "title": title,
                        "link": link,
                        "excerpt": excerpt[:350],
                        "content": "",
                        "categories": [],
                        "source": "wp_api"
                    })
            return posts
    except Exception as e:
        print(f"[!] Fallback WP API ingestion encountered: {e}")
        return []

def fetch_latest_posts() -> List[Dict[str, Any]]:
    """Multi-tiered fetch: RSS primary, WP REST API secondary fallback."""
    posts = fetch_from_rss()
    if posts:
        print(f"[OK] Ingested {len(posts)} publications via RSS Feed.")
        return posts
    
    print("[!] RSS feed unavailable or empty. Engaging WordPress REST API fallback...")
    posts = fetch_from_wp_api()
    if posts:
        print(f"[OK] Ingested {len(posts)} publications via WP REST API.")
        return posts
        
    print("[!] All ingestion sources returned 0 publications.")
    return []

def build_bluesky_facets(text: str, link: str, tags: List[str]) -> List[dict]:
    """Computes exact UTF-8 byte offsets for clickable links and hashtags in Bluesky AT Protocol."""
    facets = []
    text_bytes = text.encode("utf-8")
    
    # 1. Link facet
    link_idx = text.find(link)
    if link_idx != -1:
        byte_start = len(text[:link_idx].encode("utf-8"))
        byte_end = byte_start + len(link.encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{"$type": "app.bsky.feed.post#link", "uri": link}]
        })

    # 2. Tag facets
    for tag in tags:
        clean_tag = tag.lstrip("#")
        tag_str = f"#{clean_tag}"
        for match in re.finditer(re.escape(tag_str), text):
            start_char = match.start()
            end_char = match.end()
            byte_start = len(text[:start_char].encode("utf-8"))
            byte_end = len(text[:end_char].encode("utf-8"))
            facets.append({
                "index": {"byteStart": byte_start, "byteEnd": byte_end},
                "features": [{"$type": "app.bsky.feed.post#tag", "tag": clean_tag}]
            })
            
    return facets

def format_social_copy(post: dict, platform: str) -> Tuple[str, str, List[str]]:
    """
    Constructs high-conversion funnel copy with topic-tailored tags,
    engaging hook, dynamic CTA, and platform-specific UTM link.
    """
    title = post["title"]
    base_link = post["link"]
    excerpt = post.get("excerpt", "")
    categories = post.get("categories", [])
    
    topic, tags, hook, cta = classify_content(title, excerpt, categories)
    utm_link = build_utm_link(base_link, platform)
    
    tag_line = " ".join(tags)
    
    if platform == "bluesky":
        # Bluesky has a strict 300 character limit.
        # Structure: Hook \n Title \n\n CTA \n utm_link \n\n tag_line
        fixed_part = f"{hook}\n\"{title}\"\n\n{cta}\n{utm_link}\n\n{tag_line}"
        
        # If over 295 chars, use shorter format without quotation/hook redundancy
        if len(fixed_part) > 295:
            compact_cta = "Read full article:"
            fixed_part = f"\"{title}\"\n\n{compact_cta}\n{utm_link}\n\n{tag_line}"
            
        if len(fixed_part) > 295:
            # Further compact title if title itself is extremely long
            allowed_title_len = 295 - len(f"\n\n{utm_link}\n\n{tag_line}") - 10
            truncated_title = title[:allowed_title_len].rstrip() + "..."
            fixed_part = f"{truncated_title}\n\n{utm_link}\n\n{tag_line}"
            
        return fixed_part, utm_link, tags
        
    elif platform == "mastodon":
        # Mastodon allows 500 characters. We can include a compelling excerpt!
        clean_excerpt = excerpt.replace("\n", " ").strip()
        if len(clean_excerpt) > 140:
            clean_excerpt = clean_excerpt[:137].rstrip() + "..."
            
        if clean_excerpt:
            copy = f"{hook}\n\n\"{title}\"\n\n{clean_excerpt}\n\n{cta}\n{utm_link}\n\n{tag_line}"
        else:
            copy = f"{hook}\n\n\"{title}\"\n\n{cta}\n{utm_link}\n\n{tag_line}"
            
        if len(copy) > 490:
            copy = f"{hook}\n\n\"{title}\"\n\n{cta}\n{utm_link}\n\n{tag_line}"
            
        return copy, utm_link, tags

    else:
        # Generic copy for Webhooks / other channels
        copy = f"{hook}\n\n**{title}**\n\n{excerpt[:200]}\n\n{cta} {utm_link}\n\n{tag_line}"
        return copy, utm_link, tags

def post_to_bluesky(identifier: str, password: str, text: str, link: str, title: str, description: str, tags: List[str]) -> bool:
    """Publishes a rich record to Bluesky using the AT Protocol with rich external embed cards and facets."""
    if not identifier or not password:
        return False
        
    try:
        # 1. Authenticate & Create Session
        auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
        auth_payload = json.dumps({"identifier": identifier, "password": password}).encode("utf-8")
        auth_req = urllib.request.Request(auth_url, data=auth_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(auth_req, timeout=15) as resp:
            session = json.loads(resp.read().decode("utf-8"))
            access_jwt = session.get("accessJwt")
            did = session.get("did")
            
        if not access_jwt or not did:
            print("[!] Bluesky auth response missing JWT or DID")
            return False

        # 2. Build facets for clickable link and hashtags
        facets = build_bluesky_facets(text, link, tags)

        # 3. Build post record with external link embed card
        record_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        record_content: Dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "facets": facets,
            "createdAt": now_iso,
            "embed": {
                "$type": "app.bsky.embed.external",
                "external": {
                    "uri": link,
                    "title": title[:200],
                    "description": (description or title)[:280]
                }
            }
        }
        
        record_payload = {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record_content
        }
        
        req = urllib.request.Request(
            record_url,
            data=json.dumps(record_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_jwt}"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Successfully posted to Bluesky: HTTP {resp.getcode()}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[!] Bluesky HTTP Error {e.code}: {err_body}")
        return False
    except Exception as e:
        print(f"[!] Bluesky posting failed: {e}")
        return False

def post_to_mastodon(instance_url: str, access_token: str, text: str, idempotency_key: str = "") -> bool:
    """Publishes status to Mastodon instance using ActivityPub REST API."""
    if not instance_url or not access_token:
        return False
        
    base_instance = normalize_mastodon_url(instance_url)
    status_url = f"{base_instance}/api/v1/statuses"
    
    payload = {
        "status": text,
        "visibility": "public",
        "language": "en"
    }
    
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "AviPereraSocialBroadcaster/2.0"
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
        
    try:
        req = urllib.request.Request(
            status_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            toot_url = res_data.get("url", res_data.get("uri", ""))
            print(f"[OK] Successfully posted to Mastodon: HTTP {resp.getcode()} -> {toot_url}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[!] Mastodon HTTP Error {e.code}: {err_body}")
        return False
    except Exception as e:
        print(f"[!] Mastodon posting failed: {e}")
        return False

def post_to_webhook(webhook_url: str, title: str, link: str, excerpt: str, tags: List[str]) -> bool:
    """Dispatches embed to Discord / Slack webhook."""
    if not webhook_url:
        return False
        
    payload = {
        "content": f"📰 **New Research Publication from Avi Perera**\n{' '.join(tags)}",
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

def main() -> int:
    print("=== Autonomous Social Broadcast Engine (8-Hour Link Syndicator) ===")
    state = load_state()
    posts = fetch_latest_posts()
    print(f"Retrieved {len(posts)} recent publications from aviperera.com")

    # Read credentials from environment
    bsky_user = os.getenv("BSKY_IDENTIFIER", "").strip()
    bsky_pass = os.getenv("BSKY_APP_PASSWORD", "").strip()
    masto_instance = os.getenv("MASTODON_INSTANCE_URL", "https://mastodon.social").strip()
    masto_token = os.getenv("MASTODON_ACCESS_TOKEN", "").strip()
    webhook_url = os.getenv("COMMUNITY_WEBHOOK_URL", "").strip()

    force_dry_run = "--dry-run" in sys.argv
    has_bluesky = bool(bsky_user and bsky_pass)
    has_mastodon = bool(masto_token)
    has_webhook = bool(webhook_url)

    dry_run = force_dry_run or not (has_bluesky or has_mastodon or has_webhook)

    if dry_run:
        print("[!] Execution running in PREVIEW / DRY-RUN mode.")
        if not (has_bluesky or has_mastodon):
            print("    Reason: Missing BSKY_* or MASTODON_* secrets. Set repository secrets to enable live broadcast.")

    # Find posts needing syndication (filtering on per-platform state)
    unbroadcasted = []
    for p in posts:
        pid = p["id"]
        history = state.get("syndicated", {}).get(pid, {})
        platforms = history.get("platforms", {})
        
        needs_bsky = has_bluesky and not platforms.get("bluesky", False)
        needs_masto = has_mastodon and not platforms.get("mastodon", False)
        needs_hook = has_webhook and not platforms.get("webhook", False)
        
        # If in dry-run, consider unbroadcasted if pid not seen yet
        if dry_run and pid not in state["syndicated"]:
            unbroadcasted.append((p, True, True, True))
        elif needs_bsky or needs_masto or needs_hook:
            unbroadcasted.append((p, needs_bsky, needs_masto, needs_hook))

    print(f"Publications pending syndication: {len(unbroadcasted)}")

    processed_this_run = []
    
    # Process at most 1 new publication per 8-hour run to maintain organic spacing
    for item in unbroadcasted[:1]:
        post, do_bsky, do_masto, do_hook = item
        title = post["title"]
        excerpt = post.get("excerpt", "")
        pid = post["id"]
        
        print(f"\nProcessing publication: {title} (ID: {pid})")
        
        bsky_text, bsky_link, bsky_tags = format_social_copy(post, "bluesky")
        masto_text, masto_link, masto_tags = format_social_copy(post, "mastodon")
        
        item_summary = {
            "id": pid,
            "title": title,
            "link": post["link"],
            "bluesky_status": "Skipped",
            "mastodon_status": "Skipped"
        }

        if dry_run:
            print("[DRY-RUN PREVIEW] Bluesky Copy:")
            print(f"----------------------------------------\n{bsky_text}\n(Length: {len(bsky_text)} chars)\n----------------------------------------")
            print("[DRY-RUN PREVIEW] Mastodon Copy:")
            print(f"----------------------------------------\n{masto_text}\n(Length: {len(masto_text)} chars)\n----------------------------------------")
            item_summary["bluesky_status"] = "Dry-Run Preview"
            item_summary["mastodon_status"] = "Dry-Run Preview"
            processed_this_run.append(item_summary)
            continue

        # Live Broadcasting with per-platform isolation
        if pid not in state["syndicated"]:
            state["syndicated"][pid] = {
                "title": title,
                "link": post["link"],
                "platforms": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        plat_state = state["syndicated"][pid].setdefault("platforms", {})

        # 1. Broadcast to Bluesky
        if do_bsky:
            print("Broadcasting to Bluesky...")
            success = post_to_bluesky(
                identifier=bsky_user,
                password=bsky_pass,
                text=bsky_text,
                link=bsky_link,
                title=title,
                description=excerpt,
                tags=bsky_tags
            )
            plat_state["bluesky"] = success
            item_summary["bluesky_status"] = "Live Broadcast" if success else "Failed"

        # 2. Broadcast to Mastodon
        if do_masto:
            print(f"Broadcasting to Mastodon ({masto_instance})...")
            idempotency_key = hashlib.sha256(f"{pid}:{masto_link}".encode("utf-8")).hexdigest()
            success = post_to_mastodon(
                instance_url=masto_instance,
                access_token=masto_token,
                text=masto_text,
                idempotency_key=idempotency_key
            )
            plat_state["mastodon"] = success
            item_summary["mastodon_status"] = "Live Broadcast" if success else "Failed"

        # 3. Optional Webhook
        if do_hook:
            post_to_webhook(webhook_url, title, post["link"], excerpt, bsky_tags)
            plat_state["webhook"] = True

        processed_this_run.append(item_summary)

    if not dry_run and processed_this_run:
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        print("[OK] State file successfully saved.")

    write_step_summary(processed_this_run, dry_run=dry_run, has_bsky=has_bluesky, has_masto=has_mastodon)
    return 0

def write_step_summary(items: list, dry_run: bool, has_bsky: bool, has_masto: bool):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
        
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("## 📢 Social Broadcast & Syndication Engine\n\n")
        mode_text = "🟡 **DRY-RUN / SIMULATION MODE**" if dry_run else "🟢 **LIVE BROADCAST EXECUTION**"
        f.write(f"**Execution Mode:** {mode_text}\n\n")
        
        f.write("### Credential Health Check\n")
        f.write(f"- **Bluesky (`BSKY_IDENTIFIER` & `BSKY_APP_PASSWORD`):** {'✅ Configured' if has_bsky else '❌ Missing or empty'}\n")
        f.write(f"- **Mastodon (`MASTODON_ACCESS_TOKEN`):** {'✅ Configured' if has_masto else '❌ Missing or empty'}\n\n")

        if not items:
            f.write("✅ All latest publications are already syndicated. Zero pending items.\n")
            return
            
        f.write(f"### Processed Publications ({len(items)} item):\n\n")
        f.write("| ID | Title | Bluesky | Mastodon |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for it in items:
            f.write(f"| `{it['id']}` | [{it['title']}]({it['link']}) | `{it['bluesky_status']}` | `{it['mastodon_status']}` |\n")

if __name__ == "__main__":
    sys.exit(main())
