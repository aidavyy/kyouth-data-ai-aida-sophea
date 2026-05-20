from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


BATCH_SIZE = 5
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _candidate_db_paths() -> list[Path]:
    base_dir = _script_dir()
    return [
        base_dir / "data" / "jobs_d1.db",
        base_dir / "data" / "3_gold" / "jobs.db",
    ]


def _resolve_db_path(db_url: str | None) -> Path | None:
    candidates: list[Path] = []
    if db_url and db_url.strip():
        candidates.append(Path(db_url.strip()).expanduser())

    env_path = os.environ.get("TAG_DATA_DB_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.extend(_candidate_db_paths())

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _estimate_tokens(text: str) -> int:
    words = re.findall(r"\S+", text or "")
    return math.ceil(len(words) / 4) if words else 0


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _truncate(value: str, limit: int = 700) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _rule_based_stack(job_title: str, description: str) -> str:
    blob = f"{job_title}\n{description}".lower()
    patterns = [
        ("Python", ["python"]),
        ("SQL", ["sql", "postgres", "mysql", "sqlite", "oracle sql"]),
        ("Java", ["java"]),
        ("JavaScript", ["javascript", "node.js", "nodejs", "node "]),
        ("TypeScript", ["typescript"]),
        ("PHP", ["php"]),
        ("C#", ["c#", ".net", "dotnet", "c sharp"]),
        ("ABAP", ["abap"]),
        ("R", ["\br\b", "powerbi", "tableau", "excel"]),
        ("Spark", ["spark", "pyspark"]),
        ("Hadoop", ["hadoop"]),
        ("Airflow", ["airflow"]),
        ("Docker", ["docker", "container"]),
        ("Kubernetes", ["kubernetes", "k8s"]),
        ("Git", ["git", "code review", "ci/cd"]),
        ("LLM/RAG", ["llm", "rag", "genai", "gen ai", "prompt", "chatbot"]),
        ("Machine Learning", ["machine learning", "ml ", "ml,", "scikit-learn", "xgboost", "pytorch", "tensorflow"]),
        ("APIs", ["api", "rest", "graphql", "microservice"]),
        ("Databases", ["database", "databases", "mongodb", "redis", "etl"]),
        ("Shell", ["shell", "bash", "powershell"]),
        ("Testing", ["testing", "pytest", "unit test"]),
    ]

    values: list[str] = []
    for label, tokens in patterns:
        if any(token in blob for token in tokens):
            values.append(label)

    if not values:
        values = ["Python"] if "engineer" in blob else ["SQL"]

    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return ", ".join(deduped)


def _extract_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]

    return cleaned


