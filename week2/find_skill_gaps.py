from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field


BATCH_SIZE = 200
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.5


class SkillDemandStat(BaseModel):
    skill: str
    job_count: int
    demand_share: float
    rank: int
    covered_in_resume: bool


class SkillGapResult(BaseModel):
    gaps: list[str]
    matched_skills: list[str] = Field(default_factory=list)
    ignored_skills: list[str] = Field(default_factory=list)
    skill_stats: list[SkillDemandStat] = Field(default_factory=list)
    total_jobs: int = 0
    total_unique_job_skills: int = 0
    tokens_used: int = 0
    time_used_seconds: float = 0.0
    notes: list[str] = Field(default_factory=list)


_CANONICAL_SKILL_PATTERNS: dict[str, tuple[str, ...]] = {
    "c/c++": (r"\bc/c\+\+\b", r"\bc\+\+\b", r"(?<![a-z0-9])c(?![a-z0-9])"),
    "python": (r"\bpython\b",),
    "sql": (r"\bsql\b", r"\bmysql\b", r"\bpostgres(?:ql)?\b", r"\bsqlite\b", r"\boracle sql\b"),
    "java": (r"\bjava\b",),
    "javascript": (r"\bjavascript\b", r"\bnode\.js\b", r"\bnodejs\b"),
    "php": (r"\bphp\b",),
    "r": (r"\br\b", r"\bpower bi\b", r"\bpowerbi\b", r"\btableau\b", r"\bexcel\b"),
    "docker": (r"\bdocker\b", r"\bcontainer(s)?\b"),
    "kubernetes": (r"\bkubernetes\b", r"\bk8s\b"),
    "git": (r"\bgit\b", r"\bgithub\b", r"\bcode review\b", r"\bci/cd\b"),
    "llm/rag": (r"\bllm\b", r"\brag\b", r"\bgenai\b", r"\bgen ai\b", r"\bchatbot\b", r"\bprompt engineering\b"),
    "machine learning": (r"\bmachine learning\b", r"\bml\b", r"\bpytorch\b", r"\btensorflow\b", r"\bscikit-learn\b", r"\bxgboost\b"),
    "apis": (r"\bapi\b", r"\brest\b", r"\bgraphql\b", r"\bmicroservice\b"),
    "databases": (r"\bdatabase\b", r"\bdatabases\b", r"\bmongodb\b", r"\bredis\b", r"\betl\b"),
    "shell": (r"\bshell\b", r"\bbash\b", r"\bpowershell\b"),
    "testing": (r"\btesting\b", r"\bpytest\b", r"\bunit test\b"),
}

_CANONICAL_SKILLS = tuple(sorted(_CANONICAL_SKILL_PATTERNS))


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _resolve_existing_path(candidate_paths: Iterable[Path]) -> Path | None:
    for path in candidate_paths:
        if path.exists():
            return path.resolve()
    return None


def _resolve_resume_path(input_file_path: str) -> Path | None:
    raw_path = (input_file_path or "").strip()
    candidates: list[Path] = []
    if raw_path:
        candidate = Path(raw_path).expanduser()
        candidates.append(candidate)
        if not candidate.is_absolute():
            candidates.append(_script_dir() / candidate)

    candidates.append(_script_dir() / "data" / "resume.txt")
    candidates.append(_script_dir() / "data" / "resume_d3.txt")

    return _resolve_existing_path(candidates)


def _candidate_db_paths() -> list[Path]:
    base_dir = _script_dir()
    return [
        base_dir / "data" / "jobs_d1.db",
        base_dir / "data" / "3_gold" / "jobs.db",
    ]


