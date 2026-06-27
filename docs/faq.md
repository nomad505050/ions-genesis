 IONS Genesis — Frequently Asked Questions

*Protocol version: ions-v0.4*

---

## General

**What is IONS?**

IONS (Intelligence Operating Network System) is an open protocol for traversable knowledge networks. Instead of compressing knowledge into model weights, IONS externalizes it into a network of atomic, typed, evidence-backed claims called Cognitive Building Blocks (CBBs). Lightweight models act as interpreters — the knowledge lives in the network, not in the model.

**What problem does IONS solve?**

Large language models are opaque, expensive to update, and dependent on parameter scale for quality. IONS makes knowledge inspectable (you can see exactly which claims produced an answer), updatable (add or correct CBBs without retraining), and model-agnostic (swap the model without losing the knowledge).

**How is IONS different from RAG?**

RAG retrieves chunks of text and passes them to a model as context. The reasoning process is discarded after the query. IONS traverses a typed graph of atomic claims and stores the reasoning path as a reusable artifact. The path is as valuable as the answer — it shows exactly which claims, in which order, connected by which relationship types, produced the result.

**How is IONS different from a knowledge graph?**

Traditional knowledge graphs have nodes and edges. IONS CBBs carry confidence scores, evidence references, assumptions, and scope. Relationships carry typed semantics, rationale, and confidence. Reasoning paths carry three independent quality scores. The network learns over time through routing sessions, path feedback, and self-validation. A knowledge graph is a data structure. IONS is a protocol.

**Is IONS open source?**

Yes. MIT license. Repository: https://github.com/nomad505050/ions-genesis

---

## The Network

**What is a CBB?**

A Cognitive Building Block is one atomic, assertable claim backed by evidence. Not a summary, not an opinion — one claim, specific enough to evaluate as true or false in context. Example: *"Organizations that automate without operational discovery build on incorrect assumptions."*

**What is a Reasoning Path?**

A Reasoning Path is the stored result of traversal — an ordered sequence of CBBs connected by typed relationships that collectively support an answer to a query. Paths carry three scores: path_confidence (knowledge trustworthiness), path_relevance (how well it answers the query), and path_utility (historical usefulness from feedback).

**What is a Cognitive Domain?**

Cognitive Domains are the top-level attention routing layer. The Genesis network has 7: Business & Operations, Intelligence & Technology, Human Performance, Economics & Finance, Knowledge & Epistemology, Society & Governance, and Emerging Frontiers. When a query arrives, the routing layer scores it against all domains to allocate attention before traversal begins.

**What is a Cognitive Subdomain?**

Cognitive Subdomains (formerly NSI clusters) are semantic groupings of CBB domains within a Cognitive Domain. For example, Business & Operations contains Organizational Development, Business Strategy, Innovation Management, Process Optimization, and others. The Genesis network has 24 subdomains.

**What is routing confidence?**

Routing confidence measures whether the attention allocation started in the right neighborhood of the network. It is the winning path rank score divided by the best possible score (1.0). Below 0.60 consistently on a query type means the network has limited coverage in that domain — contribute more CBBs there.

**What is a Routing Session?**

Every query generates a Routing Session — a complete record of every attention allocation decision made during that query. Which domains were considered, which CBBs were discovered, which path was selected, what confidence was achieved. Routing sessions are the flight recorder for network intelligence.

---

## Using the Network

**How do I query the network?**

Go to the Explorer at ionsprotocol.org or at `http://localhost:3000` on your own node. Type any question in the domain and press Enter. The network traverses CBBs via beam search and returns an answer grounded in the reasoning path.

**What does "path confidence" mean?**

Path confidence measures the trustworthiness of the knowledge used to produce the answer:
- Average CBB confidence in the path
- Average relationship confidence
- Evidence score of CBBs used

Below 60%: sparse coverage in this domain. Above 70%: well-covered domain with strong evidence.

**What does "routing confidence" mean?**

Routing confidence measures whether the network's attention started in the right place. High path confidence with low routing confidence means the answer is good but the network may have found an even better path with smarter routing. Both metrics improve with use as routing weights adjust.

**Why are there alternative paths?**

The beam search finds multiple high-scoring paths simultaneously. Alternative paths represent different angles on the same question — different starting CBBs, different relationship chains, sometimes different conclusions. When paths contradict each other, a Conflict Artifact is raised rather than silently choosing one.

**What does "thumbs up / thumbs down" do?**

Feedback adjusts path_utility — the historical usefulness score for that reasoning path. Path utility is one of three components in the path rank score. Feedback does not change CBB confidence or relationship confidence — those require stronger evidence than user preference. The routing layer uses feedback signals to gradually adjust domain routing weights.

**Can I query the public genesis node?**

Yes. The public API is at https://api.ionsprotocol.org. Example:

```bash
curl -X POST https://api.ionsprotocol.org/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does institutional memory compound competitive advantage?"}'
```

---

## Running a Node

**What do I need to run a node?**

Docker, Docker Compose, and an OpenRouter API key (free tier available). A server with a public URL if you want to federate with other nodes.

**How long does setup take?**

About 10 minutes to get a local node running. The genesis corpus is not included in the repo — you start with an empty network and build it up by contributing CBBs and generating relationships, or by federating with the genesis node.

**Can I run a node without a public server?**

Yes — local nodes work fully for personal use. You can query, contribute, and generate relationships without any public URL. You just won't federate with other nodes until you deploy publicly.


**Can a business run IONS privately, without connecting to the public network?**

