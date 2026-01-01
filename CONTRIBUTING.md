# Contributing

## Development Setup

```bash
git clone <repository-url>
cd Incremental_MODEL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Code Standards

- **Type hints**: Required for all function parameters and return types
- **Docstrings**: Required for all public functions and classes
- **Style**: Follow PEP 8
- **Imports**: Use absolute imports, group by standard library → third-party → local
- **Error handling**: Explicit exception handling, no silent failures

## Architecture Principles

1. **Layer separation**: Each module has a single responsibility
2. **Incremental updates**: All changes must be additive, no retraining from scratch
3. **State persistence**: All state must be explicitly saved to disk
4. **Deterministic**: Same input must produce same output
5. **Config-driven**: No magic numbers, all thresholds in configuration

## Pull Request Process

1. Create a feature branch from `main`
2. Make changes following code standards
3. Ensure all functionality works incrementally
4. Update documentation if needed
5. Submit PR with clear description of changes

## Testing

- Verify incremental behavior: new data doesn't require full retraining
- Test state persistence: system survives restarts
- Validate deterministic output: same input produces same results
