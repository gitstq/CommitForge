# CommitForge

A lightweight terminal Git commit message intelligent generation and standardization tool.

## Features

- **AI-Powered Generation**: Support for OpenAI, Anthropic, DeepSeek, Ollama (local), and Google Gemini
- **Offline Rules Engine**: Pattern-based commit message generation without any AI dependency
- **Conventional Commits**: Full support for the Conventional Commits v1.0.0 specification
- **History Analysis**: Learn from your repository's commit history to improve suggestions
- **Git Hook Integration**: Automatically generate commit messages before each commit
- **Multi-Language**: Support for English and Chinese output
- **Zero Dependencies**: No external runtime dependencies, uses only Python standard library

## Installation

```bash
pip install -e .
```

## Usage

### Generate commit message

```bash
commitforge                    # Generate from staged changes (rules engine)
commitforge gen                # Same as above
commitforge gen --backend openai  # Use OpenAI backend
commitforge gen --no-ai        # Force rules engine
commitforge gen --lang zh      # Chinese output
commitforge gen --type feat    # Force commit type
commitforge gen --scope api    # Force commit scope
commitforge gen --emoji        # Include emoji
commitforge gen --dry-run      # Preview without committing
commitforge gen -v             # Verbose output
```

### Validate last commit

```bash
commitforge check              # Validate last commit message
commitforge check --lang zh    # Chinese output
```

### History analysis

```bash
commitforge history            # Analyze commit history
commitforge history -n 100     # Analyze last 100 commits
commitforge history --stats-only
```

### Git hook management

```bash
commitforge hook install       # Install prepare-commit-msg hook
commitforge hook uninstall     # Uninstall hook
commitforge hook status        # Show hook status
```

### Configuration

```bash
commitforge init               # Create default config file
commitforge init --install-hook  # Create config and install hook
commitforge config show        # Show current configuration
commitforge config set --key backend --value openai
```

### Examples

```bash
commitforge examples           # Show example commit messages
commitforge examples --emoji   # Show with emoji
```

## Configuration

Create a `.commitforge.toml` file in your project root:

```toml
backend = "rules"
language = "en"
emoji = false

[openai]
api_key = ""
model = "gpt-4o-mini"

[anthropic]
api_key = ""
model = "claude-sonnet-4-20250514"
```

### Environment Variables

- `COMMITFORGE_BACKEND` - Default AI backend
- `COMMITFORGE_LANGUAGE` - Output language (en/zh)
- `COMMITFORGE_OPENAI_API_KEY` - OpenAI API key
- `COMMITFORGE_ANTHROPIC_API_KEY` - Anthropic API key
- `COMMITFORGE_DEEPSEEK_API_KEY` - DeepSeek API key
- `COMMITFORGE_GEMINI_API_KEY` - Google Gemini API key
- `COMMITFORGE_OLLAMA_BASE_URL` - Ollama base URL
- `NO_COLOR` - Disable colored output

## License

MIT License
