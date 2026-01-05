
============================================================
Analysis (SEED)
============================================================

# SEED DOCUMENT — Enterprise Agent System (ERC3-style)  
_Source: provided interview transcript (Russian)._

---

## 1. EXECUTIVE SUMMARY

### Main topic & purpose
- Building a **high-performing enterprise agent** for the **Enterprise RAG/Agent Challenge (ERC3)** that can solve realistic company tasks using:
  - many heterogeneous **API tools**,
  - a **company “Wikipedia” knowledge base** (markdown pages),
  - **fuzzy access-control rules** (who can see/do what),
  - strong **context management** to keep small/cheap models competitive.

### Key problem being solved
- How to make an agent:
  - **accurate and consistent** (enterprise-grade),
  - **cost-effective** (able to run on open models like **GPT OSS 120B**),
  - resilient to:
    - instruction overload (“too many rules”),
    - long toolchains (compounding error),
    - API quirks (pagination limits, inconsistent responses),
    - permission-sensitive requests.

### Primary solution approach
- Heavy **context engineering** + architectural constraints:
  - **Pre-ingest and route rules** from the company wiki into the system prompt **dynamically**.
  - **Pre-fetch user-related data** via APIs, then use an LLM as a **context selector** (only relevant blocks).
  - Use a **Plan+ReAct-style agent loop** with **structured outputs** (instead of native function calling).
  - Add an **LLM “step validator”** gate to intercept incorrect actions and provide corrective feedback.
  - Aggressively **trim conversation history** and hide failed attempts from the agent.
  - In another benchmark variant (“store”), use a **manager/orchestrator + sub-agents** pattern to isolate context and tools.

---

## 2. ARCHITECTURAL PATTERNS & DECISIONS

### 2.1 Benchmark-as-a-Company Simulation (ERC3 Environment Pattern)
**Description**
- ERC3 simulates an “AP company” with:
  - ~20–24 API tools with different syntax/quirks,
  - entities: employees, projects, clients, time logs, wiki pages,
  - permission rules that depend on the requesting user (employee role, project membership, guest vs authenticated).

**Why chosen / trade-offs**
- Chosen by the benchmark design; the solution must handle enterprise realism:
  - **tool diversity**,
  - **permission gating** without explicit ACL tables (“fuzzy rules” in wiki),
  - **large interlinked data**.

**Implementation approach**
- Always call **HMI (“who am I”)** to learn requester identity/type.
- Use wiki-derived rules + requester context to decide allow/deny and how to respond.

**Benefits**
- Realistic constraints for enterprise agents.

**Limitations**
- Permissions are “soft” (LLM must interpret policy text).
- Tool calls can explode due to pagination and entity volume.

---

### 2.2 Preprocessing + Cache-by-Wiki-Hash (Wiki Ingestion / Rule Extraction)
**Description**
- A one-time (per wiki version) preprocessing step:
  - the system receives a **wiki hash** via HMI,
  - if hash unchanged, reuse locally cached extracted artifacts,
  - extract and cluster “rules” from wiki pages.

**Why chosen / trade-offs**
- Avoid repeatedly re-reading/parsing a static wiki across tasks.
- Trade-off: complexity of ingestion pipeline, but saves tokens and time later.

**Implementation approach**
- On startup / before benchmark run:
  - iterate wiki pages,
  - **extract rules** into buckets:
    - rules for **authenticated users**,
    - rules for **public/guest users**,
    - rules for **response formatting** (kept separate; loaded later on demand).

**Benefits**
- Faster runtime per task.
- Enables dynamic prompt assembly without bloating context.

**Limitations**
- Rule extraction quality matters; errors propagate.
- Requires careful versioning via hash.

---

### 2.3 Dynamic System Prompt Routing (Rule Routing / Noise Reduction)
**Description**
- Do **not** put all rules into the system prompt.
- Route only the relevant cluster based on user type (public vs authenticated).

**Why chosen / trade-offs**
- Core motivation: reduce **noise** and “cognitive load” of the model.
- Trade-off: need a routing mechanism and rule clustering.

**Implementation approach**
- After HMI:
  - if requester is **public** → include “public rules” only,
  - else **authenticated** → include “employee rules” (still scoped vs total ruleset).

**Benefits**
- Better instruction-following, fewer distractions.
- Scales better than a “100 rules always in system prompt” approach.

