#!/usr/bin/env python3
"""
content_classifier.py
Intelligent topic classification, dynamic hashtag selection,
and context-aware Call to Action (CTA) generator for aviperera.com.
"""

import re
from typing import Dict, List, Tuple

# Pre-defined domain profiles with tailored hooks, CTAs, and hashtags
TOPIC_PROFILES = {
    "defense_laws": {
        "keywords": [
            "weapon", "weapons", "laws", "autonomous weapon", "drone", "switchblade",
            "military", "warfare", "defense", "security", "missile", "combat", "strikes",
            "lethal", "battlefield", "pentagon", "loitering"
        ],
        "primary_tags": ["#AutonomousWeapons", "#LAWS", "#DefenseTech", "#MilitaryAI"],
        "hooks": [
            "Critical analysis on autonomous systems & military defense:",
            "Operational breakdown of emerging defense capabilities:",
            "New dossier on autonomous weapon systems & international security:"
        ],
        "ctas": [
            "Explore the full operational breakdown & legal assessment:",
            "Read the complete defense dossier & technical specs:",
            "Examine the full strategic analysis:"
        ]
    },
    "ai_governance": {
        "keywords": [
            "ai", "artificial intelligence", "governance", "ethics", "safety", "alignment",
            "llm", "neural", "deep learning", "agent", "algorithm", "algorithms",
            "model", "machine learning", "gpt", "frontier", "sovereign", "superintelligence"
        ],
        "primary_tags": ["#AIGovernance", "#AISafety", "#AIEthics", "#ArtificialIntelligence"],
        "hooks": [
            "Key insights from my latest AI governance research:",
            "New analysis on sovereign algorithms & AI safety frameworks:",
            "Critical examination of frontier AI policy & institutional design:"
        ],
        "ctas": [
            "Read the complete policy analysis & institutional framework:",
            "Explore the full research paper on aviperera.com:",
            "Read the in-depth governance breakdown:"
        ]
    },
    "international_law": {
        "keywords": [
            "law", "legal", "ihl", "treaty", "geneva", "sovereignty", "united nations",
            "un", "regulation", "framework", "jurisdiction", "treaties", "customary",
            "humanitarian", "court", "liability", "compliance", "convention"
        ],
        "primary_tags": ["#InternationalLaw", "#IHL", "#LegalFramework", "#GlobalGovernance"],
        "hooks": [
            "In-depth examination of international legal frameworks:",
            "Evaluating state responsibility under international humanitarian law:",
            "New legal analysis on sovereignty and treaty compliance:"
        ],
        "ctas": [
            "Read the complete legal breakdown & treaty analysis:",
            "Explore the full jurisprudential assessment:",
            "Access the complete legal analysis on aviperera.com:"
        ]
    },
    "software_tech": {
        "keywords": [
            "python", "javascript", "code", "api", "software", "dashboard", "architecture",
            "database", "engineering", "github", "server", "deploy", "fullstack", "frontend",
            "backend", "react", "vue", "docker", "pipeline", "performance", "web", "html"
        ],
        "primary_tags": ["#SoftwareEngineering", "#TechArchitecture", "#OpenSource", "#DevCommunity"],
        "hooks": [
            "Technical architecture breakdown & implementation details:",
            "Engineering walkthrough and system design patterns:",
            "Deep dive into software architecture and performance:"
        ],
        "ctas": [
            "Explore the technical architecture & implementation:",
            "Read the full engineering walkthrough on aviperera.com:",
            "Check out the complete system design:"
        ]
    },
    "productivity_strategy": {
        "keywords": [
            "productivity", "workflow", "obsidian", "note", "writing", "deep work",
            "strategy", "academic", "researcher", "habits", "system", "archive", "knowledge"
        ],
        "primary_tags": ["#AcademicResearch", "#DeepWork", "#Productivity", "#KnowledgeManagement"],
        "hooks": [
            "Reflections on research workflows & analytical productivity:",
            "Frameworks for sustained deep work and intellectual output:",
            "New essay on knowledge architecture and research systems:"
        ],
        "ctas": [
            "Read the full essay and actionable takeaways:",
            "Explore the complete workflow system on aviperera.com:",
            "Read the full methodology here:"
        ]
    }
}

DEFAULT_PROFILE = {
    "primary_tags": ["#AIGovernance", "#TechPolicy", "#InternationalRelations"],
    "hooks": [
        "New publication on aviperera.com:",
        "Fresh analysis on technology and governance:"
    ],
    "ctas": [
        "Read the full article on aviperera.com:",
        "Explore the complete publication:"
    ]
}

def classify_content(title: str, content: str = "", categories: List[str] = None) -> Tuple[str, List[str], str, str]:
    """
    Evaluates text against topic domains and returns:
    (topic_name, hashtags, hook, cta)
    """
    if categories is None:
        categories = []
        
    combined_text = f"{title} {' '.join(categories)} {content}".lower()
    
    scores: Dict[str, int] = {}
    
    for topic, config in TOPIC_PROFILES.items():
        score = 0
        for kw in config["keywords"]:
            # Word boundary matching to prevent partial substring false positives
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = len(re.findall(pattern, combined_text))
            score += matches * (3 if kw in title.lower() else 1)
        scores[topic] = score

    best_topic = max(scores, key=scores.get) if scores else None
    
    if best_topic and scores[best_topic] > 0:
        profile = TOPIC_PROFILES[best_topic]
        # Deterministically select hook & cta based on post title hash for variety without randomness
        selector = abs(hash(title))
        hook = profile["hooks"][selector % len(profile["hooks"])]
        cta = profile["ctas"][selector % len(profile["ctas"])]
        return best_topic, profile["primary_tags"], hook, cta
    
    selector = abs(hash(title))
    return (
        "general",
        DEFAULT_PROFILE["primary_tags"],
        DEFAULT_PROFILE["hooks"][selector % len(DEFAULT_PROFILE["hooks"])],
        DEFAULT_PROFILE["ctas"][selector % len(DEFAULT_PROFILE["ctas"])]
    )

def build_utm_link(base_url: str, platform: str) -> str:
    """Appends UTM campaign parameters for attribution in web analytics."""
    clean_url = base_url.split("?")[0].rstrip("/") + "/"
    return f"{clean_url}?utm_source={platform}&utm_medium=social&utm_campaign=syndication"
