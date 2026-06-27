# IONS: Intelligence Operating Network System

**A protocol for cognitive composition at scale through traversable Cognitive Building Blocks**

*Darron Dickinson — June 2026*

---

## Abstract

Current AI architectures compress knowledge into model weights, creating systems that are opaque, difficult to update, and dependent on parameter scale for quality. This paper introduces IONS (Intelligence Operating Network System), an open protocol that externalizes knowledge into a traversable network of atomic, typed, evidence-backed claims called Cognitive Building Blocks (CBBs). Lightweight models act as interpreters and synthesizers rather than knowledge stores. The Genesis experiment demonstrates that an 8B parameter model connected to a CBB network matched a frontier model on 5 of 8 domain-specific queries, producing inspectable reasoning paths with explicit evidence chains. v0.4 introduces a Cognitive Attention Architecture — a hierarchical routing tree that allocates attention across the network before traversal begins, enabling the protocol to scale to millions of relationships across hundreds of federated nodes.

---

## 1. The Problem with Weight-Compressed Intelligence

Modern large language models achieve impressive general capability by compressing knowledge from training data into billions of parameters. This architecture has fundamental limitations:

**Opacity** — The reasoning process is invisible. When a model produces an answer, there is no inspectable chain of evidence.

**Staleness** — Knowledge embedded in weights reflects the training cutoff. Updating knowledge requires retraining or fine-tuning, which is expensive and slow.

**Scale dependency** — Quality is tightly coupled to parameter count. Better answers require larger models, which require more compute and energy.

**No provenance** — There is no mechanism to trace an answer back to its evidence sources, attribute knowledge to its contributors, or establish confidence grounded in specific claims.

**Monolithic architecture** — A model is a single artifact. There is no protocol for composing multiple specialized knowledge sources or federating across distributed knowledge holders.

---

## 2. The IONS Architecture

IONS inverts the traditional AI architecture:

```
Traditional AI:
Model → Knowledge → Answer

IONS:
CBBs → Relationships → Traversal → Reasoning Path → Answer
```

The durable asset is not the model. The durable asset is the network of Cognitive Building Blocks, relationships, and reasoning paths. Models are replaceable interpreters.

### 2.1 Two-Layer Architecture

v0.4 explicitly separates the protocol into two layers:

**Knowledge Layer (immutable)** — CBBs, Relationships, Reasoning Paths. Changes only through human curation, outcome evidence, or multi-validator consensus. Never modified by automated feedback alone.

**Routing Layer (adaptive)** — Cognitive Domain weights, beam parameters, exploration budget, path cache, routing sessions. Adjusts based on validation signals and feedback. Fully resettable without touching the knowledge layer.

Knowledge survives routing failures. Routing can be corrected without losing knowledge.

### 2.2 Cognitive Building Blocks

A CBB is the atomic unit of knowledge in IONS:

- **One claim** — a single assertable statement
- **Evidence-backed** — references to supporting sources
- **Confidence-rated** — creator-asserted confidence (0-1)
- **Addressable** — stable unique ID and cryptographic hash
- **Embedded** — vector embedding for semantic routing

### 2.3 Relationships

Eight typed relationship edges: supports, contradicts, depends_on, causes, correlates_with, extends, refines, references. Each is a first-class artifact with confidence, rationale, and cryptographic hash.

### 2.4 Reasoning Paths

Three independent scores per path:

- **path_confidence** — knowledge trustworthiness (CBB × REL × Evidence)
- **path_relevance** — query answer quality (embedding similarity)
- **path_utility** — historical usefulness (feedback + validation signals)

Final rank: `path_rank_score = (relevance × 0.45) + (confidence × 0.35) + (utility × 0.20)`

### 2.5 Cognitive Domains

Seven canonical routing domains for Genesis:

| Domain | CBBs |
|---|---|
| Business & Operations | 2,445 |
| Intelligence & Technology | 2,344 |
| Human Performance | 1,496 |
| Economics & Finance | 802 |
| Knowledge & Epistemology | 679 |
| Society & Governance | 625 |
| Emerging Frontiers | 191 |

Each domain contains multiple Cognitive Subdomains (NSI clusters). Domains are canonical in Genesis but may evolve through protocol governance.

---

## 3. The Cognitive Attention Architecture

### 3.1 Query Flow

```
Query + Intent
  ↓ Embed Query
  ↓ Route to Relevant Nodes
  ↓ Route to Cognitive Domains
  ↓ Route to Cognitive Subdomains
  ↓ Discover Candidate CBBs (embedding similarity)
  ↓ Beam Search Relationships
  ↓ Contradiction Detection
  ↓ Rank Reasoning Paths
  ↓ Compute Routing Confidence
  ↓ Generate Answer
  ↓ Store Path + Routing Session
  ↓ Validation Sampling
```

### 3.2 Beam Search

