Processing video: 3JYHMMw5WSU
Retrieved 2826 transcript segments
Analyzing with gpt-5.2-pro (seed mode)...
Testing API connectivity with gpt-5.2-pro...
API ready. Using model: gpt-5.2-pro
Note: gpt-5.2-pro is a reasoning model and may take 5-10 minutes for complex analysis.

============================================================
Analysis (SEED)
============================================================

# SEED DOCUMENT — ERC3 Enterprise Agent System (Transcript-Derived)

> Source: Interview transcript (Russian) about an **Enterprise Rock Challenge (ERC3)** agent solution that achieves strong results on an **open model (GPT-OSS-120B)**. The discussion focuses on **context engineering**, **dynamic policy routing**, **tool/API orchestration**, and **reliability controls** (validator, reduced steps, trimmed history).  
> If something is not explicitly present in the transcript, it is marked **“Not discussed in video.”**

---

## 1. EXECUTIVE SUMMARY

### Main topic & purpose
- Building a **production-like enterprise agent** for ERC3 (Enterprise Rock Challenge), where an agent must solve realistic company tasks using many APIs under **access-control rules**.
- Demonstrates how strong performance can be achieved **even on a smaller/open model** via:
  - rigorous **context management**
  - dynamic rule routing
  - minimized agent steps
  - validation layers

### Key problem being solved
- **Enterprise agent reliability under constraints**:
  - Many tools/APIs (≈20–24) with different syntaxes and quirks.
  - Complex **authorization / access rules**: agent can see everything, but must only disclose what the *requesting user* is allowed to see.
  - High chance of error due to:
    - long instruction sets (rules/policies)
    - noisy context
    - multi-step compounding error probability
    - pagination/latency constraints in APIs

### Primary solution approach
- Treat agent-building as **context engineering**:
  - **Pre-ingest** company wiki rules and route only relevant rule subsets into the system prompt.
  - Build **dynamic user-context blocks** and select only relevant ones before agent loop.
  - Use a **Plan+ReAct style structured loop** (state → plan → action → function).
  - Add an **LLM validator** (“second pair of eyes”) to catch/redirect bad actions.
  - Reduce compounding error by **minimizing the number of tool calls/steps**.
  - Aggressively **trim conversation history** to only what’s needed.

---

## 2. ARCHITECTURAL PATTERNS & DECISIONS

### 2.1 “Enterprise Benchmark as a Company Simulation” (Problem Architecture)
**Description**
- ERC3 provides a simulated company environment:
  - Company Wiki (markdown articles): behavioral rules + employee/project info.
  - Entities: employees, projects, clients, time logs, permissions.
  - Tools/APIs: ~20–24 endpoints with different contracts.

**Why chosen / trade-offs**
- Not a choice by implementer; it defines constraints:
  - Forces realistic enterprise concerns (RBAC-like constraints, auditability, operational workflows).

**How it works**
- Agent receives tasks + can call APIs + must comply with wiki-defined policy rules.

**Benefits**
- Realistic evaluation of enterprise agent patterns.

**Limitations**
- “Fuzzy logic” access enforcement: agent *can* access data, but must self-restrict → prompt-injection and policy-following robustness are critical.

---

### 2.2 Dynamic System Prompt Assembly (“Rule Routing”)
**Pattern name**
- **Dynamic Policy Routing / Selective System Prompt**

**Description**
- Instead of stuffing *all* wiki rules into the system prompt, rules are:
  - extracted once per wiki version (using wiki hash)
  - clustered and routed based on user type (authorized vs public)
  - selectively injected into system prompt per task

**Why it was chosen (trade-offs)**
- Chosen because “all rules in context doesn’t scale”:
  - Too many rules → low signal-to-noise → weaker compliance.
- Trade-off: more engineering complexity; rule extraction needs to be correct.

**Implementation approach**
- Pre-step (“prep” executed once per wiki hash):
  - iterate over wiki rule pages
  - extract rules aimed at agent behavior
  - store rule clusters:
    - for **authorized users**
    - for **public users**
    - for **response formatting** (kept separate; loaded only when needed)

**Benefits**
- Higher precision and instruction-following.
- Lower context noise (“cognitive capacity” / signal-to-noise improvement).

**Limitations**
- Requires robust rule extraction.
- If routing is wrong/incomplete, agent may violate policy or refuse valid requests.

---

