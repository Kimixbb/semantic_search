#!/usr/bin/env python3
import os
import json
import curses
from openai import OpenAI
import openai

# ----------------------------
# Configuration
# ----------------------------
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Please set the DEEPSEEK_API_KEY environment variable.")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


# ----------------------------
# Prompt template constants
# ----------------------------
PROMPT_BASE = (
    "You are a helpful assistant that finds semantically relevant lines in documents. "
    "The user will provide a document where each line is prefixed with '[LINE N]: ' where N is the zero-indexed line number. "
)

PROMPT_FORMAT = (
    "Format: [0, 5, 12, 23] "
    "Return an empty array [] if nothing matches. "
    "Do not include any explanation, only the JSON array."
)

RELEVANCE_INSTRUCTIONS = {
    0: (  # STRICT - High precision
        "Analyze the document and return ONLY a JSON array of zero-indexed line numbers that DIRECTLY and PRECISELY match the user's query. "
        "Be selective and only include lines that are highly relevant and directly address the query topic. "
        "Exclude lines that are only tangentially related or mention the topic in passing. "
    ),
    1: (  # NORMAL - Balanced
        "Analyze the document and return ONLY a JSON array of zero-indexed line numbers that semantically match the user's query. "
        "Include ALL lines that are relevant to the query, not just a few examples. "
    ),
    2: (  # LOOSE - High recall
        "Analyze the document and return ONLY a JSON array of zero-indexed line numbers that match OR relate to the user's query. "
        "Be inclusive and include ALL lines that mention, relate to, or provide context about the query topic. "
        "Include lines that are tangentially related, contain related concepts, or provide relevant background. "
    )
}


# ----------------------------
# DeepSeek semantic search
# ----------------------------
def semantic_search(query: str, lines: list, relevance_level: int = 1) -> tuple:
    """
    Use DeepSeek to find line numbers that semantically match the query.
    Lines are cleaned (whitespace stripped) and formatted with line numbers before sending to API.

    Args:
        query: The search query
        lines: List of file lines
        relevance_level: Search precision (0=STRICT, 1=NORMAL, 2=LOOSE)

    Returns a tuple: (line_numbers_set, error_message)
    - On success: (set of zero-indexed line numbers, None)
    - On error: (empty set, error string)

    Relevance Levels:
    - 0 (STRICT): Only direct, precise matches - high precision, low recall
    - 1 (NORMAL): All relevant lines - balanced (default)
    - 2 (LOOSE): Include tangential relations - high recall, lower precision

    Error formats:
    - Connection errors: "Connection Error: Could not reach DeepSeek API"
    - Timeout errors: "Request Timeout: API took too long to respond"
    - Rate limit (429): "429 - Rate Limit: Too many requests"
    - Authentication (401): "401 - Authentication Failed: Invalid API key"
    - Insufficient balance (402): "402 - Insufficient Balance"
    - Other status errors: "500 - Internal Server Error"
    - JSON parsing: "Error: Invalid JSON response from API"
    - Invalid format: "Error: Invalid response format (expected array)"
    """
    # Clean and format lines with line numbers
    numbered_lines = [f"[LINE {i}]: {line.strip()}" for i, line in enumerate(lines)]
    document_text = "\n".join(numbered_lines)

    # Construct system prompt from components
    relevance_instruction = RELEVANCE_INSTRUCTIONS.get(relevance_level, RELEVANCE_INSTRUCTIONS[1])
    system_prompt = PROMPT_BASE + relevance_instruction + PROMPT_FORMAT

    # First try-except: DeepSeek API request
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": f"Find all lines semantically related to: '{query}'\n\nDocument:\n{document_text}"}
            ],
            stream=False,
        )
        result = response.choices[0].message.content.strip()
    except openai.APIConnectionError as e:
        # Network connection failures
        return (set(), "Connection Error: Could not reach DeepSeek API")
    except openai.APITimeoutError as e:
        # Request timeout
        return (set(), "Request Timeout: API took too long to respond")
    except openai.RateLimitError as e:
        # 429 - Rate limit exceeded
        return (set(), "429 - Rate Limit: Too many requests")
    except openai.AuthenticationError as e:
        # 401 - Invalid API key
        return (set(), "401 - Authentication Failed: Invalid API key")
    except openai.APIStatusError as e:
        # Catches all HTTP status errors (400, 402, 403, 404, 500, etc.)
        # Explicitly handle 402 for DeepSeek insufficient balance
        if e.status_code == 402:
            return (set(), "402 - Insufficient Balance")
        else:
            # Use e.message for cleaner error text
            return (set(), f"{e.status_code} - {e.message}")
    except openai.APIError as e:
        # Catch-all for other API errors
        return (set(), f"API Error: {e.message}")
    except Exception as e:
        # Unexpected non-API errors
        return (set(), f"Unexpected Error: {str(e)}")

    # Second try-except: JSON parsing and validation
    try:
        line_numbers = json.loads(result)

        # Validate it's a list
        if not isinstance(line_numbers, list):
            return (set(), "Error: Invalid response format (expected array). Try again.")

        # Filter and validate each line number
        valid_lines = set()
        total_lines = len(lines)

        for item in line_numbers:
            # Check if it's an integer
            if not isinstance(item, int):
                continue  # Skip invalid entries silently

            # Check if it's in valid range (0-indexed)
            if 0 <= item < total_lines:
                valid_lines.add(item)

        return (valid_lines, None)

    except json.JSONDecodeError as e:
        return (set(), "Error: Invalid JSON response from API")
    except Exception as e:
        return (set(), f"Error: {str(e)}")


