# Week 2

Week 2 focuses on model prompting with both local Ollama and Google Gemini.

## Project Setup

Create and activate a virtual environment from inside `week2`:

```powershell
cd C:\Users\aida.zaki\kyouth-data-ai-aida\week2
uv venv .venv --python 3.14
.\.venv\Scripts\Activate.ps1
```

Install dependencies from `pyproject.toml`:

```powershell
uv lock
uv sync
```

## Ollama Setup

Install Ollama on Windows:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Verify Ollama is running:

```powershell
ollama -v
Invoke-RestMethod http://127.0.0.1:11434/
```

Pull the required local models:

```powershell
ollama pull llama3.1
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

If the first prompt is slow, the model may still be loading in the background.

## Google AI Studio Setup

Create a free API key at:

https://aistudio.google.com/

Set the API key in your current terminal session:

```powershell
$env:GOOGLE_API_KEY="your_key_here"
```

Do not commit the API key to the repository.

## Rate Limits

Store the Google model rate limits in `rate_limits.txt` using this format:

```text
gemini-2.5-flash <RPM> <TPM> <RPD>
gemini-2.5-flash-lite <RPM> <TPM> <RPD>
gemini-3-flash-preview <RPM> <TPM> <RPD>
```

## Run The Prompt Script

The script accepts a model name and a prompt. Use the Python form below, which is the most reliable on this workspace:

```powershell
uv run python prompt_model.py llama3.1 "tell me one malasyian joke"
```

Example Gemini call:

```powershell
uv run python prompt_model.py gemini-2.5-flash "tell me one malasyian joke"
```

## Notes

- Use local Ollama models for offline testing and Gemini for cloud-based prompting.
- If `uv run` tries to create a new environment unexpectedly, stay inside `week2` and run the command shown above.
- The prompt script prints `--- RESPONSE ---` and always returns a string, even when a provider call fails.

## Day 1-2: Tagging

This task enriches the `tech_stack` column in the SQLite `jobs` table by reading each job description, inferring the technologies used, and writing back comma-separated tags.

### Requirements

- Use a SQLite database file such as `jobs_d1.db` or the week 1 gold database.
- Only rows with an empty `tech_stack` value are tagged.
- Updates are processed in batches and each written stack is logged to standard output.
- The script handles missing databases and runtime errors gracefully.

### Run Command

Use this command from inside the `week2` folder:

```powershell
uv run tag_data.py
```

If you want to pass a specific database path explicitly, use:

```powershell
uv run tag_data.py C:\path\to\jobs_d1.db
```

## Day 3-4 : Skill Gaps
This task identifies skill gaps for each job by comparing the `tech_stack` against a predefined list of in-demand technologies. The results are stored in a new `skill_gaps` column.

### Requirements
- The script reads from the same SQLite database and processes rows with non-empty `tech_stack` values.
- For each job, it determines which in-demand technologies are missing from the `tech_stack` and writes these as comma-separated values in the `skill_gaps` column.
- The script handles errors gracefully and logs updates to standard output.     

### Run Command
Use this command from inside the `week2` folder:

```powershell
uv run find_skill_gaps.py
```

If you want to pass a specific database path explicitly, use:

```powershell
uv run find_skill_gaps.py C:\path\to\jobs_d1.db
``` 

