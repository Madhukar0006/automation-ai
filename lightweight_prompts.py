# Lightweight Prompts for Token Optimization

LIGHTWEIGHT_PROMPTS = {
    "vrl_generation": """Generate VRL parser:

LOG: {log_content[:200]}...
FORMAT: {log_format}

Requirements:
- Use: if exists(parsed.field) {{ .target = del(parsed.field) }}
- Error handling: parsed, err = parse_grok(raw, pattern)
- Single-line GROK
- Add compact()

Generate VRL code:""",
    "log_classification": """Classify log:

{log_content[:150]}...

Return: {{"log_format": "format", "vendor": "vendor", "product": "product"}}""",
    "ecs_generation": """Convert to ECS JSON:

LOG: {log_content[:150]}...

Required: @timestamp, event.original, event.category, message
Return JSON:""",
}