### 2.3 Context Builder + Context Selector (Pre-Agent Context Engineering)
**Pattern name**
- **Pre-Agent Context Harvesting + LLM-based Context Selection**

**Description**
- Before the main agent loop begins:
  - fetch all data related to the requester (projects, clients, logs, profile, etc.)
  - then run a **context selector** LLM call to keep only relevant blocks for the task

**Why chosen (trade-offs)**
- Prevents passing huge irrelevant user-related context to the main agent.
- Trade-off: one extra LLM call up-front; must ensure selector doesn’t drop critical info.

**Implementation approach**
1. Call `HMI` endpoint to identify user + wiki hash.
2. Programmatically fetch related entities (often in parallel).
3. Feed:
   - task text
   - “raw context blocks” related to the user  
   into a **context selector** LLM prompt: “choose what is relevant”.

**Benefits**
- Reduced number of agent steps (agent already has key IDs and entities).
- Lower error rate due to less noise.

**Limitations**
- Selector mistakes can hide needed data (mitigated by being “slightly greedy” and letting agent ignore irrelevant blocks).

---

### 2.4 Parallelized Data Fetch (Latency-Aware Orchestration)
**Pattern name**
- **Parallel API Calls during Preparation**

**Description**
- Preparation stage performs multiple independent API calls in parallel.

**Why chosen (trade-offs)**
- ERC3 includes simulated API latency (~300ms). Sequential calls would be too slow.
- Trade-off: more concurrency complexity, but straightforward for independent fetches.

**Implementation approach**
- Fetch projects, clients, logs, profile, etc. concurrently.

**Benefits**
- Lower wall-clock time per task.

**Limitations**
- Concurrency control and error handling are required (not deeply discussed).

---

### 2.5 API Wrapper Layer (Autopagination + Tool Simplification)
**Pattern name**
- **Tool Contract Normalization / Wrapper APIs**

**Description**
- ERC APIs use pagination with small page size (max 5) and unclear limits.
- A wrapper hides pagination parameters from the agent.

**Why chosen (trade-offs)**
- Prevents the agent from burning many calls and making mistakes with pagination.
- Trade-off: extra code and maintenance; wrapper must be correct.

**Implementation approach**
- Implement an **autopaginator**:
  - iteratively fetch pages until completion
  - return aggregated results
- Expose “simplified” tools to agent (pagination fields removed).

**Benefits**
- Fewer tool calls inside agent loop.
- Less prompt space spent explaining pagination.
- Reduced failure modes.

**Limitations**
- Potential for high load if entity counts large (not discussed how capped).

---

### 2.6 Plan + ReAct Hybrid Agent with Structured Output (SGR-Style)
**Pattern name**
- **Plan-ReAct Structured Loop (state/plan/action/function)**

**Description**
- The main agent produces structured fields:
  - `state`: summary of what’s known
  - `plan`: remaining steps
  - `action`: immediate next step (more detailed)
  - `function`: which tool to call + params

**Why chosen (trade-offs)**
- Provides consistency (“business apps need consistency”).
- Enables deterministic parsing and execution (via Pydantic).
- Trade-off: design complexity; may be less flexible than free-form tool calling.

**Implementation approach**
- LLM returns these fields each turn.
- Code parses `function` via **Pydantic objects** and executes tool call.
- Not using native “tool calling” interface; uses **structured output** approach.

**Benefits**
- More controllable loop.
- Easier to validate and debug.
- Better stability than ad-hoc tool calling (per speaker’s experience).

**Limitations**
- Requires careful prompt/schema design.
- Still can skip checks (e.g., not verifying post-update status).

---

### 2.7 Deferred “Response Rules” Loading via a Pseudo-Tool
**Pattern name**
- **Just-in-Time Instruction Retrieval**

**Description**
- Response formatting rules are large, so they are not always in context.
- Agent is instructed: before final response, call a pseudo-tool to load response instructions.

**Why chosen (trade-offs)**
- Keeps context clean until response time.
- Trade-off: introduces an additional step and a new failure mode (agent may forget).

**Implementation approach**
- Provide pseudo-tool like “load_response_instructions”.
- Agent calls it only when ready to respond.

**Benefits**
- Reduced context noise for earlier reasoning/tool use.

**Limitations**
- Agent sometimes forgets → validator needed to enforce ordering.

---

### 2.8 LLM Validator (“Second Pair of Eyes”)
**Pattern name**
- **LLM Action Validator / LLM-as-Judge**

