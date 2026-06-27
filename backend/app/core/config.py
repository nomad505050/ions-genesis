from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "meta-llama/llama-3.1-8b-instruct"
    ions_node_id: str = "genesis_node"
    auth_secret: str = "change-me-in-production"
    env: str = "local"

    # Federation settings
    node_id: str = "genesis_node"
    public_api_base: str = "http://localhost:8000"
    node_description: str = "IONS Genesis reference node"

    # v0.4 — Attention allocation thresholds
    node_routing_threshold: float = 0.30
    domain_routing_threshold: float = 0.35
    subdomain_top_k: int = 5
    cbb_discovery_top_k: int = 10
    precision_bypass_threshold: float = 0.92

    # v0.4 — Beam search
    beam_width: int = 5
    beam_diversity_slots: int = 1
    max_traversal_depth: int = 5
    diversity_overlap_threshold: float = 0.60
    diversity_penalty: float = 0.15

    # v0.4 — Beam scoring weights
    beam_query_weight: float = 0.45
    beam_rel_conf_weight: float = 0.20
    beam_cbb_conf_weight: float = 0.20
    beam_evidence_weight: float = 0.10
    beam_freshness_weight: float = 0.05

    # v0.4 — Path ranking weights
    rank_relevance_weight: float = 0.45
    rank_confidence_weight: float = 0.35
    rank_utility_weight: float = 0.20

    # v0.4 — Learning loop
    validation_sample_rate: float = 0.10
    optimality_gap_threshold: float = 0.08
    exploration_budget: float = 0.10
    utility_decay_factor: float = 0.95
    utility_ceiling_multiplier: float = 1.20

    # v0.4 — CBB saturation
    saturation_threshold: float = 0.30
    saturation_penalty: float = 0.08

    # v0.4 — Path reuse cache
    cache_similarity_threshold: float = 0.92
    cache_min_utility: float = 0.70

    # v0.4 — Routing confidence
    routing_confidence_alert_threshold: float = 0.60

    class Config:
        env_file = ".env"

settings = Settings()