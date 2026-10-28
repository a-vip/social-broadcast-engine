#!/usr/bin/env python3
"""
organic_broadcaster.py
Autonomous Organic Thought-Leadership & Snippet Broadcaster for aviperera.com.
Selects key quotes, insights, and philosophical/policy reflections from publications
and broadcasts pure organic text posts (no direct links) to Bluesky and Mastodon.
This builds high organic engagement and algorithmic reach across feeds.
"""

import os
import sys
import json
import re
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from content_classifier import classify_content
from broadcast_engine import (
    clean_text,
    fetch_from_rss,
    fetch_from_wp_api,
    build_bluesky_facets,
    post_to_mastodon
)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ORGANIC_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "organic_history.json")

def load_organic_state() -> dict:
    if os.path.exists(ORGANIC_STATE_FILE):
        try:
            with open(ORGANIC_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "posted_snippets" not in data:
                    data["posted_snippets"] = {}
                return data
        except Exception as e:
            print(f"[!] Warning reading organic state ({e}).")
    return {"posted_snippets": {}, "last_run": None}

def save_organic_state(state: dict):
    os.makedirs(os.path.dirname(ORGANIC_STATE_FILE), exist_ok=True)
    with open(ORGANIC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def extract_meaningful_snippets(content: str, title: str) -> List[str]:
    """Extracts coherent, high-value insight sentences from publication text."""
    text = clean_text(content)
    if not text:
        return []

    # Split by sentence terminators
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    candidate_snippets = []

    for s in raw_sentences:
        s_clean = s.strip().strip("\"'“”‘’")
        length = len(s_clean)
        # We want punchy, insightful sentences (80 to 200 characters)
        if 75 <= length <= 210:
            # Exclude navigational or metadata text
            low = s_clean.lower()
            if any(skip in low for skip in ["click here", "read more", "subscribe", "cookie", "http", "published", "copyright"]):
                continue
            # Ensure sentence contains substantive punctuation and words
            if s_clean[0].isupper() and (s_clean.endswith(".") or s_clean.endswith("!") or s_clean.endswith("?")):
                candidate_snippets.append(s_clean)

    # If no long sentence matched, craft an insight summary from the title & excerpt
    if not candidate_snippets and text:
        short_summary = text[:180].rsplit(" ", 1)[0] + "."
        candidate_snippets.append(short_summary)

    return candidate_snippets

def format_organic_post(snippet: str, title: str, categories: List[str]) -> Tuple[str, List[str]]:
    """Formats an organic quote post with topic-specific hashtags and attribution."""
    topic, tags, _, _ = classify_content(title, snippet, categories)
    tag_line = " ".join(tags[:3]) # 2-3 most relevant tags
    
    # Structure:
    # "Quote snippet here."
    # 
    # — From the research on [Topic/Title]
    # 
    # #Tags
    attribution_topic = {
        "defense_laws": "Autonomous Weapon Systems & Defense Tech",
        "ai_governance": "AI Governance & Sovereign Algorithms",
        "international_law": "International Humanitarian Law & Treaty Frameworks",
        "software_tech": "Software Architecture & Systems Engineering",
        "productivity_strategy": "Research Strategy & Analytical Frameworks"
    }.get(topic, "Sovereign Systems & Global Tech Policy")

    copy = f"\"{snippet}\"\n\n— Insights on {attribution_topic}\n\n{tag_line}"
    
    # Bluesky character limit safety check (300 chars max)
    if len(copy) > 295:
        # Compact attribution
        copy = f"\"{snippet}\"\n\n— Avi Perera\n\n{tag_line}"
        
    if len(copy) > 295:
        allowed = 290 - len(f"\n\n— Avi Perera\n\n{tag_line}") - 5
        truncated = snippet[:allowed].rstrip() + "..."
        copy = f"\"{truncated}\"\n\n— Avi Perera\n\n{tag_line}"

    return copy, tags[:3]

def post_organic_to_bluesky(identifier: str, password: str, text: str, tags: List[str]) -> bool:
    """Posts pure organic text to Bluesky with hashtag facets (no external link embed)."""
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
            return False

        # 2. Build tag facets
        facets = build_bluesky_facets(text, link="", tags=tags)

        # 3. Post pure organic record (no external embed)
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
            print(f"[OK] Successfully posted organic insight to Bluesky: HTTP {resp.getcode()}")
            return True
    except Exception as e:
        print(f"[!] Bluesky organic post failed: {e}")
        return False

def main() -> int:
    print("=== Autonomous Organic Insights & Snippet Broadcaster ===")
    state = load_organic_state()
    
    # Ingest publications
    posts = fetch_from_rss()
    if not posts:
        posts = fetch_from_wp_api()
        
    if not posts:
        print("[!] No publications available to extract snippets from.")
        return 0

    bsky_user = os.getenv("BSKY_IDENTIFIER", "").strip()
    bsky_pass = os.getenv("BSKY_APP_PASSWORD", "").strip()
    masto_instance = os.getenv("MASTODON_INSTANCE_URL", "https://mastodon.social").strip()
    masto_token = os.getenv("MASTODON_ACCESS_TOKEN", "").strip()

    force_dry_run = "--dry-run" in sys.argv
    has_bluesky = bool(bsky_user and bsky_pass)
    has_mastodon = bool(masto_token)
    dry_run = force_dry_run or not (has_bluesky or has_mastodon)

    if dry_run:
        print("[!] Running in PREVIEW / DRY-RUN mode.")

    # Find candidate snippet from articles
    selected_snippet = None
    selected_post = None

    for post in posts:
        content_source = post.get("content") or post.get("excerpt") or ""
        snippets = extract_meaningful_snippets(content_source, post["title"])
        for s in snippets:
            s_hash = hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
            if s_hash not in state.get("posted_snippets", {}):
                selected_snippet = s
                selected_post = post
                snippet_key = s_hash
                break
        if selected_snippet:
            break

    if not selected_snippet:
        print("[*] All current snippets have been posted previously. Archive exhausted.")
        return 0

    organic_text, tags = format_organic_post(
        selected_snippet,
        selected_post["title"],
        selected_post.get("categories", [])
    )

    print(f"\nSelected Insight from: '{selected_post['title']}':")
    print("--------------------------------------------------")
    print(organic_text)
    print(f"(Length: {len(organic_text)} chars)")
    print("--------------------------------------------------")

    if dry_run:
        print("[DRY-RUN] Insight post validated successfully.")
        return 0

    # Live Broadcast
    success_any = False
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if has_bluesky:
        if post_organic_to_bluesky(bsky_user, bsky_pass, organic_text, tags):
            success_any = True

    if has_mastodon:
        idempotency_key = hashlib.sha256(organic_text.encode("utf-8")).hexdigest()
        if post_to_mastodon(masto_instance, masto_token, organic_text, idempotency_key=idempotency_key):
            success_any = True

    if success_any:
        state["posted_snippets"][snippet_key] = {
            "snippet": selected_snippet[:100],
            "title": selected_post["title"],
            "timestamp": now_iso
        }
        state["last_run"] = now_iso
        save_organic_state(state)
        print("[OK] Organic state updated.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
