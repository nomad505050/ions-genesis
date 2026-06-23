# IONS — Intelligence Operating Network System

**A lightweight protocol for publishing, connecting, and traversing Cognitive Building Blocks into reusable reasoning paths.**

IONS is an open protocol that inverts the traditional AI architecture. Instead of compressing knowledge into model weights, IONS externalizes knowledge into a traversable network of atomic, typed, and evidence-backed claims called **Cognitive Building Blocks (CBBs)**. Any lightweight model can then traverse this network to produce answers with visible reasoning chains.

> Genesis Result: An 8B parameter model connected to a CBB network matched or exceeded a frontier model on 5 of 8 domain-specific queries — at a fraction of the compute cost.

---

## The Core Thesis

Traditional AI: `Model → Knowledge → Answer`

IONS: `CBBs → Relationships → Traversal → Reasoning Path → Answer`

The durable asset is not the model. The durable asset is the network of CBBs, relationships, and reasoning paths. Models are replaceable interpreters. The network compounds.

---

## What is a CBB?

A **Cognitive Building Block** is a single atomic, assertable claim:

```json
{
  "cbb_id": "cbb_a1b2c3d4e5f6",
  "type": "claim",
  "domain": "organizational_intelligence",
  "content": "Organizations that automate without operational discovery build on incorrect assumptions.",
  "confidence": 0.85,
  "evidence": [{"source_type": "book", "source_id": "abr_chapter_3"}],
  "assumptions": ["Organization has existing workflows to map"],
  "scope": ["enterprise_ai", "process_automation"],
  "status": "published"
}
```

CBBs are:
- **Atomic** — one claim only, specific enough to evaluate
- **Typed** — confidence, evidence, scope, and assumptions are explicit
- **Addressable** — every CBB has a stable ID and cryptographic hash
- **Traversable** — connected by typed relationships to other CBBs

---

## What is a Reasoning Path?

A reasoning path is the ordered result of traversal — stored as a reusable artifact:

```
Query: "Why do AI initiatives fail early?"

Path: cbb_001 → [supports] → cbb_014 → [causes] → cbb_027 → [depends_on] → cbb_039
Confidence: 65.5%
Answer: "Many enterprise AI initiatives fail early because shallow operational 
         discovery produces incomplete requirements..."
```

Paths are inspectable, scorable, and reusable. The reasoning is visible — not a black box.

---

## Genesis — The Reference Implementation

Genesis is the first IONS node. It proves the protocol works with a curated corpus of CBBs across multiple domains including organizational intelligence, economics, blockchain, peak performance, AI regulation, and healthcare AI.

### Genesis Benchmark Results

| Query Type | Raw 8B | 8B + CBB Traversal | Claude Sonnet |
|---|---|---|---|
| Domain-specific | Weak | **Strong** | Strong |
| Cross-domain reasoning | Weak | **Competitive** | Strong |
| Average path confidence | — | 0.547 | — |

The 8B + CBB network matched or exceeded the frontier model on 5 of 8 domain queries.

---

## Architecture

```
Knowledge Sources (documents, books, research, observations)
        ↓
Light D2Brain Extractor (LLM-powered CBB extraction)
        ↓
Review Queue (human approval before publication)
        ↓
IONS Network
  ├── CBB Registry
  ├── Relationship Registry  
  ├── Path Registry
  └── Traversal Engine
        ↓
Query Interface → Answer + Reasoning Path + Evidence
```

---

## Genesis Node

The reference genesis node is publicly accessible. You can query it directly or register your node against it:

