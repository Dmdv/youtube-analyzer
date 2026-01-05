
============================================================
Analysis (SEED)
============================================================

# COMPREHENSIVE SEED DOCUMENT: ERC3 AGENT SYSTEM

## 1. EXECUTIVE SUMMARY

### Main Topic and Purpose
This video discusses Ilya Rees's winning solution for the Enterprise RAG Challenge 3 (ERC3) competition, focusing on building high-performance AI agent systems using open-source models (specifically GPT-OSS 120B) that rival proprietary models like Claude Opus and GPT-4.

### Key Problem Being Solved
- Building enterprise-grade AI agents that can handle complex multi-step tasks with access controls and permissions
- Achieving competitive performance using smaller, open-source models versus expensive proprietary alternatives
- Managing context effectively to prevent cognitive overload and hallucinations in LLMs
- Handling API pagination, permissions systems, and policy enforcement in agent workflows

### Primary Solution Approach
A multi-layered agent architecture featuring:
- **Pre-execution context preparation** (dynamic rule routing, context filtering)
- **Plan-React hybrid agent pattern** with structured output
- **Step validator** to catch errors before execution
- **Aggressive context trimming** to maintain focus and reduce token usage
- **Multi-agent orchestration** for complex workflows

---

## 2. ARCHITECTURAL PATTERNS & DECISIONS

### Pattern 1: Dynamic Context Building (Pre-Agent Preparation)

**Description:**
Before the main agent executes, a preparation pipeline:
1. Extracts user information via `who_am_i` API call
2. Fetches all related entities (projects, clients, time logs, employee profiles) in parallel
3. Uses a "Context Builder" LLM to filter only task-relevant information

**Why Chosen:**
- Open-source models have limited cognitive capacity
- Including all available context creates noise that degrades performance
- Pre-filtering reduces context size by 60-80% while maintaining relevance

**How It Works:**
```
1. who_am_i() → user_id, role, permissions
2. Parallel API calls:
   - get_projects(user_id)
   - get_clients(user_id)
   - get_time_logs(user_id)
   - get_employee_profile(user_id)
3. Context Builder LLM:
   Input: task_text + all_user_data
   Output: selected_relevant_blocks (by ID)
4. Selected blocks → user_prompt
```

**Benefits:**
- Dramatically reduced context window usage
- Higher precision in retrieval (LLM does final selection vs embeddings)
- Faster inference due to smaller prompts

**Limitations:**
- Adds one extra LLM call before main agent starts
- Context Builder can occasionally miss relevant information if too aggressive

---

### Pattern 2: Dynamic Rule Routing

**Description:**
Instead of loading all policy rules into system prompt, rules are:
1. Pre-extracted from Wiki during preparation phase (done once per Wiki hash)
2. Clustered by user type (authenticated users, public users, response formatting)
3. Dynamically routed based on `who_am_i` result

**Why Chosen:**
- System prompt with all rules becomes too large for smaller models
- Irrelevant rules create noise and confusion
- Signal-to-noise ratio is critical for performance

**How It Works:**
```python
# Preprocessing (done once)
wiki_hash = get_wiki_hash()
rules = {
    'authenticated': extract_authenticated_rules(wiki),
    'public': extract_public_rules(wiki),
    'response': extract_response_rules(wiki)
}

# Per-request routing
user_type = who_am_i().type
relevant_rules = rules[user_type]
system_prompt = base_prompt + relevant_rules
```

**Benefits:**
- Scalable to larger rule sets
- Consistent rule application
- Reduced cognitive load on model

**Limitations:**
- Requires upfront rule categorization
- May miss edge cases where rules overlap categories

---

### Pattern 3: Plan-React Hybrid Agent with Structured Output

**Description:**
Agent uses 4-field structured output instead of native function calling:
1. **State:** Current situation summary
2. **Plan:** Remaining steps to complete task
3. **Action:** Next immediate step to take
4. **Function:** Tool call with parameters (Pydantic validated)

**Why Chosen:**
- More deterministic than native function calling
- Allows explicit reasoning chain
- Better control over agent behavior
- Enforces step-by-step thinking

