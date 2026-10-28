#!/usr/bin/env python3
"""
intellectual_axioms.py
Curated high-level philosophical insights, ethical frameworks,
and societal analysis reflecting the published writings and research of Avi Perera.
Focuses strictly on AI Ethics, Society, Legal Liability, Human Rights, and Governance.
"""

from typing import Dict, List

# Curated statements directly reflecting Avi Perera's research, essays, and published stances
CURATED_AXIOMS: List[Dict[str, str]] = [
    {
        "category": "ai_ethics_liability",
        "text": "The era of voluntary ethical guidelines for artificial intelligence is officially over. We have entered the era of strict enforcement, where software and autonomous systems are classified as products with non-negotiable legal liability.",
        "tags": "#AIEthics #ProductLiability #TechPolicy #AIAct"
    },
    {
        "category": "ai_governance",
        "text": "When Microsoft’s Tay chatbot generated hate speech within 24 hours of launch in 2016, it was treated as an experiment gone wrong. Today, that exact failure is a corporate liability and a breach of human rights compliance.",
        "tags": "#AIEthics #AlgorithmicBias #CorporateGovernance #TechLaw"
    },
    {
        "category": "international_law",
        "text": "Unlike trade rules that prioritize market safety, genuine AI governance must center on human rights, democracy, and the rule of law. If a system degrades human agency, technical optimization cannot redeem it.",
        "tags": "#HumanRights #RuleOfLaw #AIGovernance #CouncilOfEurope"
    },
    {
        "category": "institutional_governance",
        "text": "The defining institutional challenge of our generation is latency: regulation and jurisprudence advance at the pace of precedent, while compute and model capabilities advance exponentially.",
        "tags": "#AIGovernance #InstitutionalDesign #TechPolicy #PublicLaw"
    },
    {
        "category": "society_digital_dignity",
        "text": "We often mistake computational velocity for cognitive depth. An algorithmic model can optimize within boundaries infinitely faster than a human, but it cannot conceptualize the moral necessity of the boundary itself.",
        "tags": "#AIEthics #PhilosophyOfTech #Epistemology #HumanValues"
    },
    {
        "category": "ai_ethics_fairness",
        "text": "Algorithmic bias is rarely a technical bug; it is an evidentiary mirror of historical systemic disparities codified into training distributions. Correcting it requires structural intervention, not cosmetic re-weighting.",
        "tags": "#AIEthics #AlgorithmicFairness #DataJustice #SocietalImpact"
    },
    {
        "category": "sovereign_compute",
        "text": "Sovereignty in the 21st century is defined not merely by territorial borders, but by whether a society retains the democratic capacity to inspect, contest, and veto the algorithmic systems governing public life.",
        "tags": "#DigitalSovereignty #AIGovernance #DemocraticInstitutions #PublicPolicy"
    },
    {
        "category": "un_global_compact",
        "text": "Global AI governance requires an impartial scientific consensus comparable to the IPCC for climate. Without shared empirical risk benchmarks, geopolitical competition will inevitably drive regulatory race-to-the-bottom dynamics.",
        "tags": "#UN #GlobalGovernance #AISafety #TechDiplomacy"
    },
    {
        "category": "online_safety_verification",
        "text": "Combating generative synthetic deception and deepfakes requires moving beyond reactive detection toward statutory duties of care and cryptographic provenance at the point of creation.",
        "tags": "#OnlineSafety #Deepfakes #DigitalIntegrity #MediaPolicy"
    },
    {
        "category": "digital_economy_society",
        "text": "The rapid expansion of the digital knowledge economy frequently masks new asymmetries between capital-exporting hubs and host communities. Sustainable tech policy must account for local socioeconomic sovereignty.",
        "tags": "#DigitalEconomy #TechSociety #GlobalSouth #Sovereignty"
    },
    {
        "category": "research_epistemology",
        "text": "In an era of hyper-abundant synthetic text, genuine intellectual value accrues to primary source verification, rigorous cross-jurisdictional comparison, and independent epistemic critique.",
        "tags": "#AcademicResearch #CriticalThinking #Epistemology #HigherEd"
    },
    {
        "category": "ai_ethics_healthcare",
        "text": "When algorithmic systems are deployed in high-stakes domains like healthcare or credit, explainability is not an engineering luxury—it is a non-derogable procedural right.",
        "tags": "#AIEthics #ExplainableAI #HealthcareTech #FundamentalRights"
    }
]

# Keywords indicating deep philosophical, ethical, and societal reflection
DEPTH_INDICATORS = [
    "ethics", "ethical", "society", "societal", "governance", "sovereignty", "sovereign",
    "liability", "framework", "precedent", "jurisdiction", "accountability", "human rights",
    "democracy", "rule of law", "bias", "fairness", "transparency", "oversight", "dignity",
    "epistemology", "epistemic", "institutional", "compact", "convention", "verification",
    "normative", "deliberation", "imperative", "asymmetry", "disparities"
]

# Keywords indicating hardware, kinetic weapons, or shallow commercial specs to strictly deprioritize
SHALLOW_OR_WEAPONS_INDICATORS = [
    "missile", "drone specs", "strikes", "kill chain", "loitering munition",
    "ammunition", "battlefield drone", "switchblade", "unitree b2", "v-bat",
    "built by", "manufactured by", "founded in", "headquartered in", "specs include",
    "battery life", "click here", "read more", "subscribe", "cookie", "copyright",
    "affiliate link", "disclaimer", "dimensions are", "weighs approximately", "payload capacity"
]

def score_sentence_depth(sentence: str) -> int:
    """
    Scores a sentence prioritizing AI Ethics, Societal impact, and Legal frameworks,
    while penalizing kinetic weapon specs or shallow commercial boilerplate.
    """
    low = sentence.lower()
    
    # Penalize weapons and shallow specs
    if any(shallow in low for shallow in SHALLOW_OR_WEAPONS_INDICATORS):
        return -50
        
    score = 0
    words = low.split()
    for word in words:
        clean_w = word.strip(".,;:\"'()?!")
        if clean_w in DEPTH_INDICATORS:
            score += 12
            
    # Bonus for strong philosophical assertions
    if any(phrase in low for phrase in [
        " human rights", " rule of law", " strictly liable", " must be ",
        " fundamental ", " democratic ", " accountability ", " institutional ",
        " procedural right", " genuine "
    ]):
        score += 15

    # Penalize sentences outside the ideal readable social length (75 to 220 chars)
    length = len(sentence)
    if length < 75 or length > 220:
        score -= 25

    return score
