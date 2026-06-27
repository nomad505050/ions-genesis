"""
IONS v0.4 — Canonical Cognitive Domain Taxonomy
Genesis-defined, governance-evolved.
These are the 7 top-level attention routing domains.
"""

COGNITIVE_DOMAINS = [
    {
        "domain_id": "domain_business_operations",
        "label": "Business & Operations",
        "description": "Organizational management, strategy, process design, and leadership. Covers how organizations are structured, run, and transformed.",
        "decay_tier": "medium",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_intelligence_technology",
        "label": "Intelligence & Technology",
        "description": "Artificial intelligence, software systems, blockchain, digital transformation, and complex computational systems.",
        "decay_tier": "fast",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_economics_finance",
        "label": "Economics & Finance",
        "description": "Markets, monetary systems, financial technology, trade, investment, and economic theory.",
        "decay_tier": "fast",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_human_performance",
        "label": "Human Performance",
        "description": "Individual and team capability, health, psychology, learning science, and peak performance.",
        "decay_tier": "medium",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_society_governance",
        "label": "Society & Governance",
        "description": "Institutions, regulation, policy, social systems, geopolitics, and governance frameworks.",
        "decay_tier": "fast",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_knowledge_epistemology",
        "label": "Knowledge & Epistemology",
        "description": "Philosophy, science, decision theory, epistemology, innovation, and the nature of knowledge itself.",
        "decay_tier": "slow",
        "routing_weight": 1.0,
    },
    {
        "domain_id": "domain_emerging_frontiers",
        "label": "Emerging Frontiers",
        "description": "Existential risk, future technology, long-term thinking, agent dynamics, and emerging paradigms.",
        "decay_tier": "fast",
        "routing_weight": 1.0,
    },
]

# Domain affinity matrix — Genesis defaults
# When domain A is selected, include domain B if affinity > 0.50
DOMAIN_AFFINITY = {
    ("Intelligence & Technology", "Society & Governance"): 0.65,
    ("Intelligence & Technology", "Business & Operations"): 0.55,
    ("Intelligence & Technology", "Emerging Frontiers"): 0.60,
    ("Economics & Finance", "Society & Governance"): 0.50,
    ("Economics & Finance", "Business & Operations"): 0.60,
    ("Human Performance", "Knowledge & Epistemology"): 0.45,
    ("Human Performance", "Business & Operations"): 0.50,
    ("Business & Operations", "Knowledge & Epistemology"): 0.45,
    ("Emerging Frontiers", "Intelligence & Technology"): 0.60,
    ("Emerging Frontiers", "Society & Governance"): 0.55,
}

# NSI cluster to Cognitive Domain mapping — Genesis defaults
# Used to assign existing NSI clusters to domains
NSI_DOMAIN_MAPPING = {
    "Cognitive Studies": "domain_human_performance",
    "Economic Analysis": "domain_economics_finance",
    "Economic Systems": "domain_economics_finance",
    "Business Operations": "domain_business_operations",
    "Business Strategy": "domain_business_operations",
    "Human Performance": "domain_human_performance",
    "Business Innovation Strategy": "domain_business_operations",
    "Organizational Development": "domain_business_operations",
    "Artificial Intelligence": "domain_intelligence_technology",
    "Leadership Development": "domain_business_operations",
    "Decision Making": "domain_knowledge_epistemology",
    "Digital Transformation": "domain_intelligence_technology",
    "Blockchain Technology": "domain_intelligence_technology",
    "Technology Futures": "domain_emerging_frontiers",
    "Complex Systems Theory": "domain_knowledge_epistemology",
    "Software Development Efficiency": "domain_intelligence_technology",
    "Sleep and Consciousness": "domain_human_performance",
    "Healthcare Management": "domain_human_performance",
    "Health and Longevity": "domain_human_performance",
    "Technology Governance": "domain_society_governance",
    "Financial Compliance": "domain_economics_finance",
    "Communication Methods": "domain_business_operations",
    "AI Deployment Strategy": "domain_intelligence_technology",
    "Business Transformation": "domain_business_operations",
    "AI Accountability": "domain_society_governance",
    "Human-Agent Interaction": "domain_emerging_frontiers",
    "Digital Financial Systems": "domain_economics_finance",
    "Governance and Technology": "domain_society_governance",
    "Innovation Management": "domain_business_operations",
    "Risk and Uncertainty": "domain_knowledge_epistemology",
    "Peak Performance Psychology": "domain_human_performance",
    "Systems Complexity": "domain_knowledge_epistemology",
    "Artificial Intelligence Regulation": "domain_society_governance",
    "Human Development": "domain_human_performance",
    "Healthcare Operations": "domain_human_performance",
    "Medical Longevity": "domain_human_performance",
    "Product Development": "domain_business_operations",
    "Forex Trading": "domain_economics_finance",
    "Agent Interaction Boundaries": "domain_emerging_frontiers",
}

# Evidence decay tiers
DECAY_TIERS = {
    "slow": 0.99,    # Physics, Mathematics, Philosophy, History
    "medium": 0.97,  # Business, Economics, Biology, Psychology
    "fast": 0.94,    # AI, Medicine, Regulation, Finance, Geopolitics
}