**How It Works:**
- Agent doesn't use native tool calling API
- Tools defined in system prompt as descriptions
- Structured output schema enforces 4-field response
- Each field builds on previous (state → plan → action → function)

**Benefits:**
- Higher consistency across runs
- Easier to debug (can inspect reasoning)
- Works better with smaller models
- Reduced hallucination on tool calls

**Limitations:**
- Doesn't leverage native function calling optimizations
- Slightly more verbose prompting required

---

### Pattern 4: Step Validator (Error Prevention Layer)

**Description:**
Before executing any tool call, a separate LLM validates the agent's decision:
- Reviews: task, system prompt, context, history, proposed action
- Returns: `approved` or `rejected` with feedback
- On rejection: feedback returned to agent for retry (max 2 rejections)

**Why Chosen:**
- Cumulative error problem: P(success) = 0.9^n (for n steps)
- Prevents policy violations before execution
- Catches premature responses (e.g., responding before loading response rules)

**How It Works:**
```
Agent proposes: function_call(params)
  ↓
Validator checks:
  - Is this allowed per policies?
  - Are all prerequisites met?
  - Is context sufficient?
  ↓
If approved: execute tool
If rejected: return feedback → agent retries
```

**Benefits:**
- Reduces error propagation
- Catches ~30-40% of potential mistakes
- Doesn't slow down correct decisions
- Improves overall task completion rate

**Limitations:**
- Adds latency (1 extra LLM call per step)
- Validator itself can hallucinate (false positives/negatives)
- Only works well with fast inference (Cerebras)

---

### Pattern 5: Aggressive History Trimming

**Description:**
Unlike typical chat history that preserves all messages, this system:
- Only preserves: `tool_name` + `tool_result` from previous steps
- Discards: reasoning, plans, rejected attempts
- Failed validation attempts never enter history
- Sliding window for certain fields (only last step visible)

**Why Chosen:**
- Prevents context pollution from outdated information
- Reduces cumulative context growth
- Failed attempts are noise, not learning opportunities
- "History is written by the victors" - only show successes

**How It Works:**
```python
# Standard approach (bloated)
history = [
  {state, plan, action, function, result},
  {state, plan, action, function, result},
  ...
]

# Trimmed approach
history = [
  {function: "get_project", result: {...}},
  {function: "update_status", result: "success"},
]
```

**Benefits:**
- Dramatically smaller context windows
- Better caching efficiency (less churn)
- Prevents "lost in the middle" attention problems
- Faster inference

**Limitations:**
- Agent can't learn from past mistakes within conversation
- May lose helpful context in complex multi-turn scenarios

---

### Pattern 6: Pagination Auto-Wrapper

**Description:**
API endpoints return max 5 items per page. Instead of exposing pagination to agent:
- Created wrapper functions that auto-paginate
- Agent only sees simplified "get_all_X()" interface
- Wrapper handles offset/limit logic programmatically

**Why Chosen:**
- Pagination logic is error-prone for LLMs
- Reduces step count dramatically
- Simplifies tool descriptions in prompt

**How It Works:**
```python
def get_all_projects(filters):
    results = []
    offset = 0
    while True:
        page = sdk.get_projects(filters, offset=offset, limit=5)
        results.extend(page)
        if len(page) < 5:
            break
        offset += 5
    return results
```

**Benefits:**
- Eliminates entire class of errors
- Reduces average steps from 20+ to 3-5
- Agent focuses on task logic, not API mechanics

**Limitations:**
- May retrieve more data than needed
- Adds latency if many pages (mitigated by parallel calls)

---

### Pattern 7: Multi-Agent Orchestration (Store Benchmark)

**Description:**
Hierarchical agent system:
- **Orchestrator:** Manager with no raw SDK tools, only pseudo-tools (sub-agents)
- **Workers:** Specialized agents with subset of SDK tools
- Workers report results upward without exposing internal reasoning

**Why Chosen:**
- Separates planning from execution
- Each worker has minimal context (only their tools/responsibilities)
- Orchestrator doesn't need to know implementation details
- Similar to corporate hierarchy

