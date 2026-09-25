# Behailu Weldeyohannes

**AI Engineer — LLM orchestration, RAG, and GPU inference on self-hosted models**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/behailu-weldeyohannes)
[![Open Source](https://img.shields.io/badge/Open_Source-Addis--Pulse--Studio-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Addis-Pulse-Studio)

---

## About

I build AI systems on the assumption that generation fails. Models time out, return
schema-breaking JSON, and crash mid-batch — so the engineering that matters is in what happens
next: provider-agnostic gateways that reroute automatically, retrieval pipelines that refuse
rather than guess, agent layers that validate a plan before executing it, and GPU admission
control that stops incompatible models colliding on one card.

Ten years across software, data and analytics; the last three building production LLM systems.
I also hold a Georgetown LL.M. and write about model licensing, training-data provenance, and the
copyright litigation reshaping how these systems get built.

**Currently:** running self-hosted generative pipelines on a single 32 GB GPU, and publishing
ComfyUI extensions under Apache-2.0.

---

## Open source

Public work lives under the **[Addis-Pulse-Studio](https://github.com/Addis-Pulse-Studio)** org.

### [ComfyUI-HyperFlow](https://github.com/Addis-Pulse-Studio/ComfyUI-HyperFlow) · Apache-2.0

An 8-step sampling adapter porting HyperFlow's two-time LoRA onto ComfyUI's **native** MiniMax H3
model rather than diffusers — work at the weight level, not API integration.

- Maps diffusers/PEFT LoRA parameter naming to ComfyUI targets across **314 locations**, applying
  q/k/v as row-slice patches of a fused `qkv_proj`
- Builds a separate fp32 endpoint time-embedder from unpatched checkpoint weights and patches
  `time_embedder.forward`, deriving each timestep's endpoint from the sampler's sigma schedule —
  the value ComfyUI's sampler loop never passes on its own
- Refuses pruned checkpoints with a baked `adaln_t_table` and rejects multi-stage samplers that
  would silently break interval conditioning
- Verified on an RTX 5090: audio/video envelope correlation of **+0.974 and +0.980 at 0 ms lag**
  against a +0.136 unrelated-audio control

**9 nodes** · Cited by [ComfyUI-Wiki](https://comfyui-wiki.com) as the node pack reproducing
HyperFlow's endpoint conditioning in ComfyUI.
*HyperFlow the technique and LoRA are Video Rebirth's; this is an independent ComfyUI-native
implementation.*

### [ComfyUI-PulseStudio](https://github.com/Addis-Pulse-Studio/comfyui-pulse-studio) · Apache-2.0

Shot-timeline direction for MiniMax H3 — write `@Mimi`, not `<Picture 3>`.

- **Zero runtime dependencies.** The 22-module core is stdlib-only and torch-free, and an
  **AST-walking test fails the build** if torch, comfy or folder_paths reach it
- A second AST test enforces **zero network egress** — it's a property users are told about, so it
  has to be one the build can prove, not a habit that lasts until the first convenient
  `requests.get`
- Timeline compiler quantises render windows to H3's 17k+5 frame grid with tested correctness
  properties: no reference ordinal is ever stored, so reordering assets cannot desynchronise
  prompt text from sockets
- CI is a 3-version Python matrix that invokes JS tests **directly**, so a missing runtime fails
  instead of silently skipping

**9 nodes** · **882 Python tests + 3 JS suites** · Distributed via the
[Comfy.ICU registry](https://comfy.icu/extension/Addis-Pulse-Studio__comfyui-pulse-studio)

---

## Selected private work

These are client and production systems, so the repositories aren't public. Happy to walk through
architecture and code in a conversation.

| System | What it does | Scale |
|---|---|---|
| **Addis Pulse Publishing** | Editorial automation: 109 RSS sources → research → writing → SEO → validation → git-based publishing, on a 10-node LangGraph state machine with SQLite checkpointing | **67 articles published unattended** · ~94,000 first-party Python lines · 2,227 tests · 5 CI jobs |
| **OMNI Content Engine** | FastAPI orchestration gateway for self-hosted generative engines; 100% local inference, no cloud model dependency | 33 routes · 14 abstract ports · **89.5% coverage** · mypy strict · 19 ADRs · layering enforced by AST tests |
| **ChannelBoostAI** | Multi-tenant YouTube analytics SaaS — Google OAuth, Stripe subscription billing with signature-verified webhooks, per-user quotas | 5-table Postgres · 8 Alembic migrations · non-root Docker · deployed to Render + Vercel |
| **ClarityHealth** | Regulatory intelligence over US/EU healthcare law — 17 purpose-built scrapers with SHA-256 change detection, LLM structured extraction, Postgres full-text retrieval | **91,491 rows** across GDPR, EU MDR, HIPAA, CMS, FDA and 6 state privacy statutes |
| **Pathfinder AI** | Retrieval-augmented immigration assistant — multi-format ingestion, recursive chunking, persistent ChromaDB, grounded prompting that refuses unsupported answers | LangChain · sentence-transformers · KMeans clustering over embeddings · 3-service Docker Compose |
| **PulseDyno** | Benchmark harness for local LLMs — a dynamometer for language models | 9-table schema whose **10 triggers enforce append-only results** · mypy strict · 15 CLI commands |

---

## Engineering approach

A few decisions that recur across these systems, because they're the ones that actually held up:

- **Make invariants executable.** If a property matters, a test should fail the build when it
  breaks — AST import-graph gates, zero-egress scans, config-policy suites — rather than living in
  a comment.
- **Name the failure.** A schema violation and an unreachable model need different fixes, so they
  get different exception types and different log lines. Collapsing them wastes the next debugging
  session.
- **Serialise structurally, not by convention.** GPU contention doesn't get solved by everyone
  remembering to take turns; it gets solved by a lease every stage must hold.
- **Degrade, don't die.** Losing a telemetry frame must never kill a render that's been running
  ten minutes.

---

## Stack

**Languages** Python · TypeScript · JavaScript · SQL · Bash

**LLM & RAG** LangGraph · LangChain · LlamaIndex · Model Context Protocol (MCP) · ChromaDB ·
sentence-transformers · Anthropic · OpenAI · Google Gemini · Ollama · OpenRouter

**Backend** FastAPI · pydantic v2 · SQLAlchemy 2.0 async · Alembic · PostgreSQL · Typer ·
WebSockets

**GPU & systems** CUDA/VRAM lifecycle management · NVML · nvidia-smi telemetry · single-model
residency · subprocess isolation · diffusion-model internals

**Frontend** React 19 · Next.js 16 · Tailwind · Vite

**Infra & quality** Docker · GitHub Actions · AWS · GCP · Vercel · Render · pytest · mypy strict ·
ruff · coverage

---

## Writing

I author a technical AI/ML publication — **67 articles** on model releases and inference
engineering (MoE architectures, hybrid attention, quantization-aware distillation), speech
systems, low-resource-language modelling including Amharic, and AI law and policy.

**Publication:** Behailu T. Weldeyohannes, *Reforming Prison Policy to Improve Women-Specific
Health and Sanitary Care Conditions of Prisons in Ethiopia*,
[24 Wm. & Mary J. Women & L. 101 (2017)](https://scholarship.law.wm.edu/wmjowl/vol24/iss1/5/).

---

<sub>Open to conversations about LLM infrastructure, retrieval systems, and self-hosted inference —
reach me on [LinkedIn](https://linkedin.com/in/behailu-weldeyohannes).</sub>
