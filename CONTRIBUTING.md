# Contributing to FlowCheck

Thank you for your interest in contributing to FlowCheck! This project is designed as an **AI-first Git hygiene tool**, so contributions should keep this philosophy in mind.

## Design Philosophy

FlowCheck is built for **agentic coding workflows**—AI assistants that write code autonomously. Key principles:

1. **Non-blocking**: Nudge, never block. Preserve developer autonomy.
2. **AI-readable**: Tools return structured data that AI agents can act on.
3. **Enforceable rules**: The `rules/` directory contains agent instructions.
4. **Privacy-first**: All analysis stays local.

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-org/flowcheck.git
   cd flowcheck
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/flowcheck --cov-report=term-missing
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

## Architecture Overview

```
src/flowcheck/
├── server.py         # FastMCP server with MCP tools
├── core/
│   ├── models.py     # Data models (FlowState, Status)
│   └── git_analyzer.py  # Git repository analysis
├── rules/
│   └── engine.py     # Recommendation logic
└── config/
    └── loader.py     # Configuration management
```

## Adding New Rules

To add a new rule to the Rules Engine:

1. Add threshold to `config/loader.py` default config
2. Implement detection logic in `rules/engine.py`
3. Add recommendation message in `generate_recommendations()`
4. Write tests in `tests/test_rules_engine.py`

## Questions?

Open an issue for any questions or suggestions!
