OPPORTUNITY_PROMPT = """
You are an expert in regulatory analysis and startup strategy.

A new regulatory event has been published. Analyze it and return a JSON object.

REGULATORY EVENT:
Title: {title}
Source: {source}
Published: {published_at}
Text: {text}

Return ONLY valid JSON with these exact keys:
{{
  "rule_summary": "1-sentence plain English summary of what the rule does",
  "sectors": ["list", "of", "affected", "sectors"],
  "opportunity_hypothesis": "2-3 sentence startup opportunity hypothesis",
  "who_wins": "description of the first-mover target customer or archetype",
  "urgency": "High | Medium | Low",
  "urgency_reason": "why this urgency level",
  "historical_precedent": "analogous historical startup or market that won after a similar rule change",
  "compliance_product_opportunity": "what compliance tooling or service could be sold to incumbents",
  "urgency_score": <integer 1-5>,
  "market_size_score": <integer 1-5>,
  "defensibility_score": <integer 1-5>,
  "regulatory_certainty_score": <integer 1-5>
}}
"""