**How It Works:**
```
User request
  ↓
Orchestrator (manager)
  ├─→ Product Explorer (finds items)
  │    └─→ Returns: "Product XYZ found"
  ├─→ Basket Builder (applies coupons)
  │    └─→ Returns: "Best coupon: 20% off"
  └─→ Checkout Agent (completes purchase)
       └─→ Returns: "Order #123 placed"
```

**Benefits:**
- Extremely clean context separation
- Workers can be optimized independently
- Easier to debug (isolated failures)
- Scalable to complex workflows

**Limitations:**
- More complex to set up initially
- Requires careful interface design between agents
- Can be overkill for simple tasks

---

## 3. KEY INSIGHTS & TAKEAWAYS

### Technical Insights

1. **Context is king, not model size:** 80% of effort went into context management, not prompt engineering
2. **Smaller models + better architecture > larger models + naive approach:** GPT-OSS 120B matched Claude Opus performance
3. **Pre-filtering beats post-filtering:** Better to prevent bad data entering context than trying to ignore it
4. **Parallel API calls are essential:** 300ms simulated delay per call × 20 calls = 6 seconds vs 300ms with parallelization
5. **Validation adds robustness:** Step validator caught 30-40% of potential errors
6. **Function calling vs prompting:** No clear winner; structured output with explicit schemas worked well for this use case
7. **History trimming is underrated:** Only preserving successful steps reduced context by ~70%
8. **LLM as re-ranker beats embeddings alone:** Filtering 1000 items to 100 programmatically, then LLM selecting final items outperformed pure RAG
9. **Fewer steps = higher success rate:** P(success)^n means every additional step compounds error probability
10. **XML tags > Markdown:** Better delimiter clarity for structured data

### Strategic Insights

1. **Enterprise = cost optimization:** Open-source models are 10-100x cheaper than proprietary, critical for scale
2. **Benchmarks require skepticism:** Always verify methodology; providers manipulate metrics
3. **Agent ≠ silver bullet:** Over-reliance on agent autonomy reduces consistency; hybrid approaches (pipeline + agent) work better
4. **Specialization beats generalization:** Multi-agent systems with focused responsibilities outperform single general-purpose agents
5. **Offline preparation is free:** One-time preprocessing (rule extraction, Wiki indexing) amortizes across all requests
6. **Validation is meta-cognition:** Asking model to "double-check its own work" catches errors without additional knowledge

### Lessons Learned

1. **Start simple, add complexity only when needed:** Began with basic React agent, added validator only after identifying error patterns
2. **Measure everything:** Used custom visualizer to inspect every step; crucial for debugging
3. **Failed attempts are noise:** Don't include validation failures in history
4. **Cerebras speed enables new patterns:** Fast inference (1 sec per call) makes validator pattern practical
5. **Cognitive capacity is limited:** Even large models forget; better to trim context than rely on attention
6. **Domain rules > general intelligence:** Hardcode what you can (pagination, parallel calls), use LLM for judgment

### Best Practices Mentioned

1. **Use XML tags for structured prompts** (clearer boundaries than Markdown)
2. **Parallel API calls by default** (especially with simulated latency)
3. **Separate rules by user type** (authenticated vs public)
4. **Create pseudo-tools for complex operations** (response instructions, context building)
5. **Medium reasoning effort is sufficient** (high only for critical one-time operations)
6. **Wrapper simplifications for LLMs** (auto-pagination, simplified interfaces)
7. **Sliding window for certain context fields** (only show latest plan, not all historical plans)
8. **Build custom evaluation harness** (run same task 10x to measure consistency)
9. **Open-source solutions for learning** (easier to inspect, modify, understand)
10. **Visualize agent traces** (essential for debugging multi-step systems)

---

## 4. TERMINOLOGY & KEYWORDS

### Technical Terms

- **Plan-React Agent:** Hybrid agent pattern combining explicit planning with reactive execution
- **SGR (Structured Guided Reasoning):** Forcing LLM to reason through predefined steps (state → plan → action → function)
- **Context Builder:** Pre-agent LLM that filters raw data to relevant blocks
- **Step Validator:** Separate LLM that reviews agent decisions before execution
- **History Trimming:** Aggressively reducing conversation history to only essential information
- **Dynamic Rule Routing:** Loading only relevant policy rules based on user context
- **Pseudo-Tools:** Functions that wrap complex logic (pagination, sub-agents) as simple tool interfaces
- **Orchestrator Pattern:** Manager agent that delegates to specialized worker agents
- **Cumulative Error:** Multiplicative probability of failure across multi-step processes (P(success) = p^n)