```bash
# Query the genesis node
curl -X POST http://162.243.203.243:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does institutional memory compound competitive advantage?"}'

# Register your node with genesis
curl -X POST http://162.243.203.243:8000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id": "your_node_id", "public_api_base": "https://your-node.example.com"}'

# Node manifest
curl http://162.243.203.243:8000/.well-known/ions-node.json
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An [OpenRouter](https://openrouter.ai) API key (for CBB extraction and relationship generation)
- Node.js 18+ (for the frontend)

### 1. Clone and configure

```bash
git clone https://github.com/ions-protocol/genesis
cd genesis
cp .env.example .env
```

Edit `.env`:

```bash
OPENROUTER_API_KEY=sk-or-your-key-here
IONS_NODE_ID=my_node
DATABASE_URL=postgresql+asyncpg://ions:ions@localhost:5432/ions
```

### 2. Start the node

```bash
docker compose up -d
```

This starts:
- PostgreSQL (port 5432) — system of record
- FastAPI backend (port 8000) — CBB registry, traversal engine, API
- Next.js frontend (port 3000) — explorer, workbench, graph

### 3. Verify the node is running

```bash
# Health check
curl http://localhost:8000/health

# Node manifest
curl http://localhost:8000/.well-known/ions-node.json

# API docs
open http://localhost:8000/docs

# Frontend
open http://localhost:3000
```

---

## Contributing Knowledge

### Via the Web Interface

1. Open `http://localhost:3000/contribute`
2. Paste text or upload a `.txt`, `.md`, or `.docx` document
3. Click **Extract CBBs** — the network identifies atomic claims automatically
4. Review and deselect any you don't want
5. Submit to the review queue
6. Approve in the Workbench

### Via the API

```bash
curl -X POST http://localhost:8000/cbb \
  -H "Content-Type: application/json" \
  -d '{
    "type": "claim",
    "domain": "organizational_intelligence",
    "content": "Shallow discovery is the most common cause of failed AI transformation.",
    "confidence": 0.85,
    "evidence": [{"source_type": "original", "source_id": "field_observation_2024"}],
    "status": "candidate"
  }'
```

### What makes a good CBB?

✓ **Good**: "Organizations that skip operational discovery produce AI requirements that don't match how work actually happens."

✗ **Too vague**: "AI is important for business."

✗ **Compound claim**: "AI fails because of bad data and poor leadership and unclear goals."

One claim. Specific enough to evaluate as true or false in context.

---

## Querying the Network

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why do institutional knowledge gaps compound over time?",
    "top_n_paths": 3,
    "max_depth": 5
  }'
```

Response includes:
- `raw_answer` — direct LLM answer without CBB context
- `cbb_answer` — answer synthesized from traversal paths
- `paths` — ordered reasoning paths with confidence scores, CBB sequences, and relationship chains

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/cbb` | Publish a CBB |
| GET | `/cbb` | Search CBBs |
| GET | `/cbb/{id}` | Retrieve a CBB |
| POST | `/cbb/{id}/deprecate` | Deprecate a CBB |
| POST | `/relationship` | Create a relationship |
| GET | `/relationship` | List relationships |
| POST | `/query` | Run traversal query |
| GET | `/path/{id}` | Retrieve a saved path |
| GET | `/path` | List saved paths |
| GET | `/health` | Node health check |
| GET | `/.well-known/ions-node.json` | Node manifest |
| GET | `/stats` | Network statistics |
| GET | `/docs` | Interactive API docs |

---

## Running Your Own Node

Every IONS node is independent. To run a node:

1. Fork this repository
2. Configure your `.env`
3. Run `docker compose up -d`
4. Seed your node with CBBs from your domain
5. Your node announces itself via `/.well-known/ions-node.json`

### Node Manifest

Your node's manifest is automatically available at:

```
GET /.well-known/ions-node.json
```

```json
{
  "node_id": "your_node_id",
  "protocol_version": "ions-genesis-0.1",
  "supported_cbb_types": ["claim"],
  "capabilities": ["publish_cbb", "publish_relationship", "query", "traverse"],
  "public_api_base": "https://your-node-url.com",
  "status": "active",
  "open_contributions": true
}
```

Update `public_api_base` in `backend/main.py` to your public URL before deploying.