**Limitations**
- Still coarse-grained; could be further atomized (speaker notes this as a possible improvement).

---

### 2.4 Context Builder + LLM Context Selector (Pre-fetch then Filter)
**Description**
- Before the main agent loop:
  - programmatically fetch a broad set of **user-linked entities** (projects, clients, profile, time logs, etc.),
  - run a **Context Builder/Selector** LLM call to decide which blocks are relevant to the current task.

**Why chosen / trade-offs**
- Solves two problems:
  1. Avoid the agent spending many steps “discovering” basic context.
  2. Avoid dumping everything into the prompt.

- Trade-off: extra LLM call up front, but net fewer steps and less token waste.

**Implementation approach**
- After HMI, in parallel:
  - fetch related data via tool wrappers,
  - pass: {task text + candidate blocks} to context selector LLM,
  - produce “selected block IDs” that become the user/context prompt.

**Benefits**
- Dramatically reduces agent steps (many tasks solved in ~3 steps).
- Improves reliability (less compounding error).

**Limitations**
- Selector can be “greedy” or miss needed blocks; tuning required.

---

### 2.5 Parallel Tool Execution (Latency Hiding)
**Description**
- Many API calls run concurrently.

**Why chosen / trade-offs**
- Benchmark injected ~300ms API latency.
- Sequential pagination + discovery becomes too slow.

**Implementation approach**
- Fetch user-linked entities (projects/clients/logs/profile) in parallel during preparation.

**Benefits**
- Significant wall-clock speedup.
- Enables richer prep context without slowing too much.

**Limitations**
- Concurrency control, rate limits, error handling complexity.

---

### 2.6 Tool Wrappers / Proxies (API Simplification Layer)
**Description**
- Wrap “raw” tools to remove complexity from the LLM, especially **pagination**.

**Why chosen / trade-offs**
- Pagination limit was extremely small (max 5 items) and not documented; you learn only by error.
- Agents calling list endpoints 20 times is fragile and slow.

**Implementation approach**
- Create a code-level **autopaginator** wrapper:
  - iterate pages until complete,
  - return full list to the caller,
  - hide `offset/limit` parameters from the LLM-facing tool schema.

**Benefits**
- Fewer agent steps and fewer failure modes.
- Less prompt/tool schema complexity.

**Limitations**
- Potentially heavy responses (larger payloads).
- Needs caching and limits to avoid huge token injection.

---

### 2.7 Plan + ReAct Hybrid Agent Loop with Structured Outputs (No Native Tool Calling)
**Pattern name**
- **Plan-React (hybrid)** using **Structured Output**.

**Description**
- Agent produces 4 fields per step:
  - `state`: what is known now,
  - `plan`: remaining steps,
  - `action`: next step details,
  - `function`: function name + parameters (executed by code).

**Why chosen / trade-offs**
- Author preference: enterprise requires **consistency** (“nail everything down”).
- Belief: structured output is easier to control than freeform tool calling.
- Trade-off: you bypass native function-calling training benefits, but gain determinism.

**Implementation approach**
- Tools are described in the prompt + schema (via **Pydantic** models).
- The runtime parses the `function` field and executes the corresponding API tool.

**Benefits**
- More predictable step format.
- Easier logging/validation.
- Supports a guided step-by-step “railroad track” for reasoning.

**Limitations**
- Still probabilistic; LLM can skip checks.
- You must maintain schemas and parsing.

---

### 2.8 On-Demand Response Policy Loading (Pseudo-Tool for “Response Instructions”)
**Description**
- Response-formatting rules are large, so they are **not** kept in context.
- The agent is instructed to call a pseudo-tool (e.g., `load_response_instructions`) only when it is ready to answer.

**Why chosen / trade-offs**
- Reduces prompt clutter until the final stage.
- Trade-off: agent may forget to load instructions → needs enforcement (validator).

**Implementation approach**
- Add a pseudo-tool that returns response rules (link formatting, citation IDs, style constraints).
- The agent calls it just before `respond`.

**Benefits**
- Higher signal-to-noise during planning/execution.
- Better compliance with formatting/citation requirements.

**Limitations**
- Another step that can be forgotten without a guard.

---

### 2.9 Step Validator (LLM Gate / Critic / Controller)
**Description**
- A second LLM checks each intended action before execution.
- If it rejects, it supplies corrective feedback; the agent retries.

