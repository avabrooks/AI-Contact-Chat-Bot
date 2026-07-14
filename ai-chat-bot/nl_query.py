"""
Claude-powered plain-text -> SQL -> plain-English pipeline for the IT asset
chatbot.

Flow for every question:
  1. generate_sql()   - Claude turns the question into a single read-only
                         SQL SELECT statement against our known schema.
  2. _validate_sql()  - reject anything that isn't a single safe SELECT.
  3. run_query()      - execute against a read-only SQLite connection.
  4. summarize()      - Claude turns the raw rows back into a plain-English
                         answer.

Requires ANTHROPIC_API_KEY to be set (see .env.example).
"""

import json
import os
import re

from anthropic import Anthropic

from database import get_connection, get_schema_description

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Anthropic(api_key=api_key)
    return _client


SQL_SYSTEM_PROMPT = f"""You translate plain-English questions about company IT equipment into a
single SQLite SELECT query.

{get_schema_description()}

Rules:
- Output ONLY the raw SQL query. No markdown fences, no explanation, no trailing semicolon commentary.
- Only ever write a SELECT statement. Never write INSERT/UPDATE/DELETE/DROP/ALTER/ATTACH/PRAGMA.
- Use LIKE with wildcards for name/text matching so partial names and different casing still match.
- If the question is ambiguous, make the most reasonable interpretation and still return a query.
- If the question cannot be answered from this schema at all, output exactly: NO_QUERY
"""

ANSWER_SYSTEM_PROMPT = """You are an internal IT helpdesk assistant. You are given the user's
original question and the JSON rows returned from the database. Write a short, direct, plain-English
answer using only that data. If the rows are empty, say clearly that nothing was found. Do not
mention SQL, databases, or JSON in your answer -- just answer like a helpful coworker. Keep it
concise: a sentence or two, or a short list if there are multiple items worth naming individually.
"""

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|create|replace|vacuum)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> str:
    sql = sql.strip().strip("`").strip()
    if sql.upper() == "NO_QUERY":
        raise ValueError("NO_QUERY")
    if ";" in sql.rstrip(";"):
        raise ValueError("Multiple statements are not allowed.")
    if not re.match(r"(?is)^\s*select\b", sql):
        raise ValueError("Only SELECT statements are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a disallowed keyword.")
    return sql.rstrip(";")


def generate_sql(question: str) -> str:
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SQL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    raw_sql = resp.content[0].text
    return _validate_sql(raw_sql)


def run_query(sql: str, limit: int = 200):
    conn = get_connection(read_only=True)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        results = [dict(zip(cols, row)) for row in rows[:limit]]
        return results
    finally:
        conn.close()


def summarize(question: str, rows: list) -> str:
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=ANSWER_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nData (JSON): {json.dumps(rows, default=str)}",
            }
        ],
    )
    return resp.content[0].text


def answer_question(question: str) -> dict:
    """Full pipeline. Returns dict with answer, sql, and raw rows (rows/sql are
    useful for a debug panel in the UI, and can be hidden from end users)."""
    try:
        sql = generate_sql(question)
    except ValueError as e:
        if str(e) == "NO_QUERY":
            return {
                "answer": "I don't have data to answer that yet -- I can currently only "
                          "answer questions about computers, monitors, monitor arms, docks, "
                          "and cable inventory.",
                "sql": None,
                "rows": [],
            }
        return {"answer": f"I couldn't safely build a query for that: {e}", "sql": None, "rows": []}

    try:
        rows = run_query(sql)
    except Exception as e:
        return {"answer": f"That query failed to run: {e}", "sql": sql, "rows": []}

    answer = summarize(question, rows)
    return {"answer": answer, "sql": sql, "rows": rows}
