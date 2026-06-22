# IONS: Intelligence Operating Network System

**A protocol for cognitive composition at scale through traversable Cognitive Building Blocks**

*Darron Dickinson — June 2026*

---

## Abstract

Current AI architectures compress knowledge into model weights, creating systems that are opaque, difficult to update, and dependent on parameter scale for quality. This paper introduces IONS (Intelligence Operating Network System), an open protocol that externalizes knowledge into a traversable network of atomic, typed, evidence-backed claims called Cognitive Building Blocks (CBBs). Lightweight models act as interpreters and synthesizers rather than knowledge stores. The Genesis experiment demonstrates that an 8B parameter model connected to a CBB network matched or exceeded a frontier model on 5 of 8 domain-specific queries, producing inspectable reasoning paths with explicit evidence chains. The protocol supports multi-node federation, enabling distributed knowledge networks where any compliant node can contribute CBBs and participate in cross-node traversal.

---

## 1. The Problem with Weight-Compressed Intelligence

Modern large language models achieve impressive general capability by compressing knowledge from training data into billions of parameters. This architecture has fundamental limitations:

**Opacity** — The reasoning process is invisible. When a model produces an answer, there is no inspectable chain of evidence. Users must trust the output without understanding why it was produced.

**Staleness** — Knowledge embedded in weights reflects the training cutoff. Updating knowledge requires retraining or fine-tuning, which is expensive and slow.

**Scale dependency** — Quality is tightly coupled to parameter count. Better answers require larger models, which require more compute and energy.

**No provenance** — There is no mechanism to trace an answer back to its evidence sources, attribute knowledge to its contributors, or establish confidence that is grounded in specific claims.

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

### 2.1 Cognitive Building Blocks

A Cognitive Building Block (CBB) is the atomic unit of knowledge in IONS. Each CBB is:

- **One claim** — a single assertable statement, specific enough to evaluate as true or false in context
- **Evidence-backed** — references to supporting sources
- **Confidence-rated** — creator-asserted confidence score (0-1)
- **Scoped** — explicit assumptions and domain applicability
- **Addressable** — stable unique ID and cryptographic hash
- **Typed** — currently `claim`; future types include `observation`, `procedure`, `outcome`, `decision`

```json
{
  "cbb_id": "cbb_a1b2c3d4e5f6",
  "type": "claim",
  "domain": "organizational_intelligence",
  "content": "Organizations that automate without operational discovery build on incorrect assumptions.",
  "confidence": 0.85,
  "evidence": [{"source_type": "book", "source_id": "abr_chapter_3"}],
  "assumptions": ["Organization has existing workflows"],
  "scope": ["enterprise_ai", "process_automation"],
  "status": "published",
  "hash": "sha256:..."
}
```

### 2.2 Relationships

Relationships are first-class artifacts connecting CBBs with typed, confidence-rated edges:

| Type | Meaning |
|---|---|
| `supports` | Source increases confidence of target |
| `contradicts` | Source challenges target |
| `depends_on` | Source requires target as premise |
| `causes` | Source leads to target |
| `correlates_with` | Source and target are associated |
| `extends` | Source expands target |
| `refines` | Source narrows or clarifies target |
| `references` | Source cites target |

Relationships include rationale, creator attribution, confidence score, and cryptographic hash. They are not merely database edges — they are protocol artifacts with full lineage.

### 2.3 Reasoning Paths

A Reasoning Path is the stored result of traversal — an ordered sequence of CBBs and relationships that supports an answer to a specific query. Paths are reusable artifacts with:

- Path confidence score (computed from CBB avg × Relationship avg × Evidence score)
- Full CBB sequence with individual confidence scores
- Relationship sequence with types and rationale
- Synthesized answer grounded in the path
- Cryptographic hash for integrity

Reasoning paths are more valuable than answers alone because they are inspectable, evidence-grounded, and reusable.

### 2.4 NSI Clusters

Narrow Super Intelligence (NSI) clusters are semantic groupings of CBB domains. As contributors add knowledge, domains form organically and are grouped into NSIs by the LLM. A node running IONS Genesis currently covers 21 NSI clusters including:

- Economics & Finance
- AI & Machine Learning
- Organizational Intelligence
- Platform & Strategy
- Peak Performance
- AI Regulation & Policy
- Healthcare and AI
- Blockchain & Cryptocurrency

NSI clusters are a visualization and routing layer — they do not constrain what domains CBBs can be assigned to.

---

## 3. The Traversal Engine

The traversal engine receives a query, identifies candidate starting CBBs, explores connected CBBs through relationships, scores candidate paths, and synthesizes an answer from the top-ranked path.

### 3.1 Query Flow