### Domain-Specific Vocabulary

- **ERC (Enterprise RAG Challenge):** Competition series by Renat Abdullin testing agent systems on enterprise scenarios
- **Cerebras Inference:** High-speed LLM inference service enabling <1 second response times
- **Wiki (Company Wikipedia):** Knowledge base containing policies, employee data, project info
- **who_am_i:** API endpoint returning current user's identity and permissions
- **Pagination:** Returning large datasets in chunks (offset/limit pattern)
- **SDk Tools:** Raw API functions provided by the benchmark environment
- **Context Window:** Total amount of text (tokens) an LLM can process at once
- **Signal-to-Noise Ratio:** Proportion of relevant vs irrelevant information in context
- **Function Calling:** Native LLM capability to output structured tool calls
- **Structured Output:** Enforcing LLM responses to match predefined schemas (Pydantic)

### Acronyms

- **ERC:** Enterprise RAG Challenge
- **RAG:** Retrieval-Augmented Generation
- **LLM:** Large Language Model
- **SDK:** Software Development Kit (API library)
- **API:** Application Programming Interface
- **GPT-OSS:** GPT Open Source (specifically 120B parameter model)
- **SGR:** Structured Guided Reasoning
- **XML:** eXtensible Markup Language
- **UX:** User Experience
- **ID:** Identifier

---

## 5. IMPLEMENTATION RECOMMENDATIONS

### Step-by-Step Approach

**Phase 1: Preparation Pipeline**
1. Implement `who_am_i` call to identify user
2. Build parallel API fetching for related entities
3. Create Context Builder LLM with filtering prompt
4. Extract and cluster policy rules from knowledge base
5. Implement dynamic rule routing based on user type

**Phase 2: Core Agent**
1. Define 4-field structured output schema (state, plan, action, function)
2. Create system prompt with base instructions + dynamic rules
3. Build tool wrappers for pagination auto-handling
4. Implement main agent loop with structured output parsing
5. Add conversation history with aggressive trimming

**Phase 3: Validation Layer**
1. Create Step Validator with separate system prompt
2. Pass agent's proposed action + full context to validator
3. Implement retry logic (max 2 rejections)
4. Filter failed attempts from conversation history

**Phase 4: Orchestration (Advanced)**
1. Design worker agent responsibilities
2. Create pseudo-tools for each worker
3. Build orchestrator agent with only pseudo-tools
4. Implement result reporting (workers → orchestrator)
5. Add validator to orchestrator level

### Tools and Technologies Recommended

**Core Stack:**
- **LLM:** GPT-OSS 120B via Cerebras Inference (or similar fast provider)
- **Validation:** Pydantic for structured output schemas
- **Parallelization:** Python `asyncio` or `concurrent.futures`
- **Visualization:** Custom web app (built with Cursor, hosted on GitHub Pages)

**Development Tools:**
- **Tracing:** Custom JSON trace logger for every step
- **Debugging:** Web visualizer to inspect agent reasoning
- **Testing:** Batch runner to execute same task 10x for consistency metrics
- **Version Control:** Git with detailed README documentation

### Configuration Notes

**Model Settings:**
- **Reasoning Effort:** Medium for most operations, High only for one-time critical tasks (rule extraction)
- **Temperature:** Not specified, but likely low (0.2-0.4) for consistency
- **Max Tokens:** Varies by step; context builder uses smaller limit

**Prompt Structure:**
```xml
<task>User request text</task>
<context>
  <employee id="123">...</employee>
  <project id="456">...</project>
</context>
<rules>
  - Rule 1
  - Rule 2
</rules>
```

**API Wrapper Example:**
```python
def get_all_projects_wrapper(filters):
    """Auto-paginating wrapper hiding complexity from LLM"""
    return auto_paginate(
        sdk.get_projects, 
        filters=filters, 
        page_size=5
    )
```

### Code Patterns Discussed

