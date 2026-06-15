## Known Limitations / Future Enhancements

### Loop Detection (guardrails/loop_guard.py)
Scoped but not implemented. The current single-pass graph (supervisor → router →
one of rag/action/escalation → END) produces at most one ToolResult per request,
so loop detection has no meaningful signal to act on. This becomes relevant once
iterative/multi-step flows are added (see "Iterative Refinement Loops" below) —
at that point, state.tool_results would contain multiple entries per request,
and this guardrail would check for repeated identical (tool_name, error) pairs.

### Iterative Refinement Loops
Current graph handles one classification + one action per user turn. Compound
requests ("check my license AND reset my password") are not decomposed into
multiple steps. A planner/executor pattern would be needed to support this.

### Output Validator Grounding Check (guardrails/output_validator.py)
Designed: validates that LLM-extracted target_username (for actions targeting
another user) actually appears in the original message, to catch hallucinated
targets. Requires action_agent.py to expose the decide step separately from
execute, so action_node can run the check before tool invocation. Not yet wired.

### Human-in-the-Loop Approval
Not implemented. Would require checkpointing (graph.compile(checkpointer=...)),
an approval API endpoint, and Command(resume=...) logic to pause/resume
execution around sensitive actions. Current safe_execute permission gating
(ROLE_PERMISSIONS) covers static authorization but not per-action human approval.

### Caller-vs-Target Permission Scoping
safe_execute checks "can this caller perform this action type" but does not
distinguish "caller acting on themselves" vs "caller acting on someone else"
(e.g., employee checking their own license vs a colleague's). Currently both
are allowed if the caller has the permission at all.

### Tracing (observability/tracing.py)
OpenTelemetry tracer and `@traced` decorator are implemented and ready to apply
to agent/tool functions. No exporter is configured — spans are created via a
no-op tracer and produce no visible output. Wiring an OTLP exporter (e.g., to
Jaeger or an OTel-compatible Prometheus setup) in deploy/ would make these
spans visible without any changes to the instrumented functions themselves.

### Async Escalation via Celery (queue/tasks.py)
Ticket creation (SQLite write) is already sub-millisecond and doesn't need
async offloading at current scale. Celery is used here primarily to
demonstrate the workflow-queue pattern for the JD's requirements. A genuine
use case would emerge if ticket creation triggered slower downstream actions
(e.g., emailing the user, notifying a Slack channel, syncing to a real ITSM
like Jira/ServiceNow) — at that point, offloading to Celery would actually
improve /chat response latency.

### Caching (memory/cache.py, memory/conversation_memory.py)
Designed but not yet implemented. cache.py would cache search_kb results in
Redis (TTL-based) to reduce repeated KB lookups for common queries.
conversation_memory.py would persist AgentState.messages per session_id in
Redis, enabling multi-turn conversations (currently each /chat request is
stateless — no prior message history is retained).