**Why chosen / trade-offs**
- Addresses “agent inconsistency” and missed constraints.
- Trade-off: extra inference cost and occasional false positives/negatives.

**Implementation approach**
- Validator sees what the agent sees (no extra privileged info).
- It evaluates whether the next tool/action is appropriate.
- If rejected:
  - action is not executed,
  - a feedback message is injected,
  - agent produces a revised action.
- There’s a cap on rejections (e.g., allow only N blocks then let through).

**Benefits**
- Prevents premature terminal responses (e.g., responding without loading response instructions).
- Reduces catastrophic wrong tool calls.

**Limitations**
- Validator can hallucinate too (may block correct actions or allow wrong ones).
- Adds latency.

---

### 2.10 Conversation History Trimming + “Hide Failures” Strategy
**Description**
- The agent does not see full prior verbose state/plan dumps.
- Only keep compact records: **tool called + result**.
- Validator-rejected attempts are removed from history (“history is written by winners”).

**Why chosen / trade-offs**
- Reduce context size and avoid confusion.
- Trade-off: agent loses potentially useful learning signal from its mistakes.

**Implementation approach**
- For each step:
  - store a compact line like: “Called TOOL X(args) → RESULT Y”.
  - omit past `state/plan/action` blocks.
  - omit rejected attempts entirely.

**Benefits**
- Cleaner context; fewer distractions.
- Helps smaller models stay reliable.

**Limitations**
- Less transparency for debugging unless you store full traces separately (they did: JSON traces + visualizer).

---

### 2.11 Orchestrator + Sub-Agents (“Store benchmark” architecture)
**Description**
- A central **orchestrator/manager** has only pseudo-tools that correspond to specialized worker agents.
- Workers have restricted subsets of raw SDK tools and narrow prompts.

**Why chosen / trade-offs**
- Strong compartmentalization:
  - orchestrator doesn’t get polluted with tool details,
  - workers don’t see irrelevant tools,
  - better context economy and specialization.
- Trade-off: more moving parts; coordination complexity.

**Implementation approach**
- Orchestrator delegates tasks in natural language to workers like:
  - “ProductExplorer”: find product SKU,
  - “BasketBuilder”: test coupons/apply best discount/build basket,
  - etc. (one worker was removed and merged into BasketBuilder during iteration).
- Worker returns only a concise “report” to orchestrator.

**Benefits**
- Tool filtering “for free” (workers only know their tools).
- Clear separation of responsibilities.
- Scales to large toolsets.

**Limitations**
- Additional agent calls.
- Requires good delegation prompting and robust worker interfaces.

---

## 3. KEY INSIGHTS & TAKEAWAYS

### Technical insights (numbered)
1. **Context engineering dominates**: ~80% of effort goes into delivering the *right* information to the model with minimal noise.
2. **Don’t dump all rules into the system prompt**; route rules dynamically (public vs employee, etc.) to reduce instruction noise.
3. **Pre-fetch + LLM-select context blocks** reduces tool steps and compounding error.
4. **Parallelize tool calls** aggressively when APIs are slow or numerous.
5. **Wrap painful APIs (pagination)** in code so the model doesn’t manage offsets/limits.
6. **Structured output (state/plan/action/function)** creates a consistent “railroad track” that improves reliability for enterprise-like workflows.
7. **Load heavy response-format instructions only at the end** via a pseudo-tool to avoid polluting the working context.
8. **Step validator (LLM critic) can gate actions** and fix “premature respond” or policy slips without requiring a bigger base model.
9. **Trim history to tool-call summaries**; keep only what the next step truly needs.
10. **Hide failed attempts from the agent** to prevent confusion and context bloat (but keep full traces externally for debugging).
11. **Fewer steps → higher end-to-end success** because per-step error compounds multiplicatively.
12. **RAG + LLM final selection** can replace classic “RAG + reranker” since LLM selection is often cheap and stronger than standalone rerankers.

### Strategic insights
- For enterprise, cost and deployment constraints can make **open models** preferable if you compensate with strong orchestration and context control.
- Benchmark scores are useful but easy to game; real adoption requires **task-specific evaluations**.

### Lessons learned
- Agents are not a silver bullet: even with validators they can still hallucinate or skip verification.
- Adding more and more rules to the system prompt can require a *much larger model* to follow them reliably.

