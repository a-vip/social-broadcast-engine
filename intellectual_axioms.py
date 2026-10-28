#!/usr/bin/env python3
"""
intellectual_axioms.py
Curated high-level philosophical insights, strategic paradoxes,
and governance axioms reflecting the research of Avi Perera.
"""

from typing import Dict, List

# High-level intellectual statements, strategic paradoxes, and foundational axioms
CURATED_AXIOMS: List[Dict[str, str]] = [
    {
        "category": "ai_governance",
        "text": "Sovereignty in the 21st century is no longer defined strictly by territorial borders, but by the autonomy of a nation's compute stack and algorithmic governance.",
        "tags": "#AIGovernance #Sovereignty #TechPolicy #Geopolitics"
    },
    {
        "category": "defense_laws",
        "text": "When autonomous systems compress kinetic decision cycles from hours into milliseconds, human deliberation ceases to be an operational virtue and becomes a tactical vulnerability. This is the central moral crisis of modern defense.",
        "tags": "#AutonomousWeapons #LAWS #MilitaryAI #DefenseTech"
    },
    {
        "category": "international_law",
        "text": "The fundamental dilemma of international humanitarian law in algorithmic warfare: accountability cannot be distributed to software, yet human command chains increasingly serve as rubber stamps for machine outputs.",
        "tags": "#InternationalLaw #IHL #GenevaConventions #AIEthics"
    },
    {
        "category": "ai_governance",
        "text": "Regulation naturally advances at the speed of judicial precedent, while artificial intelligence advances at the speed of compute. Bridging this institutional latency is the defining challenge of our era.",
        "tags": "#AIGovernance #Institutions #TechRegulation #LawTech"
    },
    {
        "category": "defense_laws",
        "text": "Loitering munitions and autonomous swarms do not merely change tactical engagements; they dismantle the traditional economic doctrine of air defense by making precision mass cheaper than precision interception.",
        "tags": "#AutonomousWeapons #DefenseTech #MilitaryStrategy #SecurityStudies"
    },
    {
        "category": "philosophy_tech",
        "text": "We often mistake computational velocity for cognitive depth. An algorithm can optimize within defined boundaries infinitely faster than a human, but it cannot conceptualize the moral necessity of the boundary itself.",
        "tags": "#PhilosophyOfTech #AIEthics #ArtificialIntelligence #Epistemology"
    },
    {
        "category": "international_law",
        "text": "If autonomous weapons operate below the threshold of meaningful human control, the doctrine of state responsibility must shift from intent-based fault to strict systemic liability under customary international law.",
        "tags": "#InternationalLaw #IHL #LegalTheory #AutonomousSystems"
    },
    {
        "category": "geopolitics_compute",
        "text": "Access to advanced semiconductor fabrication is the new maritime chokepoint. The geopolitical struggles of the next fifty years will look less like territorial conquest and more like silicon containment.",
        "tags": "#Geopolitics #Semiconductors #NationalSecurity #TechPolicy"
    },
    {
        "category": "ai_governance",
        "text": "Alignment is not merely a technical benchmark between a prompt and a response; it is an institutional covenant between autonomous intelligence and human constitutional democratic order.",
        "tags": "#AISafety #AIGovernance #ConstitutionalAI #PublicPolicy"
    },
    {
        "category": "defense_laws",
        "text": "The greatest escalation hazard in algorithmic conflict is not malice, but mutual automated reaction: autonomous systems triggering automated countermeasures before human leaders recognize the threshold has been crossed.",
        "tags": "#AutonomousWeapons #LAWS #EscalationControl #GlobalSecurity"
    },
    {
        "category": "philosophy_tech",
        "text": "True technological sovereignty is not autarky—it is the institutional capacity to comprehend, interrogate, and veto the algorithmic decisions that shape public life.",
        "tags": "#Sovereignty #DigitalRights #AIGovernance #PublicLaw"
    },
    {
        "category": "strategy_productivity",
        "text": "In an era of hyper-abundant algorithmic synthesis, original research value accrues almost entirely to deep synthesis, primary source verification, and independent epistemic courage.",
        "tags": "#AcademicResearch #DeepWork #Epistemology #KnowledgeArchitecture"
    }
]

# Keywords that indicate profound analytical depth in article text
DEPTH_INDICATORS = [
    "sovereignty", "sovereign", "dilemma", "paradox", "liability", "doctrine",
    "threshold", "governance", "framework", "precedent", "asymmetry", "jurisdiction",
    "accountability", "autonomy", "autonomous", "ethical", "velocity", "institutional", "moral",
    "compute", "power", "treaty", "compliance", "systemic", "escalation", "consequence",
    "imperative", "normative", "deliberation", "kinetic", "strategic", "vulnerability"
]

# Words that indicate purely descriptive, logistical, or factual boilerplate (to be skipped)
SHALLOW_INDICATORS = [
    "built by", "manufactured by", "founded in", "headquartered", "specs include",
    "available for", "weighs approximately", "released on", "dimensions are",
    "battery life", "click here", "read more", "subscribe", "cookie", "copyright",
    "affiliate link", "disclaimer", "download the app"
]

def score_sentence_depth(sentence: str) -> int:
    """Scores a sentence based on philosophical, legal, and strategic resonance."""
    low = sentence.lower()
    
    # Check for shallow disqualifiers
    if any(shallow in low for shallow in SHALLOW_INDICATORS):
        return -50
        
    score = 0
    words = low.split()
    for word in words:
        clean_w = word.strip(".,;:\"'()?!")
        if clean_w in DEPTH_INDICATORS:
            score += 10
            
    # Bonus for thesis-like structure (e.g. contains 'must', 'cannot', 'demands', 'requires')
    if any(modal in low for modal in [" must ", " cannot ", " demands ", " requires ", " fundamentally ", " precisely because "]):
        score += 15

    # Penalize overly short or overly long sentences
    length = len(sentence)
    if length < 80 or length > 220:
        score -= 20

    return score