**Description**
- Before executing the agent’s requested tool, a validator LLM checks:
  - task + rules + context + proposed action
  - returns approve/deny with feedback

**Why chosen (trade-offs)**
- Multi-step agents accumulate error probability.
- Validator reduces action-level errors without overloading main system prompt.
- Trade-off: extra LLM calls; validator can also be wrong (false reject/false accept).

**Implementation approach**
- Validator sees **same info as agent** (no extra privileges).
- If denied:
  - validator provides feedback
  - agent retries with that feedback
- Validator can be disabled in config.
- Validator denial attempts may be capped (mentioned: limited number of denials, then allow).

**Benefits**
- Catches common workflow mistakes (e.g., trying to respond before loading response rules).
- Improves reliability with smaller/cheaper models.

**Limitations**
- Not perfect; can miss mistakes or block correct steps.
- Adds latency and complexity.

---

### 2.9 Conversation History Trimming (“Only Keep What Matters”)
**Pattern name**
- **Aggressive Context Window Pruning / Minimal History**

**Description**
- Agent does not see full prior reasoning fields.
- Store and send only:
  - which tool was called (1-line)
  - tool result summary/response
- Failed attempts blocked by validator are not included in history.

**Why chosen (trade-offs)**
- Prevents “context pollution” from old plans/states and failed branches.
- Trade-off: agent loses potentially useful reflection, but net benefit is reduced confusion.

**Implementation approach**
- Keep a compact “tool-call trace” instead of full chain-of-thought-like outputs.
- Ignore invalid branches entirely; only successful path is preserved.

**Benefits**
- Higher signal-to-noise.
- Lower compounding confusion from earlier wrong paths.
- Lower token usage.

**Limitations**
- Less transparency for the agent; debugging requires external tracing (which the author provides).

---

### 2.10 Multi-Agent Orchestrator Pattern (Store Benchmark Agent)
**Pattern name**
- **Orchestrator + Specialist Sub-Agents (“Workers”)**

**Description**
- In the “store benchmark” (warm-up benchmark), architecture is:
  - **Orchestrator** agent (manager) has *no raw SDK tools*.
  - Orchestrator calls **pseudo-tools**, each representing a specialist sub-agent.
  - Specialists have limited tool subsets and tight prompts.
  - Specialists return compact reports; orchestrator doesn’t see their internal traces.

**Why chosen (trade-offs)**
- Reduces orchestrator context load.
- Enforces specialization (each sub-agent knows only relevant tools).
- Trade-off: coordination overhead; additional agent calls.

**Implementation approach**
- Orchestrator delegates tasks like product lookup, coupon evaluation, basket building.
- Sub-agents call real SDK endpoints.
- Validator can exist “over the shoulder” of orchestrator.

**Benefits**
- Strong context isolation.
- Cleaner decision-making at the top level.

**Limitations**
- More moving parts; failure in a sub-agent can block overall success.

---

## 3. KEY INSIGHTS & TAKEAWAYS

### Technical insights (numbered)
1. **Context engineering dominates**: most effort is ensuring the model sees *only* relevant rules and data (precision > recall in prompts).
2. **Don’t dump all rules into the system prompt**; instead **route rules dynamically** (authorized vs public, plus separate response rules).
3. **Pre-fetch user-linked entities in code**, then use an LLM **context selector** to choose relevant blocks for the task.
4. **Parallelize independent API calls** to overcome simulated latency and keep runtime practical.
5. **Hide API quirks (pagination)** behind wrappers so the agent operates on simplified tool contracts.
6. **Structured output Plan+ReAct** improves consistency versus free-form tool calling (in the author’s experience).
7. **Defer large instruction blocks** (response rules) until needed via a pseudo-tool.
8. **Validator LLM** can materially reduce action errors by providing targeted feedback without bloating the main prompt.
9. **Trim history aggressively**: keep “tool called + tool result”; omit prior plans/states and omit invalid branches entirely.
10. **Reduce number of steps**: compounding error probability is a core failure mode in agents; fewer calls often beat “smarter reasoning”.

### Strategic insights
- **Open models can compete** with top proprietary agents when paired with strong orchestration/context design.
- In enterprise settings, open models are attractive due to:
  - deployment control (on-prem/self-host)
  - potentially large cost advantages at scale

