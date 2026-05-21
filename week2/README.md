# kyouth-data-ai-aida-sophea Module 2

Week 2 extends the project with model prompting, job data enrichment, and skill gap analysis.

## Project Description

This folder contains three main scripts:
- `prompt_model.py`: routes prompts to local Ollama or Google Gemini.
- `tag_data.py`: enriches `jobs` records by inferring missing `tech_stack` tags.
- `find_skill_gaps.py`: computes missing in-demand skills from tagged job records.

The goal is to support offline testing with Ollama while also allowing cloud-based prompting through Gemini when available.

## Project Structure

```text
week2/
  prompt_model.py          # model prompt wrapper for Ollama and Gemini
  tag_data.py             # batch job tagging for missing tech_stack values
  find_skill_gaps.py      # skills gap extraction from job records
  pyproject.toml          # Python 3.14 project dependencies
  rate_limits.txt         # Gemini rate limit placeholders
  data/
    resume_d3.txt         # example resume text for skill extraction
    jobs_d1.db            # sample SQLite database candidate
  src/
    sqlite_mcp_server.py  # local SQLite MCP helper module (supporting data work)
```

## Project Setup

### Local Python environment

From the `week2` folder:

```powershell
cd C:\Users\aida.zaki\kyouth-data-ai-aida-sophea\week2
uv venv .venv --python 3.14
.\.venv\Scripts\Activate.ps1
uv lock
uv sync
```

### Optional: Ollama setup

If you want to use local model prompting, install Ollama and pull the models:

```powershell
irm https://ollama.com/install.ps1 | iex
ollama pull llama3.1
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

Verify Ollama with:

```powershell
ollama -v
Invoke-RestMethod http://127.0.0.1:11434/
```

### Optional: Google Gemini setup

Create a Google AI Studio API key at:

https://aistudio.google.com/

Then set it in PowerShell:

```powershell
$env:GOOGLE_API_KEY="your_key_here"
```

Do not store the key in the repository.

## Usage

### Project Setup

#### Prompt a model

```powershell
uv run python prompt_model.py llama3.1 "tell me one Malaysian joke"
```

For Gemini:

```powershell
uv run python prompt_model.py gemini-2.5-flash "tell me one Malaysian joke"
```

### Day 1 - 2

#### Tag missing job tech stacks

```powershell
uv run tag_data.py
```

With explicit database path:

```powershell
uv run tag_data.py C:\Users\aida.zaki\kyouth-data-ai-aida-sophea\week2\data\jobs_d1.db
```

### Day 3 - 4

#### Compute skill gaps

```powershell
uv run find_skill_gaps.py
```

With explicit database path:

```powershell
uv run find_skill_gaps.py C:\Users\aida.zaki\kyouth-data-ai-aida-sophea\week2\data\resume_d3.txt
```

## Key Scripts

### `prompt_model.py`
- Routes prompts to:
  - local Ollama for models like `llama3.1`
  - Google Gemini for models starting with `gemini-`
- Returns generated text or a descriptive error string.
- Uses standard library networking and retry logic.

### `tag_data.py`
- Finds a SQLite jobs database.
- Enriches empty `tech_stack` rows with short tag lists.
- Uses Gemini when `GOOGLE_API_KEY` is set.
- Falls back to deterministic rule-based tagging when no API key is available.

### `find_skill_gaps.py`
- Reads jobs with non-empty `tech_stack`.
- Maps job tags to canonical skills.
- Writes missing `skill_gaps` values back to the database.
- Includes basic resume skill extraction support.

## Data and Assumptions

- Expected database structure:
  - Table `jobs` with at least `rowid`, `source_id`, `job_title`, `tech_stack`.
- Candidate files:
  - `week2/data/jobs_d1.db`
  - `week2/data/resume_d3.txt`
- `tag_data.py` is designed for records with empty `tech_stack`.
- `find_skill_gaps.py` is designed for records with existing `tech_stack` values.

## Notes

- `prompt_model.py` is resilient: it always returns a string, even on failure.
- `tag_data.py` and `find_skill_gaps.py` both support optional explicit DB path arguments.
- Rate limits for Gemini can be stored in `rate_limits.txt` if needed.

## Limitations

- Prompt accuracy depends on the chosen model and provider.
- The `find_skill_gaps.py` matching logic is heuristic and based on pattern matching.
- This module is built for educational/demo use, not production scaling.

## Improvements

If extended, the project could benefit from:
- formal unit and integration tests
- a shared database helper module
- improved prompt validation and structured response parsing
- explicit status reporting and dry-run support