### Best practices mentioned
- Use **XML-style tags** in prompts (clear start/end boundaries); markdown can become messy.
- Treat benchmark claims with skepticism; inspect methodology (read papers, check arXiv).
- Do **your own eval**: start with best models, then move down for cost.

---

## 4. TERMINOLOGY & KEYWORDS

### Technical terms (with definitions)
- **Agent loop**: iterative process where an LLM decides next actions, calls tools, observes results, repeats.
- **ReAct**: “Reason + Act” style agent loop (think/act cycles).
- **Plan agent / Planning step**: explicit step where the model lays out remaining steps before acting.
- **Plan+ReAct hybrid**: combination where a plan is maintained and actions are taken stepwise from it.
- **Structured output**: forcing the model to emit a strict schema (fields like state/plan/action/function).
- **Tool calling / Function calling**: model outputs a tool/function invocation that runtime executes.
- **Pydantic**: Python data validation/schema library used to define and parse structured outputs.
- **Context engineering**: designing what information enters the model context, optimizing relevance and minimizing noise.
- **Context selector / Context builder**: component that chooses which candidate context blocks are relevant to a task.
- **System prompt**: highest-priority instruction block (policies, tool specs, behavior constraints).
- **User prompt**: task-specific input and contextual data for a specific request.
- **Pagination**: API pattern returning partial lists requiring multiple requests (`offset/limit`).
- **Autopaginator wrapper**: code that repeatedly calls paginated endpoints and returns a complete list.
- **Validator / Critic model**: second model that reviews proposed agent actions and blocks/edits them.
- **Orchestrator**: manager agent that delegates to sub-agents instead of calling raw tools itself.
- **Sub-agent**: specialized worker agent with limited tools and narrow responsibilities.
- **Prompt injection**: attempts to manipulate the agent via malicious instructions in the input.

### Domain vocabulary (ERC3 simulation)
- **Company Wikipedia**: internal markdown knowledge base containing policies and company info.
- **Entities**: employees, projects, clients, time logs, etc.
- **Permissions / access rules**: rules about what information/actions are allowed for which requester.

### Acronyms
- **ERC**: Enterprise RAG Challenge (ERC2, ERC3 referenced).
- **RAG**: Retrieval-Augmented Generation.
- **HMI / WhoAmI**: endpoint/tool that identifies the requesting user and returns wiki hash and user attributes.
- **SDK**: Software Development Kit (tool endpoints exposed to agent).
- **OCR**: Optical Character Recognition (mentioned in benchmark skepticism discussion).

---

## 5. IMPLEMENTATION RECOMMENDATIONS

### Step-by-step implementation (as described)
1. **Startup / Preparation**
   - Call or obtain wiki hash (via HMI in benchmark).
   - If wiki hash is new:
     - ingest wiki markdown pages,
     - extract and cluster rules into:
       - authenticated rules,
       - public rules,
       - response-format rules.
2. **Request handling**
   - Call **HMI** to get requester identity, auth status, role metadata, wiki hash.
   - Select rule cluster based on requester type and build the **dynamic system prompt**.
3. **Pre-fetch candidate context (parallel)**
   - In parallel, fetch user-linked entities via APIs:
     - employee profile,
     - projects involved,
     - managed clients,
     - time logs,
     - etc.
   - Use **wrapper tools** to hide pagination and normalize API quirks.
4. **Context selection**
   - Provide task text + candidate blocks to a **context selector LLM**.
   - Include only selected blocks in the user/context prompt.
5. **Agent loop (Plan+ReAct structured output)**
   - Prompt the agent to emit: `state`, `plan`, `action`, `function`.
   - Parse `function` (Pydantic) → execute tool call.
6. **Validation gate (optional but recommended)**
   - Before executing a tool call, ask a **validator LLM** if the call is appropriate.
   - If rejected: inject validator feedback and request a corrected action.
   - Keep retry limits.
7. **On-demand response policy**
   - When agent is ready to answer, it must call `load_response_instructions` pseudo-tool.
   - Then call a terminal `respond` tool with:
     - status/priority,
     - message,
     - references/links (IDs of used entities).
8. **Conversation memory trimming**
   - Record only compact history: “tool call → result”.
   - Omit verbose plans/states from prior steps.
   - Omit validator-rejected attempts from agent-visible history (but log them externally).