### Lessons learned
- Benchmarks can be manipulated; treat them skeptically and prefer **your own evaluations**.
- More rules is not always better; too many constraints can overwhelm smaller models.
- Reliable systems require “nailing things down” (structured outputs, guardrails) rather than hoping the model “figures it out”.

### Best practices mentioned
- Use **dynamic rule/context routing** to avoid noise.
- Use **XML tags** to clearly delimit blocks (start/end), preferred over messy markdown for prompt structure.
- Provide **developer-friendly artifacts**:
  - open-source code
  - README with run instructions
  - trace visualizer for debugging

---

## 4. TERMINOLOGY & KEYWORDS

### Core concepts
- **ERC / ERC3 (Enterprise Rock Challenge)**: competition simulating enterprise agent tasks with many APIs and policies.
- **Agent loop / agent “petlya”**: iterative cycle of model outputs → tool calls → tool results → next model step.
- **Context engineering**: managing what information enters the model context to maximize relevance and reduce noise.
- **System prompt**: high-priority instruction block controlling global agent behavior.
- **User prompt**: task + relevant dynamic context blocks fed as user message.
- **HMI / “Who am I” endpoint**: API call that identifies the requester (employee/guest), gives metadata and wiki hash.
- **Wiki hash**: version identifier for the company wiki; enables caching pre-processing results.
- **RBAC-like rules**: authorization logic (who can see salaries, project info, etc.). In ERC3 it’s “fuzzy” because enforcement is prompt-based.
- **Prompt injection**: attempts to manipulate the agent to reveal unauthorized info.

### Agent architecture terms
- **Plan+ReAct**: hybrid approach combining planning and step-by-step actions with tool calls.
- **Structured output**: model output constrained to a schema (fields like state/plan/action/function), parsed programmatically.
- **Tool calling / function calling**: native model capability to select and call tools (discussed but not used in this solution).
- **Validator**: separate LLM that approves/blocks the main agent’s next action and provides feedback.
- **Orchestrator**: manager agent that delegates to specialist agents (sub-agents).
- **Pseudo-tool**: tool that does not map to a real SDK endpoint but triggers internal logic (e.g., load response rules; call a sub-agent).

### Engineering terms
- **Pagination**: API returns entities in pages; here max page size was effectively 5, discovered by error.
- **Autopaginator**: wrapper that iterates through pages and aggregates results.
- **Parallelism**: running independent API calls concurrently to reduce latency.
- **Signal-to-noise ratio**: relevance of provided context vs distracting information.
- **Pydantic**: Python library for schema validation/structured parsing of model outputs.

### Models and names mentioned
- **GPT-OSS-120B**: open model used; noted for fast reasoning on provider (“серебр…” likely a platform).
- **Opus / Sonnet**: top proprietary model families referenced as competition.
- **Gemini 3 Pro**: referenced in benchmark skepticism discussion.
- **GPT “5.x Thinking” / OP 4.5**: mentioned as examples to test in your own evaluations.

---

## 5. IMPLEMENTATION RECOMMENDATIONS

### Step-by-step approach (as described)
1. **Prep phase (run once per wiki hash)**
   - Download/ingest wiki markdown pages.
   - Extract and cluster rules into:
     - authorized-user rules
     - public-user rules
     - response-format rules
2. **Per-task initialization**
   - Call **HMI** to identify requester (employee/guest), role/metadata, and wiki hash.
   - Choose correct rule cluster (authorized vs public).
3. **Context harvesting (programmatic)**
   - In parallel, fetch user-linked entities:
     - projects, clients, time logs, full profile, etc.
   - Use wrappers/autopagination to avoid tool-level pagination complexity.
4. **Context selection (LLM)**
   - Feed task text + raw context blocks.
   - Ask model to select relevant blocks (IDs).
5. **Main agent loop (Plan+ReAct structured output)**
   - Provide:
     - dynamic system prompt (rules + tool contracts)
     - user prompt (task + selected context blocks)
   - Parse output fields: `state`, `plan`, `action`, `function`.
   - Execute requested function via Pydantic-validated params.
6. **Validator gate (optional but recommended)**
   - Before tool execution, ask validator to approve/deny.
   - If denied, inject validator feedback and retry.
7. **Response phase**
   - Before final response, require calling pseudo-tool to load response rules.
   - Final tool: `respond` (terminal action) including links/references (IDs) used.