**Context Trimming Pattern:**
```python
def trim_history(history):
    """Keep only essential information"""
    return [
        {
            'tool': step['function']['name'],
            'result': step['result']
        }
        for step in history
        if step['validated'] == True  # Skip rejected attempts
    ]
```

**Dynamic Rule Loading:**
```python
def get_relevant_rules(user_type, wiki_hash):
    """Load only applicable rules"""
    rules_cache = load_rules_cache(wiki_hash)
    return rules_cache[user_type]  # 'authenticated' or 'public'
```

**Parallel Entity Fetching:**
```python
async def fetch_user_context(user_id):
    """Fetch all related data in parallel"""
    tasks = [
        get_projects(user_id),
        get_clients(user_id),
        get_time_logs(user_id),
        get_employee_profile(user_id)
    ]
    return await asyncio.gather(*tasks)
```

---

## 6. EVOLUTION & ITERATIONS

### Initial Approach
- Started with basic React agent provided by competition organizer
- Used all available tools without wrappers
- Loaded all rules into system prompt
- Included full conversation history

**Problems:**
- Too many steps (20+ for simple tasks)
- Frequent pagination errors
- Rule overload causing confusion
- Context window exhaustion
- Low success rate due to cumulative errors

### Iteration 1: Simplification
- Added auto-pagination wrappers
- Reduced step count from 20+ to 8-12
- Improved success rate moderately

### Iteration 2: Context Optimization
- Implemented Context Builder for pre-filtering
- Added dynamic rule routing
- Trimmed conversation history to essentials
- Step count reduced to 3-5 for most tasks
- Significant performance improvement

### Iteration 3: Validation Layer
- Added Step Validator to catch errors
- Implemented retry logic with feedback
- Removed failed attempts from history
- Further improved success rate

### Iteration 4: Structured Output
- Switched from function calling to Plan-React with 4 fields
- Added explicit reasoning chains
- Improved consistency and debuggability

### Iteration 5: Multi-Agent (Store Benchmark)
- Created orchestrator pattern for complex workflows
- Specialized workers with focused responsibilities
- Cleaner context separation
- Validator moved to orchestrator level

### What Didn't Work

1. **Native function calling:** Less consistent than structured output approach with smaller models
2. **Including all rules:** Cognitive overload; dynamic routing essential
3. **Preserving failed attempts in history:** Added noise without value
4. **Single general-purpose agent for complex tasks:** Specialized agents performed better
5. **High reasoning effort everywhere:** Medium was sufficient for most steps; high only needed for critical operations
6. **Full conversation history:** Aggressive trimming worked better

### Key Pivots

- **Mindset shift:** From "make agent smarter" to "make context cleaner"
- **Architecture shift:** From monolithic agent to orchestrator + workers
- **Error handling shift:** From retry-after-failure to validate-before-execution
- **History management shift:** From preserving everything to preserving only successes

---

## 7. DEVELOPMENT ROADMAP

### Suggested Next Steps