### Tools & technologies explicitly mentioned
- **GPT OSS 120B** (open model)
- “SOTA” proprietary models referenced for comparison: **Opus**, **Sonnet**, **Gemini 3 Pro**, **GPT 5.x (thinking)**, etc.
- **Pydantic** (structured schemas)
- **GitHub Pages** (hosting a trace visualizer)
- **Cursor** (used to quickly build a small web app visualizer)
- **JSON traces** (logged for visualization/debugging)

### Configuration / setup notes mentioned
- **Reasoning effort**:
  - mostly **medium** for runtime,
  - **max** used only for one-time wiki rule extraction (since it runs once per wiki version).
- **Latency**:
  - benchmark simulated ~300ms per API call → parallelism and wrappers matter.

### Code patterns/examples discussed (conceptual)
- Structured step schema:
  - `state` → `plan` → `action` → `function(name, params)`
- Pagination wrapper:
  - hide `offset/limit`,
  - iterate until complete.
- Pseudo-tools:
  - `load_response_instructions` (late-binding large formatting constraints)
  - `respond` as terminal action.

---

## 6. EVOLUTION & ITERATIONS

### How the solution evolved
- Started from a **simple baseline agent** provided by the organizer (Renat) to help participants begin.
- Iteratively added:
  - **rule extraction + routing** (avoid “all rules always”),
  - **context builder** pre-fetch + LLM selection,
  - **pagination wrappers** to remove API friction,
  - **step validator** to catch premature/incorrect actions,
  - **history trimming** and suppression of failed attempts,
  - “store benchmark” variant: **orchestrator + sub-agents**.

### Iterations / refactors noted
- In the “store” system:
  - a separate “coupon worker” existed initially,
  - later removed; responsibilities merged into **BasketBuilder**.

### What didn’t work / pain points
- Keeping too many rules in system prompt:
  - required bigger models to follow consistently.
- Agents sometimes fail to verify outcomes (example: update endpoint returns 200, agent may not re-check state).
- Validator is not perfect:
  - can pass wrong actions or block correct ones.

---

## 7. DEVELOPMENT ROADMAP

### Suggested next steps (explicitly mentioned or implied)
- **Tool filtering** (dynamic tool subset selection):
  - author considered it (similar to Claude Code behavior) but didn’t implement due to time.
- Finer-grained **rule routing**:
  - break policies into more atomic pieces and assemble more selectively.
- Add more deterministic **post-action verification**:
  - e.g., after update, always GET resource and confirm state when correctness matters.

### Future improvements mentioned/implied
- Better **measurement instrumentation**:
  - run repeated trials on a subset of hard tasks and record deltas per change (the author did this informally but didn’t persist results).
- Improve validator robustness:
  - reduce false blocks/false passes; tune prompts and retry policy.

### Areas for further research
- Empirical comparison:
  - **native function calling vs prompt-based structured output**, under enterprise constraints and with validators.
- Prompt format experiments:
  - XML tags vs markdown vs other templating styles.
- Benchmark skepticism:
  - validating model claims by reading evaluation papers/methodology.

---

## 8. REFERENCES & RESOURCES

### Tools/libraries/frameworks mentioned
- **Pydantic** (structured output parsing/validation)
- **Cursor** (used to generate a web visualizer)
- **GitHub Pages** (hosting the visualizer)
- **Claude Code** (referenced for tool filtering/sub-agent ideas)
- **Gemini 3 Pro**, **Opus**, **Sonnet**, **GPT OSS 120B** (models referenced)

### External resources referenced
- **GitHub repository** of the solution (explicitly stated to be open-sourced; link not included in transcript)
- **Habr article** about prior winning ERC2 RAG solution (mentioned)
- **arXiv papers** (recommended to verify benchmark methodology)
- **BFCL benchmark** (brought up in discussion as an example of function calling vs prompt mode comparisons)

### Related topics to explore
- Context engineering patterns for agents (routing, late-binding instructions, memory trimming)
- Multi-agent orchestration (manager/worker patterns)
- Tool API hardening (wrappers, normalization, retries)
- Permission-aware LLM systems (policy extraction + enforcement gates)
- Evaluation design for enterprise assistants (task suites, regression testing)

--- 

If you want, I can convert this SEED DOCUMENT into:
1) a PRD + technical design doc bundle, or  
2) a concrete folder/module architecture (Python) matching these components (RuleStore, ContextBuilder, AgentLoop, Validator, ToolWrappers, TraceLogger, Visualizer).
