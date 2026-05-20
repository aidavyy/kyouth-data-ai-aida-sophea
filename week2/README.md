# Week 2

Week 2 focuses on model prompting with both local Ollama and Google Gemini.

## Project Setup

Create and activate a virtual environment from inside `week2`:

```powershell
cd C:\Users\adam arbain\kyouth-data-ai-adam\week2
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