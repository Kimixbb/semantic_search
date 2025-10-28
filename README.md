# semantic_search

A terminal-based file viewer with AI-powered semantic search. Like `less`, but with intelligent semantic search powered by DeepSeek's language model.

## Features

- **Semantic Search** - Search by meaning, not just keywords
- **Three Relevance Modes** - Adjust precision vs recall (STRICT/NORMAL/LOOSE)
- **Vim-style Navigation** - Intuitive keyboard shortcuts for power users
- **Match Navigation** - Jump between search results with n/N or h/l
- **Real-time Highlighting** - All matching lines highlighted instantly
- **Error Handling** - Clear error messages for API issues

## Requirements

- Python 3.6+
- DeepSeek API key (free tier available)
- Dependencies: `openai` library

## Installation

1. Clone or download this repository:
```bash
git clone <repository-url>
cd semantic_search
```

2. Install dependencies:
```bash
pip install openai
```

3. Get a DeepSeek API key:
   - Visit https://platform.deepseek.com/api_keys
   - Sign up and create an API key

4. Set your API key as an environment variable:
```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

To make it permanent, add the above line to your `~/.bashrc` or `~/.zshrc`.

## Usage

```bash
python3 semantic_search.py <filename>
```

**Example:**
```bash
python3 semantic_search.py /var/log/syslog
python3 semantic_search.py ~/documents/research.txt
```

## Key Bindings

### Search & Navigation
- `/` - Start semantic search (enter your query)
- `n` / `l` / `→` - Jump to next match
- `N` / `h` / `←` - Jump to previous match
- `c` - Clear search and highlighting

### Search Options
- `r` - Cycle relevance level (STRICT → NORMAL → LOOSE)
- `Enter` - Re-run search with current relevance level

### File Navigation
- `j` / `↓` - Scroll down one line
- `k` / `↑` - Scroll up one line
- `Page Down` - Scroll down one page
- `Page Up` - Scroll up one page
- `Home` - Jump to start of file
- `End` - Jump to end of file

### Exit
- `q` / `ESC` - Clear active search (if any), or quit the program (press twice to quit with search active)

## Relevance Levels

Control search precision with three modes:

| Mode | Precision | Recall | Best For |
|------|-----------|--------|----------|
| **STRICT** | High | Low | Finding exact, specific concepts |
| **NORMAL** | Balanced | Balanced | General exploration (default) |
| **LOOSE** | Lower | High | Broad search, catching edge cases |

**How to use:**
1. Start a search with `/`
2. Press `r` to cycle through relevance levels
3. Press `Enter` to re-run the search with the new level
4. View match count in status bar: "15 matches (Match 3/15)"

## Example Workflow

<p align="center">
  <img src="example-workflow.gif" alt="Semantic search workflow demonstration" width="800"/>
</p>

The demo above shows semantic search in action:

1. **Open the log file:**
   ```bash
   python3 semantic_search.py server.log
   ```

2. **Navigate the file:**
   - Use `j`/`k` or arrow keys to scroll through the file
   - Use `Page Down`/`Page Up` for faster navigation
   - Use `HOME` / `END` to go to file beginning / end

3. **Search semantically:**
   - Press `/` to start a search
   - Type: `service` (searching for service-related entries)
   - Press Enter

4. **View results in NORMAL mode:**
   - **13 matches** found with balanced precision
   - Use `n`/`l` to jump to next match
   - Use `N`/`h` to jump to previous match
   - Status bar shows: "Match 1/13", "Match 2/13", etc.

5. **Adjust to LOOSE mode for broader results:**
   - Press `r` to cycle relevance level to LOOSE
   - Press `Enter` to re-run search
   - **61 matches** found (more inclusive)

6. **Adjust to STRICT mode for precision:**
   - Press `r` again to cycle to STRICT
   - Press `Enter` to re-run search

7. **Exit:**
   - Press `q` once to clear search
   - Press `q` again to quit the program

## Tips

- **Natural language queries work best** - Instead of "error", try "authentication failures" or "connection problems"
- **Start with NORMAL mode** - Only adjust relevance if you're getting too many/few results
- **Use STRICT for debugging** - When you need exact matches for specific function names or error codes
- **Use LOOSE for exploration** - When learning a new codebase or investigating broadly

## Error Messages

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `401 - Authentication Failed` | Invalid API key | Check your DEEPSEEK_API_KEY |
| `402 - Insufficient Balance` | No credits remaining | Add credits at platform.deepseek.com |
| `429 - Rate Limit` | Too many requests | Wait a moment, then try again |
| `Connection Error` | Network issue | Check internet connection |

## How It Works

semantic_search sends your file (with line numbers) to DeepSeek's language model, which analyzes the content semantically and returns line numbers that match your query. Unlike traditional grep/search, it understands meaning and context, not just exact string matches.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