1. **Further context optimization:**
   - Implement tool filtering (like Claude Code's approach)
   - Experiment with dynamic tool selection based on task
   - Add semantic caching for repeated queries

2. **Enhanced validation:**
   - Multi-tier validation (quick checks vs deep analysis)
   - Confidence scores for validator decisions
   - Validator ensembles (multiple validators voting)

3. **Improved orchestration:**
   - Better worker specialization strategies
   - Dynamic worker assignment based on task analysis
   - Worker performance monitoring and adaptation

4. **Evaluation infrastructure:**
   - Automated A/B testing framework
   - Continuous benchmark runs
   - Performance regression detection

### Future Improvements Mentioned

1. **Tool filtering:** Dynamically select which tools to show agent based on task
2. **Better visualization:** More user-friendly trace debugging interface
3. **Automated prompt evolution:** Learn from benchmark errors to update system prompts
4. **Caching strategies:** Even without native caching, implement application-level caching
5. **Hybrid approaches:** Combine programmatic logic with agent flexibility more strategically

### Areas for Further Research

1. **Optimal context size:** Finding sweet spot between information and noise
2. **Validation efficiency:** When to validate vs when to trust agent
3. **Multi-agent communication:** Better protocols for agent-to-agent information passing
4. **Error recovery:** Beyond retry, how to gracefully degrade or ask for help
5. **Benchmark transferability:** Do optimizations for ERC3 apply to other domains?
6. **Model comparison:** Systematic testing of function calling vs structured output across models
7. **Reasoning effort calibration:** Per-step optimization of reasoning depth

---

## 8. REFERENCES & RESOURCES

### Tools, Libraries, and Frameworks

**LLM Providers:**
- Cerebras Inference (GPT-OSS 120B) - Primary model used
- OpenAI (GPT-4, GPT-4 Turbo Mini) - Comparison testing
- Anthropic (Claude Opus 4.2, Sonnet) - Benchmark comparisons
- Google (Gemini 3 Pro) - Benchmark comparisons

**Development Tools:**
- Cursor - Used to build web visualizer
- Pydantic - Structured output validation
- GitHub Pages - Hosting for trace visualizer

**Benchmarks:**
- ERC (Enterprise RAG Challenge) - Competition series by Renat Abdullin
- BFCL (Berkeley Function Calling Leaderboard) - Function calling evaluation

### External Resources Referenced

**Ilya's Resources:**
- GitHub Repository: Open-sourced winning solution (link in video description)
- Trace Visualizer: Live demo viewer hosted on GitHub Pages
- Previous Article: ERC2 winning solution (Habr.com, Russian & English versions)
- Blog: Technical write-ups of both competitions

**Competition Resources:**
- ERC3 Benchmark Platform: Simulated company API environment
- Company Wiki: Knowledge base with policies and employee data
- SDK Documentation: ~20-24 API tools with different contracts

**Academic/Industry References:**
- Plan-React agent pattern (existing research)
- Structured Guided Reasoning papers
- Anthropic's XML tag recommendations (blog posts)
- OpenAI prompt engineering guides (XML tags mentioned)

### Related Topics to Explore

1. **Agent Architectures:**
   - ReAct (Reasoning + Acting)
   - Plan-and-Execute patterns
   - Reflection and self-correction mechanisms
   - Multi-agent systems and orchestration

2. **Context Management:**
   - Attention mechanisms and "lost in the middle" problem
   - Prompt compression techniques
   - Dynamic context windows
   - Semantic caching strategies

3. **RAG Optimization:**
   - Hybrid retrieval (keyword + semantic)
   - LLM-based re-ranking
   - Context filtering and relevance scoring
   - Embedding model selection

4. **Validation and Quality:**
   - Self-consistency checking
   - Constitutional AI approaches
   - Chain-of-verification
   - Ensemble methods for robustness

5. **Open-Source Models:**
   - Fine-tuning strategies for specialized tasks
   - Inference optimization (quantization, pruning)
   - Smaller models for specific sub-tasks
   - Cost-performance trade-offs

6. **Enterprise AI:**
   - Permission systems and access control
   - Audit trails and explainability
   - Reliability and consistency requirements
   - Cost optimization at scale

7. **Benchmarking:**
   - Creating domain-specific evaluations
   - Avoiding benchmark overfitting
   - Metric selection and interpretation
   - Reproducibility and fairness

### Community and Learning

- **Telegram Channel:** Under Pod Kapotom (Russian AI community)
- **GitHub:** Follow Ilya's repositories for future solutions
- **Competitions:** ERC series continues with new challenges
- **Practice:** Ilya recommends building custom evaluations for your specific use case

---

## FINAL NOTES

**Key Philosophy:**
> "80% of the effort went into context management, not model selection. The best architecture is the one that gives your LLM exactly the information it needs—nothing more, nothing less."

**On Benchmarks:**
> "Always take them with a huge grain of salt. Build your own evaluation on your own data. Benchmarks tell you what's possible, not what works for you."

**On Agents:**
> "I'm not a huge fan of agents in production. Business solutions require consistency. Lock down everything you can with code; use LLMs only for judgment calls."

**On Open Source:**
> "Cerebras + GPT-OSS showed that with proper architecture, you can match Claude Opus at 1/10th the cost and 10x the speed. The model isn't magic—the system design is."

This document captures a masterclass in practical agent engineering, emphasizing that thoughtful architecture and context management can make smaller, cheaper models competitive with the largest proprietary offerings.