```
1. Receive query
2. Discover starting CBBs via keyword search
3. Enumerate paths via bounded depth-first search (max depth: 5)
4. Score each path: PathConfidence = CBB_avg × REL_avg × EvidenceScore
5. Rank paths by confidence × relevance
6. Select top N paths
7. Synthesize answer from best path
8. Store reasoning path artifact
9. Return answer + paths + confidence math
```

### 3.2 Confidence Formula

```
CBB_avg      = average confidence of CBBs in path
REL_avg      = average confidence of relationships in path
EvidenceScore = average evidence score of CBBs in path

PathConfidence = CBB_avg × REL_avg × EvidenceScore
```

Evidence scores:

| Evidence Quality | Score |
|---|---|
| No evidence | 0.25 |
| One weak/internal reference | 0.50 |
| Multiple internal or one strong external | 0.75 |
| Multiple strong references | 0.90 |
| Validated through observed outcomes | 1.00 |

Confidence is always shown with its path and evidence context — never as a context-free number.

### 3.3 Contradiction Handling

`contradicts` relationships generate alternative or warning paths rather than being mixed into the primary supporting path. This preserves the integrity of the primary answer while making counterarguments visible.

---

## 4. The Genesis Experiment

### 4.1 Objective

Prove that a lightweight model connected to a CBB network can match or exceed a frontier model on domain-specific queries.

### 4.2 Corpus Construction

The Genesis corpus was built from:

| Source | CBBs | Method |
|---|---|---|
| Organizational knowledge (Cognis) | ~740 | LLM extraction |
| Personal knowledge (D2Brain) | ~4 | Manual |
| ABR book (organizational intelligence) | ~468 | Targeted extraction |
| 42 non-fiction books across domains | ~630 | LLM extraction (15 per book) |

After quality review, the published corpus contains approximately 784 CBBs across 21 NSI clusters with 3,700+ typed relationships.

### 4.3 Benchmark Design

Three conditions were compared on 8 domain-specific queries:

1. **Raw Llama 3.1 8B** — no CBB context, direct LLM response
2. **8B + CBB Traversal** — same model with top reasoning paths as context
3. **Claude Sonnet (frontier)** — frontier model baseline

Evaluation criteria: answer relevance, reasoning coherence, evidence grounding, domain accuracy.

### 4.4 Results

| Condition | Queries won/matched |
|---|---|
| Raw Llama 3.1 8B | 0 of 8 |
| **8B + CBB Traversal** | **5-6 of 8** |
| Claude Sonnet | 8 of 8 |

Average path confidence: **0.547**

The 8B model connected to the CBB network matched or exceeded the frontier model on 5-6 of 8 domain-specific queries. The primary limitation is evidence score — most Genesis CBBs have internal-only evidence references (score: 0.50), capping the theoretical maximum path confidence. As contributors add CBBs with stronger external evidence, path confidence will improve.

### 4.5 Key Findings

**The model is not the bottleneck.** On well-covered domains, the 8B model with CBB context outperforms itself without context on every query.

**Relationship density matters.** Queries that returned weak paths consistently corresponded to domains with fewer than 3 relationships per CBB. Above 5 relationships per CBB, paths became coherent.

**Cross-domain traversal is the differentiator.** The most interesting paths crossed NSI boundaries — connecting, for example, organizational intelligence CBBs to AI regulation CBBs to produce nuanced compliance answers.

**Reasoning paths are more valuable than answers.** The inspectable path lets users evaluate the quality of reasoning rather than trusting a black-box output.

---

## 5. Multi-Node Federation

### 5.1 Protocol Design

Each IONS node announces its capabilities and domain coverage via a node manifest at a well-known URL:

```
GET /.well-known/ions-node.json
```

```json
{
  "node_id": "genesis_node",
  "protocol_version": "ions-genesis-0.1",
  "capabilities": ["publish_cbb", "query", "traverse", "federated_query"],
  "domains": ["ai_regulation", "monetary_economics", "peak_performance", ...],
  "cbb_count": 784,
  "public_api_base": "https://your-node.example.com",
  "status": "active",
  "open_contributions": true
}
```

### 5.2 Federated Query

When a query arrives at a node with federation enabled:

1. The node runs local traversal
2. In parallel, it queries all registered remote nodes
3. Paths from all nodes are merged and ranked by confidence
4. The synthesized answer draws from the best paths regardless of origin
5. Each path is tagged with its source node

```json
{
  "paths": [
    {
      "path_confidence": 0.72,
      "source_node": "node_2",
      "source_node_url": "https://node2.example.com",
      "cbb_sequence": ["cbb_abc", "cbb_def"]
    }
  ],
  "nodes_queried": 3
}
```

