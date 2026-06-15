from prometheus_client import Counter, Histogram

# Tool call metrics
TOOL_CALL_COUNTER = Counter(
    "tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "success"]
)

TOOL_CALL_LATENCY = Histogram(
    "tool_call_duration_seconds",
    "Tool call latency in seconds",
    ["tool_name"]
)

# LLM call metrics (proxy for cost tracking)
LLM_CALL_COUNTER = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["agent_name"]
)

# Router decision metrics
ROUTE_COUNTER = Counter(
    "router_decisions_total",
    "Router classification decisions",
    ["route"]
)