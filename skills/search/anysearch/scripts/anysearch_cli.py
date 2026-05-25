#!/usr/bin/env python3
"""AnySearch CLI — unified search infrastructure for AI agents"""
import json, os, sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
API_BASE = "https://api.anysearch.com"

def cmd_doc():
    """Print local documentation (no network)"""
    print(f"""AnySearch CLI — Interface Specification
========================================
API: {API_BASE}/v1/search

Commands:
  doc              Show this documentation
  search <query>   Web search
  extract <url>    Extract page content
  help             Alias for doc

Search parameters:
  query           *  Search query (string)
  max_results        Results count, default 10, range 1-100 (int)
  domains            Domain filter, e.g. ["tech","academic"]
  content_types      Content-type filter, e.g. ["web","news"]
  zone               Region: cn or intl
  language           Preferred language, e.g. zh-CN or en
  providers          Explicit provider list
  constraint.freshness  Recency: day, week, month, year
  constraint.from      Start time (RFC3339)
  constraint.to        End time (RFC3339)

Authentication:
  Set ANYSEARCH_API_KEY in .env or env var, or use anonymously
  Anonymous requests are rate-limited per IP

Vertical domains:
  code, tech, academic, news, finance, health, shopping,
  travel, entertainment, music, gaming, home, apparel,
  electronics, sports, education, government, science,
  social, video, images, job, real_estate

Environment:
  ANYSEARCH_API_KEY  API key (optional, for higher rate limits)
""")

def get_api_key():
    key = os.environ.get("ANYSEARCH_API_KEY")
    if key: return key
    env_path = SKILL_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANYSEARCH_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None

def cmd_search(args):
    import urllib.request, urllib.error
    query = " ".join(args) if args else input("Search: ")
    payload = {"query": query, "max_results": 10}
    headers = {"Content-Type": "application/json"}
    key = get_api_key()
    if key: headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        f"{API_BASE}/v1/search",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_extract(args):
    import urllib.request, urllib.error
    url = args[0] if args else input("URL: ")
    payload = {"url": url}
    headers = {"Content-Type": "application/json"}
    key = get_api_key()
    if key: headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        f"{API_BASE}/v1/extract",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        cmd_doc()
    elif sys.argv[1] == "doc":
        cmd_doc()
    elif sys.argv[1] == "search":
        cmd_search(sys.argv[2:])
    elif sys.argv[1] == "extract":
        cmd_extract(sys.argv[2:])
    else:
        print(f"Unknown command: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)