### 5.3 Network Effects

The value of the IONS network compounds with participation:

- Each new node adds domain coverage that benefits all connected nodes
- Cross-node relationships connect knowledge across contributors
- Reasoning paths that traverse multiple nodes produce answers that no single node could produce alone
- High-confidence CBBs from specialized nodes raise the overall network quality

---

## 6. Comparison with Related Systems

| System | Primary Artifact | Output | Key Limitation |
|---|---|---|---|
| RAG | Retrieved chunks | Answer with context | Chunks are not protocol artifacts; reasoning path is discarded |
| Knowledge Graph | Nodes and edges | Graph query result | No confidence, evidence, or path artifact lifecycle |
| Fine-tuned LLM | Model weights | Answer | Opaque, expensive to update, no provenance |
| **IONS** | CBB + Relationship + Reasoning Path | Answer + evidence + reusable path | Network density required for high confidence |

IONS addresses the core limitation of RAG — the reasoning path is stored as a reusable artifact, not discarded after the query. It addresses the core limitation of knowledge graphs — confidence, evidence lineage, and path scoring are first-class concepts.

---

## 7. Protocol Primitives

### 7.1 CBB Schema

```json
{
  "cbb_id": "string",
  "type": "claim",
  "domain": "string",
  "content": "string (single atomic claim)",
  "evidence": [{"source_type": "string", "source_id": "string"}],
  "confidence": "float 0-1",
  "assumptions": ["string"],
  "scope": ["string"],
  "creator": "string",
  "status": "candidate | approved | published | deprecated | rejected",
  "version": "string",
  "hash": "sha256:string"
}
```

### 7.2 Relationship Schema

```json
{
  "relationship_id": "string",
  "source_cbb_id": "string",
  "target_cbb_id": "string",
  "relationship_type": "supports | contradicts | depends_on | causes | correlates_with | extends | refines | references",
  "confidence": "float 0-1",
  "rationale": "string",
  "creator": "string",
  "status": "published",
  "hash": "sha256:string"
}
```

### 7.3 Reasoning Path Schema

```json
{
  "path_id": "string",
  "query": "string",
  "cbb_sequence": ["cbb_id"],
  "relationship_sequence": ["relationship_id"],
  "path_confidence": "float 0-1",
  "evidence_score": "float 0-1",
  "answer": "string",
  "path_explanation": "string",
  "hash": "sha256:string"
}
```

---

## 8. Current Status and Roadmap

### Live in Genesis v0.1

- CBB registry with full CRUD and status lifecycle
- Typed relationship registry
- Bounded traversal engine (depth 5, top 3 paths)
- Path registry with reusable reasoning path artifacts
- Multi-node federation with node registry and manifest
- Server-side relationship generation
- Light D2Brain extractor for document-to-CBB extraction
- Web interface: Explorer, Graph, Workbench, Contribute, Node
- MIT licensed open source reference implementation

### Future Protocol Extensions

| Extension | Trigger |
|---|---|
| Network-derived reputation scoring | Multiple contributors or nodes |
| Token access accounting | Network participation grows beyond closed Genesis |
| Context engine — scope and assumption propagation | Contradictory high-confidence paths become common |
| Advanced traversal — beam search, temporal weighting | Dataset grows beyond brute-force scale |
| Outcome feedback — real-world confidence adjustment | Paths used in practical decision workflows |
| Multiple CBB types — observation, procedure, outcome | Claim type proven at scale |
| Rights and attribution claims | Verification methodology established |

---

## 9. Running a Node

```bash
git clone https://github.com/nomad505050/ions-genesis.git
cd ions-genesis
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
docker compose up -d
open http://localhost:3000
```

See the [User Manual](user-manual.md) for detailed setup and contribution instructions.

---

## 10. Conclusion

IONS demonstrates that intelligence can emerge from traversal and composition across a network of atomic knowledge claims rather than from parameter scale alone. The Genesis experiment provides empirical evidence: an 8B model connected to a CBB network matched a frontier model on domain-specific queries while producing inspectable, evidence-grounded reasoning paths.

The protocol is open. The reference implementation is live. The network grows with every contributor.

The durable asset is not the model. The durable asset is the network.

---

## References

- Vaswani et al. (2017). Attention Is All You Need.
- Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.
- Pan et al. (2023). Unifying Large Language Models and Knowledge Graphs: A Roadmap.
- Srinivasan, B. (2022). The Network State.
- Ismail, S. (2014). Exponential Organizations.

---

*Repository: https://github.com/nomad505050/ions-genesis*
*Protocol version: ions-genesis-0.1*
*License: MIT*
