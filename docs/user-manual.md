# IONS Genesis — User Manual

A practical guide to running a node, contributing knowledge, and querying the network.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Explorer — Querying the Network](#explorer)
3. [Add CBB — Contributing Knowledge](#add-cbb)
4. [Workbench — Review and Approval](#workbench)
5. [Graph — Visualizing the Network](#graph)
6. [Node — Status and Federation](#node)
7. [Settings — API Key and Model](#settings)
8. [Generating Relationships](#generating-relationships)
9. [Joining the Network](#joining-the-network)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An [OpenRouter](https://openrouter.ai) API key — free tier available
- Node.js 18+ (for frontend development only)

### 1. Clone and configure

```bash
git clone https://github.com/nomad505050/ions-genesis.git
cd ions-genesis
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```bash
OPENROUTER_API_KEY=sk-or-your-key-here
PUBLIC_API_BASE=http://localhost:8000
NODE_DESCRIPTION=My IONS node
```

### 2. Start the node

```bash
docker compose up -d
```

This starts three services:
- **PostgreSQL** on port 5432 — system of record
- **FastAPI backend** on port 8000 — CBB registry, traversal, API
- **Next.js frontend** on port 3000 — web interface

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","node":"genesis_node"}

curl http://localhost:8000/.well-known/ions-node.json
# Returns your node manifest with capabilities and domains
```

Open `http://localhost:3000` to access the web interface.

---

## Explorer

The Explorer is the main interface for querying the network. It runs your question through both a raw LLM call and the CBB traversal engine, then shows you the difference.

### Running a query

1. Open `http://localhost:3000`
2. Type your question in the search box
3. Press Enter or click the query button
4. Wait 15-30 seconds for traversal to complete

### Reading the result

The result shows:

**CBB Traversal answer** — synthesized from the reasoning path. This answer is grounded in the CBBs that were traversed, with explicit evidence references.

**Raw LLM answer** — what the model says without CBB context. Useful for comparison.

**Confidence** — path confidence score (0-100%). This reflects:
- Average CBB confidence in the path
- Average relationship confidence
- Evidence score of the CBBs used

A confidence below 60% means the network has limited coverage of your query domain — contribute more CBBs in that area.

**Reasoning Path** — the sequence of CBBs and relationships traversed to produce the answer. Click to expand and see each step.

**Alternative paths** — other high-scoring paths the engine found. Useful for seeing different angles on your question.

### Sample queries to try

- "How does institutional memory compound competitive advantage?"
- "What are the compliance requirements for high-risk AI systems?"
- "Why do AI transformation initiatives fail early?"
- "How does Bitcoin's proof-of-work mechanism create scarcity?"
- "What is the relationship between flow states and peak performance?"

---

## Add CBB

Contributing knowledge to the network. Every CBB goes through a review queue before publication.

### Extract from a document (recommended)

The fastest way to contribute is to upload a document and let the network extract CBBs automatically.

1. Go to **Add CBB** in the sidebar
2. The **Extract from document** tab is selected by default
3. Either:
   - Click **↑ Upload file** and select a `.txt`, `.md`, or `.docx` file
   - Paste text directly into the text area
4. Fill in **Source type** (book, paper, article, etc.) and **Source reference** (title or URL)
5. Click **Extract CBBs →**
6. Review the extracted candidates — each shows the claim, assigned domain, and confidence score
7. Deselect any claims that are too vague, compound, or unsupported
8. Click **Submit X CBBs to review queue**

The system processes up to 24,000 characters across 6 chunks. For large documents, paste the most relevant sections.

### What makes a good CBB?

**Good CBBs are:**
- One atomic, assertable claim
- Specific enough to evaluate as true or false in context
- Supported by the source material
- Useful for reasoning about a topic

**Examples of good CBBs:**
> "Organizations that automate without operational discovery build on incorrect assumptions."

> "The EU AI Act applies to any company deploying AI within the EU, even if they are based elsewhere."

> "Flow states require a challenge-to-skill ratio of approximately 1:1 to sustain."

**Avoid:**
- Vague summaries: *"AI is important for organizations"*
- Compound claims: *"AI fails because of bad data and poor leadership and unclear goals"*
- Opinions without evidence: *"This is the best approach"*

### Add a single claim

Use the **Add single claim** tab for precise manual entry when you have one specific claim to add.

1. Type the claim in the text area
2. Add source type and reference
3. Click **Submit to Review Queue**

Domain and confidence are auto-assigned by the LLM if you have an API key configured in Settings.

---

## Workbench

The Workbench is where submitted CBBs are reviewed and approved before entering the network.

### Review Queue

All submitted CBBs land in the review queue as candidates. Each shows:
- The claim content
- Auto-assigned domain
- Confidence score
- Source type and timing

**Approve** — posts the CBB as published to the network and deprecates the candidate. The CBB immediately becomes available for traversal.

**Reject** — deprecates the candidate. It will not appear in traversal.

Review carefully before approving:
- Is the claim atomic? (one assertion only)
- Is it specific enough to be evaluated?
- Does the domain assignment make sense?
- Is the confidence appropriate for the evidence?

### Published Tab

Shows recently published CBBs sorted by newest first. Useful for seeing what's live in the network.

### Activity Tab

Shows the network pipeline status:
- **In review queue** — submitted, awaiting approval
- **Published** — live on the network

The **Generate Relationships** button connects recently published CBBs to existing network knowledge. Run this after approving a batch of CBBs to integrate them into the traversal graph.

---

## Graph

The Graph visualizes the network as NSI (Narrow Super Intelligence) clusters connected by relationship lines.

### NSI Clusters

NSI clusters are semantic groupings of CBB domains, computed automatically by the LLM. For example:
- **Economics & Finance** — contains `monetary_economics`, `macroeconomics`, `fintech`, `behavioral_economics`
- **AI Regulation & Policy** — contains `ai_regulation`, `gdpr_compliance`, `ai_transparency`
- **Peak Performance** — contains `peak_performance`, `flow`, `human_performance_and_resilience`

Bubble size reflects CBB count. Larger bubbles have more knowledge in that cluster.

### Connection lines

Lines between clusters indicate actual relationships between CBBs in different domains. Thicker, brighter lines mean more cross-domain relationships. This shows you where the network has rich cross-domain reasoning capability.

### Navigating

1. **Hover** over a cluster to see its name, CBB count, and sub-domain count
2. **Click** a cluster to drill into its sub-domains
3. **Click** a sub-domain to see individual CBBs
4. **Click** a CBB to see its full content and confidence
5. Use the **Filter** box to find specific clusters or CBBs by keyword
6. Click **↻ Regroup** to re-run LLM grouping after adding new domains

### Understanding the layout

The largest cluster is positioned in the center. Other clusters orbit it, sized by CBB count. Clusters with many cross-domain relationships will have many visible connection lines.

---

## Node

The Node page shows your node's status, statistics, and federation state.

### Node stats

- **Published CBBs** — total CBBs live on the network
- **NSI Clusters** — number of knowledge clusters (updates when you visit the Graph page)
- **Avg Path Confidence** — average confidence across saved reasoning paths

### API Endpoints

Shows which protocol endpoints are live on your node. All endpoints marked **live** are accessible at `http://localhost:8000`.

The interactive API docs are at `http://localhost:8000/docs`.

### Node Manifest

Your node announces its capabilities at:
```
GET /.well-known/ions-node.json
```

This includes your node ID, supported domains, CBB count, and capabilities. Other nodes use this to discover what knowledge your node holds.

### Registered Nodes

Shows other IONS nodes that have registered with your node. When nodes are registered, queries automatically traverse all connected nodes and merge the results.

---

## Settings

Configure your API key, model, and node URL.

### OpenRouter API Key

Required for:
- CBB extraction from documents (Contribute page)
- Server-side relationship generation (Workbench)
- NSI cluster grouping (Graph page)

Get a free key at [openrouter.ai](https://openrouter.ai). Set it in `.env` as `OPENROUTER_API_KEY` for server-side use, or in Settings for client-side extraction.

### Model Selection

IONS is model-agnostic. Any model available on OpenRouter works. Recommended options:

| Model | Use case |
|---|---|
| `meta-llama/llama-3.1-8b-instruct` | Default — fast, low cost, proves the thesis |
| `meta-llama/llama-3.1-70b-instruct` | Better extraction quality |
| `anthropic/claude-sonnet-4-5` | Highest accuracy, higher cost |
| `mistralai/mistral-7b-instruct` | Alternative lightweight |
| Custom | Any OpenRouter model string |

The model choice affects extraction quality and relationship suggestion accuracy. It does not affect the CBBs or relationships already in the network.

### IONS Node URL

Default is `http://localhost:8000`. Change this to point to a remote node if you want to query a different node's knowledge.

---

## Generating Relationships

Relationships are what connect CBBs into a traversable network. Without relationships, CBBs are isolated claims that cannot form reasoning paths.

### From the Workbench

1. Go to **Workbench → Activity tab**
2. Click **⬡ Generate relationships**
3. Watch the progress bar — the backend processes CBBs in batches, calling the LLM to find meaningful connections
4. The done message shows how many relationships were created

Run this after approving a batch of new CBBs. The system prioritizes CBBs with fewer than 10 relationships, so each run expands coverage evenly.

### Via API

```bash
curl -X POST http://localhost:8000/relationship/generate
# Returns: {"job_id": "abc123", "status": "running"}

curl http://localhost:8000/relationship/generate/abc123
# Returns progress and final count
```

### How many relationships do I need?

- **< 2 per CBB** — very sparse, traversal will find few paths
- **3-5 per CBB** — functional, paths exist but confidence may be low
- **6-10 per CBB** — good density, strong multi-hop paths
- **10+ per CBB** — rich network, high confidence traversal

---

## Joining the Network

Once your node is running at a public URL, it can participate in the federated IONS network.

### Make your node public

1. Deploy your node to a server with a public URL
2. Update `PUBLIC_API_BASE` in `.env` to your public URL:
   ```bash
   PUBLIC_API_BASE=https://your-node.example.com
   ```
3. Rebuild: `docker compose up -d --build api`

### Register with another node

```bash
curl -X POST https://known-node.example.com/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id": "your_node_id", "public_api_base": "https://your-node.example.com"}'
```

The remote node will fetch your manifest, verify your node is live, and add you to its registry. Queries on that node will now traverse your CBBs automatically.

### Ask others to register with you

Share your registration endpoint:
```
POST https://your-node.example.com/nodes/register
```

Any node that registers with you will have their CBBs included in your traversal queries.

### Check registered nodes

```bash
curl http://localhost:8000/nodes
```

---

## Troubleshooting

### Node won't start

```bash
cd ions-genesis
docker compose logs api --tail 20
```

Common causes:
- Missing `.env` file — copy `.env.example` to `.env`
- Database not ready — wait 10 seconds and retry
- Port conflict — change ports in `docker-compose.yml`

### No paths returned for a query

The network needs CBBs and relationships in the relevant domain. Check:
1. Are there published CBBs related to your query? Search in the Graph.
2. Do those CBBs have relationships? Check relationship count in Node stats.
3. Run Generate Relationships in the Workbench.

### Low path confidence (below 60%)

- Add more CBBs with strong external evidence references
- Run Generate Relationships to increase network density
- Try a more specific query that matches your CBB domains

### Extraction returns fewer CBBs than expected

- Document may be longer than 24,000 characters — paste in sections
- Try a different model in Settings (70B models extract more precisely)
- Some documents contain more narrative than assertable claims

### Generate Relationships creates 0 new relationships

Most CBBs already have 10+ relationships. This means the network is well-connected in those domains. Add CBBs in new domains to expand coverage.

### API key errors

- Verify key is set in Settings
- Check key is valid at openrouter.ai
- Ensure the selected model is available on your OpenRouter plan

---

## API Reference

Full interactive docs at `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/cbb` | Publish a CBB |
| GET | `/cbb` | Search CBBs |
| GET | `/cbb/{id}` | Get a CBB |
| POST | `/cbb/{id}/deprecate` | Deprecate a CBB |
| POST | `/relationship` | Create a relationship |
| POST | `/relationship/generate` | Start relationship generation |
| GET | `/relationship/generate/{job_id}` | Poll generation status |
| POST | `/query` | Run traversal query |
| GET | `/path/{id}` | Get a saved path |
| GET | `/path` | List saved paths |
| POST | `/nodes/register` | Register a node |
| GET | `/nodes` | List registered nodes |
| POST | `/nodes/{id}/ping` | Health check a node |
| GET | `/health` | Node health |
| GET | `/stats` | Network statistics |
| GET | `/.well-known/ions-node.json` | Node manifest |