def _resolve_db_path(db_url: str | None) -> Path | None:
    candidates: list[Path] = []
    raw_url = (db_url or "").strip()
    if raw_url:
        if raw_url.startswith("sqlite:///"):
            raw_url = raw_url.replace("sqlite:///", "", 1)
        candidates.append(Path(raw_url).expanduser())

    env_path = os.environ.get("TAG_DATA_DB_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.extend(_candidate_db_paths())
    return _resolve_existing_path(candidates)


def _estimate_tokens(*texts: str) -> int:
    word_count = 0
    for text in texts:
        word_count += len(re.findall(r"\S+", text or ""))
    return math.ceil(word_count / 4) if word_count else 0


def _normalize_skill(raw_skill: str) -> str:
    cleaned = _clean_text(raw_skill).lower()
    if not cleaned:
        return ""

    cleaned = cleaned.replace("cplusplus", "c++")
    cleaned = cleaned.replace("c / c++", "c/c++")
    cleaned = cleaned.replace("c plus plus", "c++")

    for canonical, patterns in _CANONICAL_SKILL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                return canonical

    if cleaned in _CANONICAL_SKILLS:
        return cleaned

    return ""


def _extract_resume_skill_block(text: str) -> str:
    lines = [line.rstrip() for line in (text or "").splitlines()]
    if not lines:
        return ""

    captured: list[str] = []
    in_skills = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_skills:
                captured.append("")
            continue

        upper = stripped.upper()
        if upper == "SKILLS":
            in_skills = True
            continue
        if in_skills and upper in {"CERTIFICATIONS", "PROJECTS", "EXPERIENCE", "SUMMARY", "EDUCATION"}:
            break
        if in_skills:
            captured.append(stripped)

    if captured:
        return "\n".join(captured)

    return text or ""


def _extract_resume_skills(text: str) -> tuple[list[str], list[str]]:
    skill_block = _extract_resume_skill_block(text)
    technical_candidates: list[str] = []
    ignored: list[str] = []

    for chunk in re.split(r"[,;/\n]", skill_block):
        candidate = _clean_text(chunk)
        if not candidate:
            continue
        normalized = _normalize_skill(candidate)
        if normalized:
            technical_candidates.append(normalized)
        else:
            ignored.append(candidate.lower())

    # Scan the whole resume as a safety net, but only keep known technical aliases.
    resume_blob = (text or "").lower()
    for canonical, patterns in _CANONICAL_SKILL_PATTERNS.items():
        if canonical in technical_candidates:
            continue
        if any(re.search(pattern, resume_blob, flags=re.IGNORECASE) for pattern in patterns):
            technical_candidates.append(canonical)

    deduped_skills: list[str] = []
    for skill in technical_candidates:
        if skill not in deduped_skills:
            deduped_skills.append(skill)

    return deduped_skills, ignored


def _parse_tech_stack(value: str) -> list[str]:
    parsed: list[str] = []
    for chunk in str(value or "").split(","):
        normalized = _normalize_skill(chunk)
        if normalized and normalized not in parsed:
            parsed.append(normalized)
    return parsed


def _row_to_skill_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(row.get("source_id", "")).strip(),
        "job_title": str(row.get("job_title", "")).strip(),
        "tech_stack": str(row.get("tech_stack", "")).strip(),
    }