Yes — fully private operation is a first-class use case. A business can run an IONS node entirely inside its own infrastructure with no external connections. Local CBBs contain proprietary knowledge, internal documents, and operational intelligence that never leaves the organization. Queries traverse only internal knowledge. No data is sent to the public genesis node or any external service. The only external dependency is the model API — which can itself be eliminated by running a local model via Ollama.

**What is mixed-mode operation?**

A node can federate selectively. A business might maintain a private internal node with proprietary knowledge and also connect to the public genesis node for general domain coverage. When a query arrives, the node traverses internal CBBs first, then optionally queries the public network for supplementary paths. Internal paths are tagged with their source node and can be weighted higher in ranking. Sensitive CBBs never leave the private node — only the query and path scores cross the boundary. This gives organizations the benefit of the broader network without exposing internal knowledge.

**What is the genesis node?**

The genesis node is the reference implementation running at https://api.ionsprotocol.org. It contains 8,369 published CBBs and 50,113 relationships across 7 Cognitive Domains. Any node can register with the genesis node to participate in federated queries.

**How does federation work?**

When a query arrives at a federated node, it runs local traversal and simultaneously queries all registered nodes. Paths from all nodes are merged and ranked by score. The best paths — regardless of origin — contribute to the answer. Each registered node gets a 15-second timeout. A node going offline never blocks a query.

**How do I register my node with the genesis node?**

```bash
curl -X POST https://api.ionsprotocol.org/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "your_node_id",
    "public_api_base": "https://your-node.example.com"
  }'
```

Then seed your Cognitive Domains:
```bash
curl -X POST https://your-node.example.com/routing/domains/seed
```

---

## Contributing Knowledge

**What makes a good CBB?**

One atomic, assertable claim. Specific enough to evaluate. Backed by a source. Not a summary, not an opinion. Good: *"Flow states require a challenge-to-skill ratio of approximately 1:1 to sustain."* Bad: *"Flow is important for performance."*

**How do I contribute CBBs?**

Use the Add CBB page in the web interface. Upload a document or paste text — the system extracts candidates automatically. Review, deselect weak candidates, and submit to the review queue. Approve in the Workbench to publish.

**What happens after I publish CBBs?**

They are immediately available for traversal but won't produce strong paths until they have relationships. Run Generate Relationships in the Workbench to connect new CBBs to the existing network. Aim for 5-10 relationships per CBB.

**What source types produce the best CBBs?**

Books and peer-reviewed papers produce the highest evidence scores (0.75-0.90). Web articles score 0.75 if from authoritative sources. Internal documents score 0.50. No citation scores 0.25 and caps path confidence significantly.

**Can I contribute programmatically?**

Yes, via the API:

```bash
curl -X POST https://api.ionsprotocol.org/cbb \
  -H "Content-Type: application/json" \
  -d '{
    "type": "claim",
    "domain": "organizational_intelligence",
    "content": "Your claim here.",
    "confidence": 0.8,
    "evidence": [{"source_type": "book", "source_id": "title"}]
  }'
```

---

## Technical

**What models does IONS support?**

Any model available on OpenRouter. The default is `meta-llama/llama-3.1-8b-instruct`. The 8B model connected to the CBB network matched a frontier model on 5-6 of 8 domain-specific queries in Genesis benchmarks. You can also run local models via Ollama — set the model URL in Settings.

**What database does IONS use?**

PostgreSQL with pgvector extension for semantic embedding similarity search. The pgvector extension enables fast cosine similarity lookups across 8,000+ CBB embeddings for the beam search discovery phase.

**What is beam search?**

Beam search is the traversal algorithm introduced in v0.4. Instead of exploring all possible paths (brute force), it maintains the top-N most promising paths at each hop using a blended score of query relevance, relationship confidence, CBB confidence, evidence quality, and freshness. This makes traversal scale to any network size.

**What is semantic deduplication?**

Semantic deduplication compares CBB embeddings within each domain and flags pairs with cosine similarity above 0.92 as near-duplicates. These appear in the Workbench Duplicates tab for human review. Pairs above 0.98 are auto-resolved. This prevents the network from developing echo chambers of near-identical claims.

**How does the self-validation loop work?**

A sample of reasoning paths are evaluated after the fact by two structural checks — one for coherence (does the chain make logical sense?) and one for optimality (was there a better path the routing missed?). Neither check calls an external model. If the routing missed a better path, domain routing weights adjust. Knowledge layer (CBB and relationship confidence) is never touched by the validation loop.

**What is CBB saturation?**

Some CBBs appear in almost every reasoning path because they are highly connected hubs. Saturation tracking identifies these and applies a PageRank-style penalty to their selection score. This prevents the network from always routing through the same handful of CBBs and encourages discovery of less-central but equally valid knowledge.

---

## Roadmap

**What is coming in v0.5?**

Automatic intent inference (the network detects whether you are asking to explain, compare, diagnose, or debate without you specifying), verified node strength (observed from actual usage rather than self-declared), and path reuse cache (returning cached high-confidence paths for similar queries).

**When will IONS support other CBB types?**

Currently only `claim` type is implemented. Observation, procedure, outcome, and decision types are planned once the claim type is proven at scale. Each type requires different evidence and confidence semantics.

**Will IONS support local-only operation?**

It already does. Run docker compose locally with a local Ollama model and no external API calls are required. The network works fully offline.

**How can I follow development?**

- GitHub: https://github.com/nomad505050/ions-genesis
- Public node: https://api.ionsprotocol.org
- Protocol site: https://ionsprotocol.org
