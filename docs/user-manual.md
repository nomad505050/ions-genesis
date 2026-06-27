# IONS Genesis — User Manual

A practical guide to running a node, contributing knowledge, and querying the network.

*Protocol version: ions-v0.4*

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Explorer — Querying the Network](#explorer)
3. [Add CBB — Contributing Knowledge](#add-cbb)
4. [Workbench — Review and Approval](#workbench)
5. [Graph — Cognitive Knowledge Map](#graph)
6. [Node — Status and Federation](#node)
7. [Settings — API Key and Model](#settings)
8. [Generating Relationships](#generating-relationships)
9. [Joining the Network](#joining-the-network)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An [OpenRouter](https://openrouter.ai) API key — free tier available
- Node.js 18+ (for frontend only)

### 1. Clone and configure

```bash
git clone https://github.com/nomad505050/ions-genesis.git
cd ions-genesis
cp .env.example .env
```

Edit `.env`:

```bash
OPENROUTER_API_KEY=sk-or-your-key-here
PUBLIC_API_BASE=https://your-public-url.com
NODE_DESCRIPTION=My IONS node
```

### 2. Start the node

```bash
docker compose up -d
```

Three services start:
- **PostgreSQL** on port 5432 — system of record
- **FastAPI backend** on port 8000 — CBB registry, traversal, API
- **Next.js frontend** on port 3000 — web interface

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","node":"genesis_node"}
```

Open `http://localhost:3000`.

---

## Explorer

The Explorer queries the network and shows you the full reasoning chain behind every answer.

### Running a query

1. Open `http://localhost:3000`
2. Type your question or pick a sample query
3. Press Enter or click **Query**
4. Wait 10-20 seconds for traversal

### Reading the result

**CBB Traversal answer** — synthesized from the reasoning path, grounded in actual CBBs with evidence.

**Path confidence** — trustworthiness of the knowledge in the path (CBB × REL × Evidence).

**Routing confidence** — did the attention allocation start in the right neighborhood? Below 0.60 means the network has limited coverage of your query domain.

**Reasoning path** — the sequence of CBBs and relationships traversed. Each hop shows the CBB ID and relationship type connecting it to the next.

**Alternative paths** — other high-scoring paths found during traversal. Different angles on the same question.

**Feedback** — thumbs up/down on the answer. Your feedback adjusts path utility and helps the routing layer improve over time.

**Session ID** — unique identifier for this query's routing session. Used for debugging and audit.

### Understanding confidence scores

| Score | Meaning |
|---|---|
| > 70% | High confidence — well-covered domain, strong evidence |
| 55-70% | Moderate — reasonable coverage, some evidence gaps |
| < 55% | Low — sparse coverage, add more CBBs in this domain |

Routing confidence below 0.60 means the attention allocation may have started in a suboptimal domain. The network will self-correct as routing sessions accumulate.

### Sample queries

- "How does institutional memory compound competitive advantage?"
- "Why do AI transformation initiatives fail to scale?"
- "What is the relationship between flow states and peak performance?"
- "How does Bitcoin proof-of-work create digital scarcity?"
- "What makes knowledge reusable across an organization?"

---

## Add CBB

Every CBB goes through a review queue before publication. The network learns from quality, not quantity.

### Extract from a document

1. Go to **Add CBB** in the sidebar
2. Upload a `.txt`, `.md`, or `.docx` file — or paste text directly
3. Fill in **Source type** and **Source reference**
4. Click **Extract CBBs →**
5. Review extracted candidates — each shows the claim, domain, and confidence
6. Deselect vague or compound claims
7. Click **Submit to review queue**

The system processes up to 24,000 characters per submission.

### What makes a good CBB?

**Good CBBs are:**
- One atomic, assertable claim
- Specific enough to evaluate in context
- Supported by the source material

**Good examples:**
> "Organizations that automate without operational discovery build on incorrect assumptions."

> "The EU AI Act applies to any company deploying AI within the EU, regardless of where they are based."

**Avoid:**
- Vague summaries: *"AI is important"*
- Compound claims: *"AI fails because of bad data and poor leadership"*
- Opinions without evidence

### Add a single claim

Use **Add single claim** tab for precise manual entry. Domain and confidence are auto-assigned if you have an API key configured.

---

## Workbench

The Workbench is where CBBs are reviewed, relationships are generated, and duplicates are managed.

### Review Queue

All submitted CBBs land here as candidates.

**Approve** — publishes the CBB to the network. It immediately becomes available for traversal.

**Reject** — deprecates the candidate. It will not appear in traversal.

Review carefully:
- Is the claim atomic? (one assertion only)
- Is it specific enough to evaluate?
- Does the domain assignment make sense?
- Is the confidence appropriate?

### Activity Tab

Shows network pipeline status and action buttons:

**Generate Relationships** — connects recent CBBs to existing network knowledge. Run after approving a batch of CBBs. Each run adds ~100-200 new relationships.

**Bulk Generate** — processes 500 CBBs with fewer than 3 relationships. Run multiple times to build network density.

**Embed Domains** — computes semantic embeddings for all domain names. Required before reclustering.

### Duplicates Tab

Shows near-duplicate CBB pairs detected by semantic similarity (above 0.92 cosine similarity within the same domain).

For each pair, review side-by-side and choose:
- **Keep A** — deprecate B
- **Keep B** — deprecate A
- **Keep Both** — both are genuinely different, keep both

Pairs with similarity > 0.98 are auto-resolved (exact duplicates). Pairs between 0.92-0.98 require human review.

---

## Graph

The Graph visualizes the network as Cognitive Subdomains (NSI clusters) connected by relationship lines.

### Cognitive Domains and Subdomains

The network is organized into 7 Cognitive Domains, each containing multiple Cognitive Subdomains:

- **Business & Operations** — Organizational Development, Business Strategy, Process Optimization, etc.
- **Intelligence & Technology** — Artificial Intelligence, Digital Transformation, Complex Systems, etc.
- **Human Performance** — Human Behavior, Learning and Development, Healthcare Systems, etc.
- **Economics & Finance** — Economic History, Secrets and Signals
- **Society & Governance** — Governance and Regulation, Climate Change, Influence Tactics
- **Knowledge & Epistemology** — Decision Making, Philosophy of Reality
- **Emerging Frontiers** — Technology Futures

Bubble size reflects CBB count. Larger bubbles have more knowledge.

### Connection lines

Lines between clusters indicate actual relationships between CBBs in different domains. Thicker lines mean more cross-domain relationships. Colors show which cluster you are hovering — all lines to/from that cluster light up in its color.

### Navigating

1. **Hover** a cluster to see its name and CBB count
2. **Click** a cluster to drill into its subdomains
3. **Click** a subdomain to see individual CBBs
4. **Click** a CBB to see full content and confidence
5. Use the **Filter** box to search by keyword
6. Click **↻ Recluster** to re-run k-means grouping after adding new domains

---

## Node

The Node page shows your node's status, statistics, and federation state.

### Node stats

- **Published CBBs** — total CBBs live on the network
- **Published Relationships** — total typed relationships
- **Cognitive Subdomains** — knowledge clusters
- **Active Nodes** — registered federated nodes

### Node Manifest

Your node announces its Cognitive Domains and capabilities at:
```
GET /.well-known/ions-node.json
```

v0.4 manifests include Cognitive Domain coverage with declared strength scores, replacing raw domain lists. This enables smarter federation routing — connected nodes can assess your node's relevance to a query before sending it.

### Registered Nodes

Shows IONS nodes registered with your node. When nodes are registered, queries automatically traverse all connected nodes and merge ranked results. Node failures are handled gracefully — a single unreachable node never blocks a query.

### Routing Health

View routing session metrics at:
```
GET /routing/health
```

Shows average routing confidence, cache hit ratio, and domain routing weights. Routing confidence trending up means the network is learning to allocate attention more effectively.

---

## Settings

### OpenRouter API Key

Required for:
- CBB extraction from documents
- Relationship generation
- Query synthesis

Get a free key at [openrouter.ai](https://openrouter.ai).

### Model Selection

IONS is model-agnostic. Recommended:

| Model | Use case |
|---|---|
| `meta-llama/llama-3.1-8b-instruct` | Default — fast, proves the thesis |
| `meta-llama/llama-3.1-70b-instruct` | Better extraction quality |
| `anthropic/claude-sonnet-4-5` | Highest accuracy |
| Local Ollama model | Zero cost, fully private |

### IONS Node URL

Default: `http://localhost:8000`. Change to point at a remote node or the public genesis node at `https://api.ionsprotocol.org`.

---

## Generating Relationships

Relationships connect CBBs into a traversable network. Without relationships, CBBs are isolated claims.

### From the Workbench

1. Go to **Workbench → Activity tab**
2. Click **⬡ Generate relationships** (100 CBBs) or **⬡ Bulk Generate** (500 CBBs)
3. Watch the progress bar
4. Check the relationship count in Node stats

Run multiple times to build density. The system prioritizes CBBs with fewer than 3 relationships.

### Target density

| Relationships per CBB | Network quality |
|---|---|
| < 2 | Sparse — few traversal paths |
| 3-5 | Functional — paths exist |
| 5-10 | Good — strong multi-hop paths |
| 10+ | Rich — high confidence traversal |

---

## Joining the Network

### Make your node public

1. Deploy to a server with a public URL
2. Update `.env`:
   ```bash
   PUBLIC_API_BASE=https://your-node.example.com
   ```
3. Rebuild: `docker compose up -d --build api`

### Register with the genesis node

```bash
curl -X POST https://api.ionsprotocol.org/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id": "your_node_id", "public_api_base": "https://your-node.example.com"}'
```

### After registering — seed Cognitive Domains

```bash
curl -X POST https://your-node.example.com/routing/domains/seed
```

This assigns your NSI clusters to Cognitive Domains and embeds them for routing. Required for your node's Cognitive Domain coverage to appear in the network manifest.

---

## API Reference

Full interactive docs at `http://localhost:8000/docs`

### Core endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/cbb` | Publish a CBB |
| GET | `/cbb` | Search CBBs |
| POST | `/query` | Run traversal query |
| GET | `/path/{id}` | Get a saved path |
| POST | `/feedback` | Submit path feedback |
| POST | `/nodes/register` | Register a node |
| GET | `/health` | Node health |
| GET | `/stats` | Network statistics |
| GET | `/.well-known/ions-node.json` | Node manifest |

### v0.4 endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/routing/domains` | Cognitive Domain taxonomy |
| GET | `/routing/health` | Routing confidence and domain weights |
| GET | `/routing/sessions` | Recent routing sessions |
| GET | `/routing/nsi-assignments` | NSI cluster to domain assignments |
| POST | `/routing/domains/seed` | Seed and embed Cognitive Domains |
| GET | `/routing/conflicts` | Unresolved Conflict Artifacts |
| GET | `/routing/validation/status` | Validation metrics |
| GET | `/dedup/status` | Embedding coverage and duplicate queue |
| POST | `/dedup/embed` | Embed all CBBs for semantic deduplication |

### Query request (v0.4)

```json
{
  "query": "How does institutional memory compound competitive advantage?",
  "intent": "explain",
  "top_n_paths": 3,
  "max_depth": 5,
  "include_contradictions": false,
  "save_path": true
}
```

### Query response (v0.4)

```json
{
  "cbb_answer": "...",
  "session_id": "rsess_abc123",
  "routing_confidence": 0.48,
  "paths": [
    {
      "path_id": "path_xyz",
      "path_confidence": 0.68,
      "path_relevance": 0.36,
      "path_rank_score": 0.48,
      "cbb_sequence": ["cbb_001", "cbb_002", "cbb_003"]
    }
  ]
}
```

---

## Troubleshooting

### Node won't start

```bash
docker compose logs api --tail 20
```

Common causes:
- Missing `.env` — copy `.env.example` to `.env`
- Database not ready — wait 10 seconds, retry
- Port conflict — change ports in `docker-compose.yml`

### No paths returned

The network needs CBBs and relationships in the relevant domain:
1. Check if relevant CBBs exist — search in the Graph
2. Check relationship count — Node stats
3. Run Generate Relationships in Workbench
4. Run Embed Domains and Recluster after adding new content

### Low path confidence (below 60%)

- Add CBBs with strong external evidence (books, papers, articles score 0.75-0.90)
- Run Bulk Generate Relationships
- Try a more specific query matching your CBB domains

### Low routing confidence (below 0.50)

- Run `/routing/domains/seed` to assign NSI clusters to Cognitive Domains
- Check `/routing/nsi-assignments` for unassigned clusters
- Manually assign clusters via `POST /routing/nsi-assignments/{label}?domain_id=...`

### Duplicate CBBs in Workbench

The Duplicates tab shows near-duplicate pairs. Review side-by-side and choose Keep A, Keep B, or Keep Both. Pairs with similarity > 0.98 are auto-resolved. Run `POST /dedup/embed` to scan the full corpus for duplicates after bulk imports.

### API key errors

- Verify key in Settings
- Check key is valid at openrouter.ai
- Ensure selected model is on your OpenRouter plan