Extension score at each hop:
```
ext_score = (query_similarity × 0.45) + (rel_confidence × 0.20) +
            (cbb_confidence × 0.20) + (evidence_score × 0.10) +
            (freshness × 0.05)
```

Beam composition: 4 highest scoring + 1 forced diversity slot per iteration.

Scaling: v0.3 touches all 50,000+ relationships per query. v0.4 touches 500-2,000 regardless of network size.

### 3.3 Routing Confidence

```
routing_confidence = winning_path_rank_score / best_possible_score
```

The primary protocol health metric. Below 0.60 consistently signals domain routing weight adjustment is needed.

### 3.4 Routing Sessions

Every query generates a complete flight recorder — every attention allocation decision, every node considered, every domain scored. Replayable for debugging systematic routing failures.

### 3.5 Contradiction Detection

When contradicting paths are found, a Conflict Artifact surfaces both positions rather than silently choosing one. The network says "I disagree with myself" instead of pretending certainty.

### 3.6 Intent

Query intent shapes attention allocation and traversal strategy:

| Intent | Behavior |
|---|---|
| Explain | Foundational CBBs, breadth over depth |
| Compare | Relationship-heavy paths |
| Diagnose | Causal chains |
| Debate | Actively seeks contradictions |
| Validate | Evidence-heavy CBBs |

---

## 4. Self-Validating Learning Loop

Self-contained — no frontier model dependency, works in regulated environments.

### 4.1 Two Structural Checks

**Coherence check** — domain-agnostic: does each step logically follow? Does the answer follow from the chain?

**Optimality check** — generates 2 alternative paths. If a better path exists that wasn't chosen, routing weights adjust toward the domain that produced it.

### 4.2 What Adjusts vs What Never Adjusts

| Signal | Adjusts | Never Adjusts |
|---|---|---|
| Path feedback | path_utility, domain routing weights | CBB confidence, relationship confidence |
| Coherence failure | Domain routing weight reduction | CBB or relationship confidence |
| Path suboptimality | Domain routing weights | Knowledge layer |

### 4.3 Exploration Budget

10% of queries ignore routing weights to prevent echo chamber convergence. The network always explores, never fully converges.

---

## 5. The Genesis Experiment

**Corpus:** 8,369 CBBs, 50,113 relationships, 175+ books, 7 Cognitive Domains

**Benchmark results:**

| Condition | Queries matched |
|---|---|
| Raw Llama 3.1 8B | 0 of 8 |
| 8B + CBB Traversal (v0.3) | 5-6 of 8 |
| 8B + Cognitive Attention (v0.4) | 6-7 of 8 |
| Claude Sonnet (frontier) | 8 of 8 |

Average path confidence: 0.686 (v0.4) vs 0.547 (v0.3)

Cross-domain traversal is the differentiator. The most interesting paths crossed Cognitive Domain boundaries — connecting institutional memory to platform data effects to organizational culture to behavioral change: a path no single domain would produce.

---

## 6. Multi-Node Federation

### 6.1 Node Manifest

```json
{
  "node_id": "genesis_node",
  "protocol_version": "ions-v0.4",
  "cognitive_domains": [
    {"label": "Business & Operations", "declared_strength": 0.91, "cbb_count": 2445}
  ],
  "cbb_count": 8369,
  "public_api_base": "https://api.ionsprotocol.org"
}
```

Cognitive Domains replace raw domain lists as the federation routing signal.

### 6.2 Fault-Tolerant Federation

Each node gets a 15-second timeout. Node failures are caught and logged without corrupting the main query session. The network degrades gracefully — if 3 of 4 nodes are offline, the query completes on the remaining node.

### 6.3 Node Strength

**Declared** (v0.4): self-reported from CBB confidence, relationship quality, evidence score.
**Verified** (future): observed from relationships used in successful paths / CBB count.

Raw relationship density is not rewarded.

---

## 7. Current Status

**Live on genesis node (https://api.ionsprotocol.org):**
- 8,369 CBBs, 50,113 relationships
- 7 Cognitive Domains, 24 Cognitive Subdomains
- Beam search traversal
- Three-score path ranking
- Routing sessions and routing confidence
- Contradiction detection
- Path feedback API
- Self-validation loop
- CBB saturation tracking

**Open source:** https://github.com/nomad505050/ions-genesis (MIT)

---

## 8. Conclusion

Intelligence emerges from traversal and composition across a network of atomic knowledge claims — not from parameter scale alone. v0.4 makes this scalable to any network size through cognitive attention allocation.

The protocol is open. The reference implementation is live. The network improves with every query, contribution, and registered node.

The durable asset is not the model. The durable asset is the network.

---

*Protocol site: https://www.ionsprotocol.org*
*Repository: https://github.com/nomad505050/ions-genesis*
*Public node: https://api.ionsprotocol.org*
*Protocol version: ions-v0.4*
*License: MIT*