def _load_jobs_direct(db_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT rowid, source_id, job_title, tech_stack
                FROM jobs
                WHERE tech_stack IS NOT NULL AND TRIM(tech_stack) != ''
                ORDER BY rowid
                """
            )
            for row in cursor.fetchall():
                rows.append(_row_to_skill_row(dict(row)))
    except sqlite3.Error:
        return []
    except Exception:
        return []
    return rows


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


async def _call_mcp_tool(session: Any, tool_name: str, arguments: dict[str, Any]) -> Any:
    if hasattr(session, "call_tool"):
        return await session.call_tool(tool_name, arguments)
    if hasattr(session, "invoke_tool"):
        return await session.invoke_tool(tool_name, arguments)
    raise RuntimeError("MCP session does not expose a tool-call method")


async def _load_jobs_via_mcp(db_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    notes: list[str] = []
    try:
        from fastmcp import Client
    except Exception as exc:
        return [], [f"MCP client unavailable: {exc}"]

    server_path = _script_dir() / "src" / "sqlite_mcp_server.py"
    if not server_path.exists():
        return [], [f"MCP server not found: {server_path}"]

    rows: list[dict[str, Any]] = []
    last_rowid = 0

    try:
        async with Client(str(server_path)) as mcp_client:
            for attempt in range(MAX_RETRIES):
                try:
                    while True:
                        batch_result = await _call_mcp_tool(
                            mcp_client.session,
                            "fetch_tagged_jobs",
                            {"after_rowid": last_rowid, "batch_size": BATCH_SIZE, "db_path": str(db_path)},
                        )
                        batch_payload = _parse_tool_payload(batch_result)
                        batch = batch_payload if isinstance(batch_payload, list) else []
                        if not batch:
                            break

                        for item in batch:
                            if isinstance(item, dict):
                                rows.append(_row_to_skill_row(item))

                        try:
                            last_rowid = int(batch[-1].get("rowid", last_rowid))
                        except Exception:
                            break

                    break
                except Exception as exc:
                    notes.append(f"MCP attempt {attempt + 1} failed: {exc}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
    except Exception as exc:
        notes.append(f"MCP client error: {exc}")

    return rows, notes


def _summarize_demand(
    job_rows: list[dict[str, Any]], resume_skills: set[str]
) -> tuple[list[str], list[SkillDemandStat], list[str], int, int]:
    demand_counter: Counter[str] = Counter()
    for row in job_rows:
        row_skills = _parse_tech_stack(row.get("tech_stack", ""))
        for skill in set(row_skills):
            demand_counter[skill] += 1

    total_jobs = len(job_rows)
    total_unique_skills = len(demand_counter)
    gaps = sorted(skill for skill in demand_counter if skill not in resume_skills)
    matched_skills = sorted(skill for skill in demand_counter if skill in resume_skills)

    ordered = sorted(demand_counter.items(), key=lambda item: (-item[1], item[0]))
    stats: list[SkillDemandStat] = []
    for rank, (skill, count) in enumerate(ordered, start=1):
        stats.append(
            SkillDemandStat(
                skill=skill,
                job_count=count,
                demand_share=(count / total_jobs) if total_jobs else 0.0,
                rank=rank,
                covered_in_resume=skill in resume_skills,
            )
        )

    return gaps, stats, matched_skills, total_jobs, total_unique_skills


def _estimate_processing_tokens(resume_text: str, job_rows: list[dict[str, Any]], result: SkillGapResult) -> int:
    job_blob = "\n".join(
        f"{row.get('source_id', '')} {row.get('job_title', '')} {row.get('tech_stack', '')}" for row in job_rows
    )
    result_blob = result.model_dump_json(exclude_none=True)
    return _estimate_tokens(resume_text, job_blob, result_blob)


def _default_result(notes: list[str] | None = None) -> SkillGapResult:
    return SkillGapResult(gaps=[], notes=notes or [])


async def _find_skill_gaps_async(input_file_path: str, db_url: str) -> SkillGapResult:
    start_time = time.perf_counter()
    notes: list[str] = []

    resume_path = _resolve_resume_path(input_file_path)
    if resume_path is None:
        notes.append("Resume file not found")
        return _default_result(notes)

    db_path = _resolve_db_path(db_url)
    if db_path is None:
        notes.append("Database file not found")
        return _default_result(notes)

    try:
        resume_text = resume_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        notes.append(f"Unable to read resume: {exc}")
        return _default_result(notes)

    resume_skills, ignored_skills = _extract_resume_skills(resume_text)
    resume_skill_set = set(resume_skills)

    job_rows, mcp_notes = await _load_jobs_via_mcp(db_path)
    notes.extend(mcp_notes)
    if not job_rows:
        job_rows = _load_jobs_direct(db_path)
        if not job_rows:
            notes.append("No tagged jobs found")
            elapsed_seconds = time.perf_counter() - start_time
            return SkillGapResult(
                gaps=[],
                matched_skills=resume_skills,
                ignored_skills=sorted(set(ignored_skills)),
                total_jobs=0,
                total_unique_job_skills=0,
                tokens_used=_estimate_tokens(resume_text),
                time_used_seconds=elapsed_seconds,
                notes=notes,
            )

    gaps, stats, matched_skills, total_jobs, total_unique_job_skills = _summarize_demand(job_rows, resume_skill_set)
    result = SkillGapResult(
        gaps=gaps,
        matched_skills=matched_skills,
        ignored_skills=sorted(set(ignored_skills)),
        skill_stats=stats,
        total_jobs=total_jobs,
        total_unique_job_skills=total_unique_job_skills,
        notes=notes,
    )
    result.tokens_used = _estimate_processing_tokens(resume_text, job_rows, result)
    result.time_used_seconds = time.perf_counter() - start_time
    return result


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
    try:
        return asyncio.run(_find_skill_gaps_async(input_file_path, db_url))
    except KeyboardInterrupt:
        return _default_result(["Cancelled"])
    except Exception as exc:
        return _default_result([f"Unexpected error: {exc}"])


def _format_cli_output(result: SkillGapResult) -> str:
    return f"gaps={result.gaps} time={round(result.time_used_seconds, 3)} tokens={result.tokens_used}"


def main(argv: list[str]) -> int:
    input_path = argv[1] if len(argv) > 1 else ""
    db_path = argv[2] if len(argv) > 2 else ""
    result = find_skill_gaps(input_path, db_path)
    print(_format_cli_output(result))
    if result.notes:
        for note in result.notes:
            print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))