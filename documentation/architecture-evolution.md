# Architecture Evolution

## Previous Method
The first system used ML predictions and rule-based operational scoring, while LLMs mainly explained outputs and enriched selected high-priority cases.

## Limitation
Fixed rule weights and a single enrichment pass do not always capture complex clinical interactions, stage-by-stage uncertainty, or structured reasoning traces.

## New Method
The new branch introduces an agentic LLM workflow:

1. Clinical Analyst
2. Risk Scorer
3. Pathway Planner
4. Operational Summarizer

## Final Flow
Raw patient -> ML baseline -> Agentic LLM -> Rule validation -> PostgreSQL cache -> Frontend.