def _normalize_rows(payload: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    if isinstance(payload, dict):
        if isinstance(payload.get("rows"), list):
            payload = payload["rows"]
        elif isinstance(payload.get("results"), list):
            payload = payload["results"]
        elif all(key in payload for key in ("source_id", "tech_stack")):
            payload = [payload]

    if not isinstance(payload, list):
        return rows

    for item in payload:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id", "")).strip()
        tech_stack = str(item.get("tech_stack", "")).strip()
        if source_id and tech_stack:
            rows.append({"source_id": source_id, "tech_stack": tech_stack})
    return rows


def _format_batch_prompt(batch: list[dict[str, Any]]) -> str:
    records = []
    for row in batch:
        records.append(
            {
                "source_id": str(row.get("source_id", "")),
                "job_title": _truncate(str(row.get("job_title", "")), 120),
                "description": _truncate(str(row.get("description", "")), 650),
            }
        )

    return (
        "Tag the tech stack for each job using only the records below. "
        "Return strict JSON only, no markdown, no explanations. "
        "The response must be a JSON array with exactly one object per input record. "
        "Each object must have source_id and tech_stack. "
        "Use short comma-separated technical terms. "
        "If you are unsure, infer from the job title and description.\n\n"
        f"Records:\n{json.dumps(records, ensure_ascii=True)}"
    )


def _extract_text_from_response(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list):
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if isinstance(parts, list):
                chunks = []
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text.strip():
                        chunks.append(part_text)
                if chunks:
                    return "".join(chunks)

    if isinstance(response, dict):
        for key in ("text", "output", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return ""


def _extract_usage_tokens(response: Any, prompt_text: str, response_text: str) -> int:
    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        total = getattr(usage, "total_token_count", None)
        if isinstance(total, int):
            return total
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        response_tokens = getattr(usage, "candidates_token_count", None)
        if isinstance(prompt_tokens, int) and isinstance(response_tokens, int):
            return prompt_tokens + response_tokens

    return _estimate_tokens(prompt_text) + _estimate_tokens(response_text)


async def _call_mcp_tool(session: Any, tool_name: str, arguments: dict[str, Any]) -> Any:
    if hasattr(session, "call_tool"):
        return await session.call_tool(tool_name, arguments)
    if hasattr(session, "invoke_tool"):
        return await session.invoke_tool(tool_name, arguments)
    raise RuntimeError("MCP session does not expose a tool-call method")


def _parse_tool_payload(result: Any) -> Any:
    if hasattr(result, "content"):
        content = getattr(result, "content")
        if isinstance(content, list) and content:
            first = content[0]
            text = getattr(first, "text", None)
            if isinstance(text, str) and text.strip():
                try:
                    return json.loads(text)
                except Exception:
                    return text
        return content

    if isinstance(result, dict):
        return result.get("content", result)

    return result


async def _generate_tags_for_batch(mcp_session: Any, batch: list[dict[str, Any]], model_name: str) -> tuple[list[dict[str, str]], int]:
    from google import genai

    prompt = _format_batch_prompt(batch)
    expected_ids = [str(row.get("source_id", "")) for row in batch]
    token_total = 0

    # If no API key is available, skip network calls and use deterministic fallback tags.
    if not os.environ.get("GOOGLE_API_KEY", "").strip():
        fallback_rows = []
        for row in batch:
            fallback_rows.append(
                {
                    "source_id": str(row.get("source_id", "")),
                    "tech_stack": _rule_based_stack(str(row.get("job_title", "")), str(row.get("description", ""))),
                }
            )
        return fallback_rows, 0

    gemini = genai.Client()
    config = genai.types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1024,
        response_mime_type="application/json",
        tools=[mcp_session],
    )

    last_error = ""
    for attempt in range(MAX_RETRIES):
        try:
            response = await gemini.aio.models.generate_content(
                model=model_name,
                contents=prompt if not last_error else f"{prompt}\n\nPrevious response error: {last_error}",
                config=config,
            )
            response_text = _extract_text_from_response(response)
            token_total += _extract_usage_tokens(response, prompt, response_text)

            parsed_text = _extract_json_text(response_text)
            parsed_payload = json.loads(parsed_text) if parsed_text else []
            rows = _normalize_rows(parsed_payload)
            returned_ids = [row["source_id"] for row in rows]

            if len(rows) == len(batch) and set(returned_ids) == set(expected_ids):
                return rows, token_total

            last_error = (
                f"Expected {len(batch)} rows for source_ids {expected_ids}, got {returned_ids or 'no usable rows'}"
            )
        except Exception as exc:
            last_error = str(exc)

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY_SECONDS)

    fallback_rows = []
    for row in batch:
        fallback_rows.append(
            {
                "source_id": str(row.get("source_id", "")),
                "tech_stack": _rule_based_stack(str(row.get("job_title", "")), str(row.get("description", ""))),
            }
        )
    return fallback_rows, token_total


