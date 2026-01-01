# Contributing

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your API keys
5. Run tests (if available)

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions and classes
- Keep functions focused and small
- Write clear, descriptive variable names

## Architecture Principles

- **Layer Separation**: Each layer has a single responsibility
- **Incremental**: All updates must be additive, no retraining from scratch
- **State-based**: All state must persist to disk
- **Deterministic**: Same input produces same output
- **Config-driven**: No magic numbers, all thresholds configurable

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description


