# Contributing

Keep product code and orchestration code modular. New workflow stages must declare dependencies in the graph, define an output contract, add failure behavior, and include tests.

Run these checks before opening a pull request:

```bash
ruff check src tests scripts
pytest --cov=urlshortener --cov-report=term-missing
```

Any change that alters release behavior, security policy, data retention, or user facing API compatibility should be treated as high impact and reviewed explicitly.