### Joining the Network

Once your node is running at a public URL, register it with any existing IONS node:

```bash
curl -X POST https://known-node.example.com/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id": "your_node_id", "public_api_base": "https://your-node.example.com"}'
```

Your node will be discovered via its manifest, added to the registry, and queries on that node will automatically traverse your CBBs as part of federated paths.

---

## Generating Relationships

After publishing CBBs, generate relationships between them:

```bash
source .env
python3 generate_relationships_fast.py
```

This connects your CBBs to each other using the same LLM-powered approach used to build the Genesis network. Run multiple times to increase relationship density. Aim for 3+ relationships per CBB for strong traversal paths.

---

## Protocol Concepts

### NSI Clusters

Narrow Super Intelligence clusters are domain-specific groupings of CBBs. The graph view automatically groups your CBBs into NSIs using LLM-powered semantic clustering. As nodes contribute knowledge in new domains, new NSI clusters form organically.

### Confidence Scoring

Path confidence is computed from:

```
PathConfidence = CBB_avg × REL_avg × EvidenceScore
```

Confidence is always shown with its path and evidence — never as a context-free number.

### Relationship Types

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

---

## Project Structure

```
ions-genesis/
├── backend/
│   ├── main.py                 # FastAPI app, health, manifest
│   ├── app/
│   │   ├── api/
│   │   │   ├── cbbs.py         # CBB CRUD endpoints
│   │   │   ├── relationships.py # Relationship endpoints  
│   │   │   └── query.py        # Traversal and path endpoints
│   │   ├── models/
│   │   │   ├── schemas.py      # Pydantic validation models
│   │   │   └── artifacts.py    # SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── traversal.py    # Path enumeration and scoring
│   │   │   ├── synthesis.py    # Answer generation
│   │   │   └── hashing.py      # Canonical hash service
│   │   └── core/
│   │       ├── config.py       # Settings
│   │       └── database.py     # Async DB connection
│   └── seed.py                 # Initial seed data
├── frontend/
│   └── app/                    # Next.js pages
│       ├── page.tsx            # Explorer
│       ├── graph/              # NSI graph visualization
│       ├── contribute/         # CBB contribution
│       ├── workbench/          # Review and approval
│       ├── rights/             # Attribution (coming soon)
│       ├── node/               # Node status and manifest
│       └── settings/           # API key and model config
├── generate_relationships_fast.py  # Bulk relationship generation
├── docker-compose.yml
└── .env.example
```

---

## Protocol Status

| Feature | Status |
|---|---|
| Multi-node federation | ✅ Live — node registry, manifest, federated query |
| Server-side relationship generation | ✅ Live — `POST /relationship/generate` |
| Node manifest | ✅ Live — `GET /.well-known/ions-node.json` |
| Path registry | ✅ Live — `GET /path/{id}` |
| Rights and attribution claims | 🔬 Experimental — framework in place, claims coming soon |
| Token / reward mechanics | 🔜 Future |
| Automated relationship generation on CBB approval | 🔜 Future |
| Network-derived reputation scoring | 🔜 Future |
| Multiple CBB types (observation, procedure, outcome) | 🔜 Future — claim type proven first |

---

## Philosophy

> "The model is less important than the network. Intelligence emerges through traversal and composition, not through parameter scale alone."

IONS is built on the belief that:
- Knowledge should be durable, inspectable, and composable
- Reasoning should be visible, not opaque
- Any model should be able to participate as an interpreter
- Contributors should be able to see their knowledge being used

This is an open protocol. Fork it. Run a node. Contribute CBBs. Build on it.

---

## License

MIT

---

## Contributing

Pull requests welcome. For significant changes open an issue first to discuss what you'd like to change.

The most valuable contributions are:
1. High-quality CBBs in underrepresented domains
2. Improvements to the traversal engine
3. New relationship types with clear semantics
4. Documentation and examples