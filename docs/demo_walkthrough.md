# Demo Walkthrough

This concise demonstration can be completed in about ten minutes.

## Start the service

Run `make install`, `make test`, then `make run`.

Show `/docs` to demonstrate the product APIs and engineering control plane in one runnable application.

## Demonstrate the URL product

Create a short URL with an alias and expiration. Resolve it once. Open analytics and point out that referrer host is retained while raw IP address is not stored. Disable the URL and show that future resolution returns HTTP 410.

## Demonstrate greenfield orchestration

Start a greenfield engineering run. Show the audit list and node state. Point out that architecture and risk analysis both completed, then four validation nodes completed before release readiness. Show that the run is waiting at `release_approval`.

Approve release and show the final summary plus decision lineage.

## Demonstrate ambiguity governance

Start the ambiguous scenario. The workflow stops at `clarification_gate`. Explain that the system refuses to invent measurable requirements. Approve the clarification with concrete retention and reliability targets, then show execution resume.

## Demonstrate brownfield reasoning

Run the brownfield scenario. Open its `codebase_reasoning` artifact. It contains actual repository paths, symbol names, and a mapped data flow. Explain that architecture waits for that evidence before proposing change scope.

## Demonstrate resilience and replan

Run a workflow with `simulate_transient_failure` metadata. Show the retry event and recovered implementation. Then call the replan endpoint with a changed requirement. Show the plan version increment and downstream approval invalidation.

## Close with tradeoffs

Explain that SQLite, JSON workflow state, and local rate limiting are prototype choices. The architecture document identifies production replacements. Emphasize that the system optimizes for controlled autonomy, traceability, and safe change management rather than unrestricted agent execution.