async def _tag_data_async(db_path: Path) -> dict[str, Any]:
    from fastmcp import Client

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return {"tokens_used": 0, "elapsed_ms": 0.0, "updated_rows": 0, "quality": {}}

    os.environ["TAG_DATA_DB_PATH"] = str(db_path)
    server_path = _script_dir() / "src" / "sqlite_mcp_server.py"
    if not server_path.exists():
        print(f"MCP server not found: {server_path}")
        return {"tokens_used": 0, "elapsed_ms": 0.0, "updated_rows": 0, "quality": {}}

    start_time = time.perf_counter()
    total_tokens = 0
    updated_rows = 0
    written_stacks: list[str] = []

    try:
        async with Client(str(server_path)) as mcp_client:
            pending_result = await _call_mcp_tool(
                mcp_client.session,
                "count_pending_jobs",
                {"db_path": str(db_path)},
            )
            pending_payload = _parse_tool_payload(pending_result)
            if isinstance(pending_payload, dict) and pending_payload.get("ok"):
                pending_count = int(pending_payload.get("count", 0))
            else:
                error_message = pending_payload.get("error") if isinstance(pending_payload, dict) else "unknown error"
                print(f"Failed to count pending rows: {error_message}")
                pending_count = 0

            if pending_count <= 0:
                print("No data to tag")
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                print(f"Total tokens used: 0, took {elapsed_ms:.3f}ms")
                return {"tokens_used": 0, "elapsed_ms": elapsed_ms, "updated_rows": 0, "quality": {"pending": 0}}

            last_rowid = 0
            while True:
                batch_result = await _call_mcp_tool(
                    mcp_client.session,
                    "fetch_pending_jobs",
                    {"after_rowid": last_rowid, "batch_size": BATCH_SIZE, "db_path": str(db_path)},
                )
                batch_payload = _parse_tool_payload(batch_result)
                batch = batch_payload if isinstance(batch_payload, list) else []

                if not batch:
                    break

                last_rowid = int(batch[-1].get("rowid", last_rowid))

                tagged_rows, batch_tokens = await _generate_tags_for_batch(mcp_client.session, batch, MODEL_NAME)
                total_tokens += batch_tokens

                if len(tagged_rows) != len(batch):
                    tagged_rows = [
                        {
                            "source_id": str(row.get("source_id", "")),
                            "tech_stack": _rule_based_stack(str(row.get("job_title", "")), str(row.get("description", ""))),
                        }
                        for row in batch
                    ]

                for row in tagged_rows:
                    source_id = row["source_id"]
                    tech_stack = _clean_text(row["tech_stack"])
                    if not source_id or not tech_stack:
                        continue

                    update_result = await _call_mcp_tool(
                        mcp_client.session,
                        "update_tech_stack",
                        {"source_id": source_id, "tech_stack": tech_stack, "db_path": str(db_path)},
                    )
                    update_payload = _parse_tool_payload(update_result)
                    if isinstance(update_payload, dict) and update_payload.get("ok"):
                        updated_rows += 1
                        written_stacks.append(tech_stack)
                        print(f"Analyzed Job {source_id}: {tech_stack}")

                if updated_rows >= pending_count:
                    break

    except Exception as exc:
        print(f"Tagging stopped early: {exc}")

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    duplicate_stacks = len(written_stacks) - len(set(written_stacks))
    quality = {
        "pending": max(0, len(written_stacks) - updated_rows),
        "duplicate_stack_count": max(0, duplicate_stacks),
        "unique_stack_count": len(set(written_stacks)),
    }
    print(f"Total tokens used: {total_tokens}, took {elapsed_ms:.3f}ms")
    return {
        "tokens_used": total_tokens,
        "elapsed_ms": elapsed_ms,
        "updated_rows": updated_rows,
        "quality": quality,
    }


def tag_data(db_url: str):
    db_path = _resolve_db_path(db_url)
    if db_path is None:
        print("Database not found")
        return {"tokens_used": 0, "elapsed_ms": 0.0, "updated_rows": 0, "quality": {}}

    try:
        return asyncio.run(_tag_data_async(db_path))
    except KeyboardInterrupt:
        print("Tagging cancelled")
        return {"tokens_used": 0, "elapsed_ms": 0.0, "updated_rows": 0, "quality": {"cancelled": True}}
    except Exception as exc:
        print(f"Tagging failed: {exc}")
        return {"tokens_used": 0, "elapsed_ms": 0.0, "updated_rows": 0, "quality": {"error": str(exc)}}


def _main(argv: list[str]) -> int:
    db_arg = argv[1] if len(argv) > 1 else ""
    result = tag_data(db_arg)
    if isinstance(result, dict):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))