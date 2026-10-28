#!/usr/bin/env python3
"""
organic_broadcaster.py
Autonomous Organic Thought-Leadership & Philosophical Insights Broadcaster for aviperera.com.
Selects high-level philosophical axioms, strategic paradoxes, and deep article theses
and broadcasts pure organic text posts (no links) to Bluesky and Mastodon.
Builds intellectual authority and algorithmic feed reach without link fatigue.
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from content_classifier import classify_content
from intellectual_axioms import CURATED_AXIOMS, score_sentence_depth
from broadcast_engine import (
    clean_text,
    fetch_latest_posts,
    build_bluesky_facets,
    post_to_mastodon,
    normalize_mastodon_url
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

def extract_high_depth_snippets(content: str, title: str) -> List[Tuple[str, int]]:
    """Extracts and scores sentences based on analytical and philosophical depth."""
    text = clean_text(content)
    if not text:
        return []

    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    candidates = []

    for s in raw_sentences:
        s_clean = s.strip().strip("\"'“”‘’")
        if not s_clean or not s_clean[0].isupper():
            continue
        depth_score = score_sentence_depth(s_clean)
        # Require a positive depth score (filtering out factual specs and shallow definitions)
        if depth_score >= 15:
            candidates.append((s_clean, depth_score))

    # Sort candidates by highest depth score descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates

def format_curated_axiom(axiom: dict) -> Tuple[str, List[str]]:
    """Formats a curated philosophical or strategic axiom."""
    text = axiom["text"].strip()
    tags_str = axiom.get("tags", "#AIGovernance #InternationalLaw")
    tags = [t.strip() for t in tags_str.split() if t.startswith("#")]
    
    copy = f"{text}\n\n{tags_str}"
    if len(copy) > 295:
        # Compact tags if needed to stay under Bluesky 300-char limit
        compact_tags = " ".join(tags[:3])
        copy = f"{text}\n\n{compact_tags}"

    return copy, tags

def format_article_thesis(snippet: str, title: str, categories: List[str]) -> Tuple[str, List[str]]:
    """Formats an organic thesis statement extracted from an article."""
    topic, tags, _, _ = classify_content(title, snippet, categories)
    tag_line = " ".join(tags[:3])
    
    attribution_topic = {
        "defense_laws": "Autonomous Weapons & Defense Systems",
        "ai_governance": "AI Governance & Sovereign Algorithms",
        "international_law": "International Law & Treaty Frameworks",
        "software_tech": "Software Architecture & Systems Design",
        "productivity_strategy": "Research Methodology & Strategic Thought"
    }.get(topic, "Sovereign Systems & Global Tech Policy")

    copy = f"\"{snippet}\"\n\n— Reflections on {attribution_topic}\n\n{tag_line}"
    
    if len(copy) > 295:
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
        auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
        auth_payload = json.dumps({"identifier": identifier, "password": password}).encode("utf-8")
        auth_req = urllib.request.Request(auth_url, data=auth_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(auth_req, timeout=15) as resp:
            session = json.loads(resp.read().decode("utf-8"))
            access_jwt = session.get("accessJwt")
            did = session.get("did")
            
        if not access_jwt or not did:
            return False

        facets = build_bluesky_facets(text, link="", tags=tags)

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

def select_next_organic_post(posts: list, state: dict) -> Tuple[Optional[str], Optional[List[str]], Optional[str], str]:
    """
    Alternates between deep thesis sentences from articles and curated philosophical axioms.
    Returns: (text, tags, key_hash, post_type)
    """
    posted = state.get("posted_snippets", {})
    
    # 1. Search recent articles for high-depth thesis sentences
    for post in posts:
        content_source = post.get("content") or post.get("excerpt") or ""
        candidates = extract_high_depth_snippets(content_source, post["title"])
        for snippet, score in candidates:
            s_hash = hashlib.sha256(snippet.encode("utf-8")).hexdigest()[:16]
            if s_hash not in posted:
                copy, tags = format_article_thesis(snippet, post["title"], post.get("categories", []))
                return copy, tags, s_hash, f"article_thesis (score {score})"

    # 2. Pull from Curated Intellectual & Philosophical Axioms pool
    for axiom in CURATED_AXIOMS:
        ax_hash = hashlib.sha256(axiom["text"].encode("utf-8")).hexdigest()[:16]
        if ax_hash not in posted:
            copy, tags = format_curated_axiom(axiom)
            return copy, tags, ax_hash, f"curated_axiom ({axiom['category']})"

    # 3. If all posted, recycle oldest curated axiom
    fallback_axiom = CURATED_AXIOMS[abs(hash(str(state.get("last_run")))) % len(CURATED_AXIOMS)]
    copy, tags = format_curated_axiom(fallback_axiom)
    return copy, tags, hashlib.sha256(copy.encode("utf-8")).hexdigest()[:16], "recycled_axiom"

def main() -> int:
    print("=== Autonomous Organic Insights & Philosophical Broadcaster ===")
    state = load_organic_state()
    posts = fetch_latest_posts()

    bsky_user = os.getenv("BSKY_IDENTIFIER", "").strip()
    bsky_pass = os.getenv("BSKY_APP_PASSWORD", "").strip()
    masto_instance = normalize_mastodon_url(os.getenv("MASTODON_INSTANCE_URL", "https://mastodon.social"))
    masto_token = os.getenv("MASTODON_ACCESS_TOKEN", "").strip()

    force_dry_run = "--dry-run" in sys.argv
    has_bluesky = bool(bsky_user and bsky_pass)
    has_mastodon = bool(masto_token)
    dry_run = force_dry_run or not (has_bluesky or has_mastodon)

    if dry_run:
        print("[!] Running in PREVIEW / DRY-RUN mode.")

    organic_text, tags, item_key, post_type = select_next_organic_post(posts, state)

    if not organic_text:
        print("[!] No candidate insights available.")
        return 0

    print(f"\n[Generated Insight Type: {post_type}]")
    print("--------------------------------------------------")
    print(organic_text)
    print(f"(Length: {len(organic_text)} chars)")
    print("--------------------------------------------------")

    if dry_run:
        print("[DRY-RUN] Insight post validated successfully.")
        return 0

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
        state["posted_snippets"][item_key] = {
            "text": organic_text[:120],
            "type": post_type,
            "timestamp": now_iso
        }
        state["last_run"] = now_iso
        save_organic_state(state)
        print(f"[OK] Organic state updated ({post_type}).")

    return 0

if __name__ == "__main__":
    sys.exit(main())