8. **History management**
   - Store only compact tool call + result summaries.
   - Exclude validator-blocked attempts from history.

### Tools & technologies recommended (explicitly mentioned)
- **Pydantic** for structured output parsing/validation.
- **Cursor** (used to build a small web app/visualizer).
- **GitHub Pages** to host trace visualizer.
- **XML-like tags** in prompts for clean delimiting.

### Configuration / setup notes from transcript
- Wiki prep phase is cached by **wiki hash**.
- Validator can be toggled off in settings.
- Reasoning effort:
  - Medium used broadly
  - High/max used for one-time wiki rule extraction (quality-critical)
- Use parallel API calls due to simulated 300ms latency.

### Code patterns / examples discussed (conceptual)
- **Wrapper pattern**: remove pagination args from agent-facing tools; handle in code.
- **Pseudo-tool pattern**: “load_response_instructions” called only when needed.
- **Terminal tool pattern**: always end with `respond` tool.
- **Context pruning pattern**: tool name + tool result only; drop plans/states and invalid branches.

---

## 6. EVOLUTION & ITERATIONS

### How the solution evolved
- Started from organizer-provided simple baseline agent.
- Iterated into a more robust architecture:
  - rule extraction + routing (dynamic system prompt)
  - context prefetch + LLM context selector
  - wrappers for pagination pain
  - structured plan/react loop (schema-based)
  - validator to reduce missteps
  - aggressive history trimming

### Iterations / versions mentioned
- **ERC2**: earlier challenge (RAG system) where author also won; similar principle: shortlist candidates then let LLM choose.
- **ERC3**: main subject (enterprise agent + policies).
- **Store benchmark / warm-up benchmark**: separate benchmark with different tools and a **multi-agent orchestrator** approach.

### What didn’t work and why (explicitly mentioned)
- Putting **all rules** into system prompt:
  - doesn’t scale
  - overwhelms smaller models
- Pagination as-is:
  - page size max not documented (learned only via errors)
  - too many calls would be required (e.g., 100 entities → 20 calls)
- Benchmarks as a truth source:
  - can be manipulated; the author cited an example where metric reporting can be misleading

---

## 7. DEVELOPMENT ROADMAP

### Suggested next steps (implied by discussion)
- **Tool filtering** (dynamic subset of tools per task):
  - author considered it but didn’t implement due to time
  - likely improves signal-to-noise further
- Improve **post-action verification**
  - e.g., after update call, fetch entity again to confirm (agent didn’t always do this)
- Extend evaluation harness
  - author ran repeated runs on difficult tasks; formalize and persist metrics

### Future improvements mentioned
- More granular rule routing (“split rules into more atomic chunks and assemble more cleverly”).
- Faster / cheaper multi-call patterns enabled by open/fast inference.

### Areas for further research (directly aligned to transcript)
- Empirical comparison of:
  - native function calling vs prompt-based structured output
  - validator strategies and failure modes
- Better ways to measure and control “cognitive load” / instruction overload.

---

## 8. REFERENCES & RESOURCES

### Repositories / artifacts (mentioned)
- **Open-source GitHub repository** of the agent solution (link referenced in conversation; not included in transcript text).
- **GitHub Pages trace visualizer** showing benchmark traces and internal steps.

### Tools, libraries, frameworks mentioned
- **Pydantic** (structured parsing/validation of the `function` field)
- **Cursor** (used to build a web visualizer)
- **GitHub Pages**

### External resources referenced
- **Habr article** (author mentions a Russian/English article for prior winning solution; exact URL not in transcript)
- **arXiv** (recommended for reading benchmark papers directly)
- Prompt formatting recommendations:
  - **Anthropic-style XML tags** (and also said OpenAI has similar guidance)
- Benchmark name mentioned:
  - **BFCL** (brought up by interviewer; author not familiar, but it appears in discussion)

### Related topics to explore
- Context engineering patterns for enterprise LLM apps
- LLM-as-judge / action validation patterns
- Multi-agent orchestration (orchestrator + specialists)
- Tool contract normalization (wrappers, pagination abstraction)
- Policy compliance under prompt injection pressure

---

If you want, I can convert this SEED DOCUMENT into:
- a **PRD + Technical Design Doc** bundle (with explicit interfaces, sequence diagrams, failure modes), or
- a **backlog** (epics → stories → acceptance criteria) specifically for implementing an ERC3-like enterprise agent in production.