# ----------------------------
# File loader
# ----------------------------
def load_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


# ----------------------------
# Display logic
# ----------------------------
class SemanticLess:
    def __init__(self, stdscr, filepath):
        self.stdscr = stdscr
        self.filepath = filepath
        self.lines = load_file(filepath)
        self.pos = 0
        self.query = ""
        self.highlighted_lines = set()
        self.match_list = []  # Sorted list of matched line numbers for navigation
        self.current_match_index = -1  # Current position in match_list (-1 = no active match)
        self.error_message = None
        self.relevance_level = 1  # 0=STRICT, 1=NORMAL (default), 2=LOOSE
        self.height, self.width = self.stdscr.getmaxyx()
        self.wrap_width = self.width - 2

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        self.height = height
        start = self.pos
        end = start + height - 2

        # Always show original file content
        display_lines = self.lines[start:end]

        for i, line in enumerate(display_lines[: height - 2]):
            try:
                absolute_line_idx = start + i
                # Apply highlighting if this line is in the highlighted set
                if absolute_line_idx in self.highlighted_lines:
                    self.stdscr.addstr(i, 0, line[: width - 1], curses.A_REVERSE)
                else:
                    self.stdscr.addstr(i, 0, line[: width - 1])
            except curses.error:
                pass

        # Status line
        level_names = ["STRICT", "NORMAL", "LOOSE"]
        status = f"{self.filepath}  |  Line {self.pos+1}/{len(self.lines)}  |  Relevance: {level_names[self.relevance_level]}"
        if self.query:
            status += f"  |  Search: {self.query}"
        if self.error_message:
            status += f"  |  {self.error_message}"
        elif self.highlighted_lines:
            status += f"  |  {len(self.highlighted_lines)} matches"
            # Show current match position if navigating
            if self.current_match_index >= 0 and self.match_list:
                status += f" (Match {self.current_match_index + 1}/{len(self.match_list)})"
        self.stdscr.addstr(height - 1, 0, status[: width - 1], curses.A_REVERSE)
        self.stdscr.refresh()

    def prompt(self, prompt_str):
        """
        Displays a prompt at the bottom of the screen
        and gets text input from the user.
        Returns the input_str.
        """
        curses.echo() # show typed keys
        self.stdscr.addstr(self.height - 1, 0, prompt_str)
        self.stdscr.clrtoeol() # clear old status bar

        # waits for the user to type and press Enter, start reading after the given prompt_str
        input_str = self.stdscr.getstr(self.height - 1, len(prompt_str)).decode("utf-8")
        curses.noecho() # hide typed keys
        return input_str.strip()

    def _execute_search(self):
        """
        Execute semantic search with current query and relevance level.
        Updates highlighted_lines, match_list, error_message, and scrolls to first match.
        """
        self.error_message = None
        line_numbers, error = semantic_search(self.query, self.lines, self.relevance_level)
        self.error_message = error

        # Only process highlights if no error
        if not error:
            self.highlighted_lines = line_numbers
            # Create sorted list for navigation
            if self.highlighted_lines:
                self.match_list = sorted(self.highlighted_lines)
                self.current_match_index = 0
                self.pos = self.match_list[0]  # Jump to first match
            else:
                self.match_list = []
                self.current_match_index = -1
        else:
            # Clear highlights and navigation state if there was an error
            self.highlighted_lines = set()
            self.match_list = []
            self.current_match_index = -1

    def _jump_to_match(self, index):
        """
        Navigate to a specific match by index in match_list.
        Updates current_match_index and scrolls to the match line.
        """
        if not self.match_list or index < 0 or index >= len(self.match_list):
            return  # No matches or invalid index

        self.current_match_index = index
        self.pos = self.match_list[index]

    def _clear_search(self):
        """
        Clear all search state: highlights, navigation, query, and errors.
        """
        self.highlighted_lines = set()
        self.match_list = []
        self.current_match_index = -1
        self.query = ""
        self.error_message = None

    def run(self):
        while True:
            self.draw()
            c = self.stdscr.getch()

            if c in (ord('q'), 27):  # q or ESC
                # If search is active, clear it first; otherwise quit
                if self.query:
                    self._clear_search()
                else:
                    # No active search, quit the program
                    break
            elif c == curses.KEY_DOWN or c == ord('j'):
                if self.pos < len(self.lines) - 1:
                    self.pos += 1
            elif c == curses.KEY_UP or c == ord('k'):
                if self.pos > 0:
                    self.pos -= 1
            elif c == curses.KEY_NPAGE:  # Page down
                self.pos = min(self.pos + self.height - 2, len(self.lines) - 1)
            elif c == curses.KEY_PPAGE:  # Page up
                self.pos = max(self.pos - (self.height - 2), 0)
            elif c == 4:  # Ctrl-D - scroll down half page
                half_page = (self.height - 2) // 2
                self.pos = min(self.pos + half_page, len(self.lines) - 1)
            elif c == 21:  # Ctrl-U - scroll up half page
                half_page = (self.height - 2) // 2
                self.pos = max(self.pos - half_page, 0)
            elif c == curses.KEY_HOME:  # Jump to start of file
                self.pos = 0
            elif c == curses.KEY_END:  # Jump to end of file
                self.pos = len(self.lines) - 1
            elif c == ord('/'):  # Semantic search
                self.query = self.prompt("/")
                if self.query:
                    self._execute_search()
            elif c == ord('c'):  # Clear search results
                self._clear_search()
            elif c == ord('n') or c == ord('l') or c == curses.KEY_RIGHT:  # Next match
                if self.match_list:
                    next_index = (self.current_match_index + 1) % len(self.match_list)
                    self._jump_to_match(next_index)
            elif c == ord('N') or c == ord('h') or c == curses.KEY_LEFT:  # Previous match
                if self.match_list:
                    prev_index = (self.current_match_index - 1) % len(self.match_list)
                    self._jump_to_match(prev_index)
            elif c == ord('r'):  # Cycle relevance level
                # Cycle through levels: STRICT (0) -> NORMAL (1) -> LOOSE (2) -> STRICT (0)
                self.relevance_level = (self.relevance_level + 1) % 3
                # UI will automatically update to show new level in status bar
                # Does NOT re-run search - user must press Enter to re-search
            elif c == ord('\n') or c == curses.KEY_ENTER:  # Enter key - re-run search
                # Only re-run if there's an active query
                # If user pressed 'c' to clear, self.query is "", so this does nothing
                if self.query:
                    self._execute_search()


# ----------------------------
# Entry point
# ----------------------------
def main(stdscr, filepath):
    curses.curs_set(0)
    viewer = SemanticLess(stdscr, filepath)
    viewer.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Semantic search text viewer using DeepSeek API")
    parser.add_argument("file", help="Path to the text file")
    args = parser.parse_args()

    curses.wrapper(main, args.file)
