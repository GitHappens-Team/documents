#!/usr/bin/env python3
"""Suggests terms to add to the glossary.

Usage:
  glossary_suggestions.py pr --base <sha> --head <sha>
      only the lines added by the PR. In CI (PR_NUMBER set) it posts a comment
      on the PR and minimizes the previous ones, locally it prints the comment.
  glossary_suggestions.py full
      every document in the repo, writes the job summary (or to stdout).

Candidates come from two sources:
- fixed rules: acronyms and names like PostgreSQL that aren't entries or aliases,
  \\term{X} without a matching entry
- model (Gemini, GEMINI_API_KEY / GEMINI_MODEL): technical or English terms a
  reader might not know, or variants of existing entries
Anything that is already an entry or alias, is in gl-ignore.txt or doesn't appear
literally in the text is dropped (the model can't make terms up).

The PR comment and the summary are in Italian, like the documents.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glossary import build_matcher, input_order, parse_glossary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY_DIR = ROOT / "RTB/documenti_interni/glossario"
IGNORE = GLOSSARY_DIR / "gl-ignore.txt"
MARKER = "<!-- glossary-suggestions -->"
DATA_RE = re.compile(r"<!-- glossary-data: (.*?) -->", re.S)
MODEL = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
BATCH_CHARS = 30000

# lines holding only document metadata, not text
HEADER_RE = re.compile(
    r"^\s*\\(documentclass|usepackage|input|include|tipodoc|datadoc|versione|modalita|"
    r"orario|redattori|verificatori|amministratore|responsabile|destinatari|partecipanti|"
    r"newcommand|renewcommand|setcounter|setlength|hline|glossentry)\b")
# acronyms and names with inner capitals: API, PoC, PostgreSQL
# (not VI\_2026, not \LaTeX, not Jira keys like SWE-05)
ACRONYM_RE = re.compile(r"(?<![\w\\])[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*(?![\w\\]|-\d)")
ROMAN_RE = re.compile(r"[IVXLC]+")
# text not worth checking: code, URLs, all-caps runs (TOTALE ORE, KEY-NUMBER-DESC)
NOISE_RE = re.compile(r"\\(?:texttt|url|href)\{[^}]*\}|[A-Z]{2,}(?:[ -][A-Z]{2,})+")
TERM_RE = re.compile(r"\\term\{([^}]*)\}")

SYSTEM = """You review the documentation of a university software engineering \
project, written in Italian with LaTeX. The team keeps a glossary: readers \
(professors and the client company) must find there every technical term, \
acronym or English industry term used in the documents.

You get some text blocks and the list of entries already in the glossary. For \
each block, list the terms that should be added to the glossary.

Rules:
- report the term exactly as written in the text, without LaTeX commands
- ignore common Italian words, people's names, dates, document codes, URLs,
  LaTeX command names and terms already in the glossary
- if the term is a variant of an existing entry (plural, acronym, different
  case) use kind "alias" and put the entry title in alias_of
- reason: at most 8 words, in Italian
- be selective: only terms a reader might really not know"""

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "block": {"type": "STRING"},
            "term": {"type": "STRING"},
            "kind": {"type": "STRING", "enum": ["acronym", "technical", "english", "alias"]},
            "reason": {"type": "STRING"},
            "alias_of": {"type": "STRING"},
        },
        "required": ["block", "term", "kind", "reason"],
    },
}


class ModelError(Exception):
    pass


# --- text ----------------------------------------------------------------

def clean(line):
    line = re.sub(r"(?<!\\)%.*", "", line)
    return "" if HEADER_RE.match(line) else line.rstrip()


def block(file, start, lines):
    text = "\n".join(lines)
    return {"file": file, "start": start, "lines": lines,
            "hash": hashlib.sha1(text.encode()).hexdigest()[:16],
            "glossary": file.startswith(str(GLOSSARY_DIR.relative_to(ROOT)) + "/")}


def blocks_from_file(path):
    """A file's paragraphs (split on blank lines) with their line numbers."""
    rel = str(path.relative_to(ROOT))
    out, cur, start = [], [], 0
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        line = clean(raw)
        if line.strip():
            if not cur:
                start = n
            cur.append(line)
        elif cur:
            out.append(block(rel, start, cur))
            cur = []
    if cur:
        out.append(block(rel, start, cur))
    return out


def blocks_from_diff(base, head):
    """Runs of consecutive added lines in the PR's .tex files."""
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", f"{base}...{head}", "--", "*.tex"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    out, file, cur, start, n = [], None, [], 0, 0

    def flush():
        nonlocal cur
        if file and any(line.strip() for line in cur):
            out.append(block(file, start, cur))
        cur = []

    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            flush()
            file = None if raw.endswith("/dev/null") else raw[6:]
        elif raw.startswith("@@"):
            flush()
            start = n = int(re.search(r"\+(\d+)", raw).group(1))
        elif raw.startswith("+") and file:
            cur.append(clean(raw[1:]))
            n += 1
    flush()
    return out


def occurrences(blk, term, exact=False):
    pat = re.compile(rf"(?<![\w\\]){re.escape(term)}(?!\w)", 0 if exact else re.I)
    return [blk["start"] + i for i, line in enumerate(blk["lines"]) if pat.search(line)]


# --- candidates ----------------------------------------------------------

def rule_candidates(blk, glossary_re):
    text = "\n".join(blk["lines"])
    out = [{"term": t, "kind": "undefined_term", "reason": "usato in `\\term{}` ma senza voce"}
           for t in TERM_RE.findall(text)]
    # \term{} handled above, existing entries (e.g. VS in VS Code), noise
    text = glossary_re.sub(" ", NOISE_RE.sub(" ", TERM_RE.sub(" ", text)))
    out += [{"term": t, "kind": "acronym", "reason": "acronimo non definito"}
            for t in ACRONYM_RE.findall(text) if not ROMAN_RE.fullmatch(t)]
    return out


def gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ModelError("GEMINI_API_KEY missing")
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": SCHEMA},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    req = urllib.request.Request(url, body, {"Content-Type": "application/json",
                                             "x-goog-api-key": key})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            parts = data["candidates"][0]["content"]["parts"]
            return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(15 * (attempt + 1))
                continue
            raise ModelError(f"{MODEL}: HTTP {e.code}") from e
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as e:
            raise ModelError(f"{MODEL}: {e}") from e


def model_candidates(blocks, entries):
    """{hash: [candidates]} for the given blocks, in batches of BATCH_CHARS."""
    glossary = "\n".join(f"- {t}" + (f" ({', '.join(a)})" if a else "") for _, t, a in entries)
    batches, batch, size = [], [], 0
    for b in blocks:
        n = sum(len(line) for line in b["lines"])
        if batch and size + n > BATCH_CHARS:
            batches.append(batch)
            batch, size = [], 0
        batch.append(b)
        size += n
    if batch:
        batches.append(batch)
    result = {}
    for batch in batches:
        text = "\n\n".join(f"### block {b['hash']} ({b['file']})\n" + "\n".join(b["lines"])
                           for b in batch)
        answer = gemini(f"Glossary entries:\n{glossary}\n\nText to check:\n\n{text}")
        for b in batch:
            result[b["hash"]] = []
        for c in answer:
            if c.get("block") in result:
                result[c["block"]].append({k: v for k, v in c.items() if k != "block"})
    return result


def collect(blocks, by_hash, entries):
    """Merges rules and model, filters, groups by term with its occurrences."""
    glossary_re, _, lookup = build_matcher(entries)
    titles = {t.lower(): t for _, t, _ in entries}
    ignore = set()
    if IGNORE.exists():
        ignore = {line.strip().lower() for line in IGNORE.read_text().splitlines()
                  if line.strip() and not line.startswith("#")}
    rank = {"undefined_term": 0, "alias": 1}
    found = {}
    for b in blocks:
        for c in rule_candidates(b, glossary_re) + by_hash.get(b["hash"], []):
            term = " ".join(c["term"].split())
            key = term.lower()
            if not term or key in lookup or key in ignore:
                continue
            if c["kind"] == "alias":
                alias_of = titles.get(c.get("alias_of", "").strip().lower())
                c = {**c, "alias_of": alias_of} if alias_of else {**c, "kind": "technical"}
            if c["kind"] == "undefined_term":
                lines = [b["start"] + i for i, line in enumerate(b["lines"])
                         if f"\\term{{{term}}}" in line]
            else:
                lines = occurrences(b, term, exact=c["kind"] == "acronym")
            if not lines:
                continue  # not in the text: dropped
            item = found.setdefault(key, {**c, "term": term, "occ": []})
            if rank.get(c["kind"], 9) < rank.get(item["kind"], 9):
                item.update({k: v for k, v in c.items() if k != "term"})
            item["occ"] += [(b["file"], n) for n in lines if (b["file"], n) not in item["occ"]]
    return sorted(found.values(), key=lambda i: (i["occ"][0], i["term"].lower()))


def reason(item):
    if item["kind"] == "alias":
        return f"aggiungere come alias di *{item['alias_of']}*"
    return item["reason"]


def run_model(blocks, entries, cache):
    """Model candidates, reusing the cache for blocks already checked."""
    hashes = {b["hash"] for b in blocks}
    todo = [b for b in blocks if not b["glossary"] and b["hash"] not in cache]
    by_hash = {h: c for h, c in cache.items() if h in hashes}
    note = None
    if todo:
        try:
            by_hash.update(model_candidates(todo, entries))
        except ModelError as e:
            note = f"suggerimenti del modello non disponibili ({e}), solo controlli fissi"
    return by_hash, note


# --- GitHub --------------------------------------------------------------

def github(method, path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, json.dumps(body).encode() if body else None,
        {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
         "Accept": "application/vnd.github+json"}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def previous_comments(repo, pr):
    out, page = [], 1
    while True:
        batch = github("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}")
        out += [c for c in batch if c["user"]["login"] == "github-actions[bot]"
                and MARKER in c["body"]]
        if len(batch) < 100:
            return out
        page += 1


def minimize(node_id):
    github("POST", "/graphql", {
        "query": "mutation($id: ID!) { minimizeComment(input: {subjectId: $id, "
                 "classifier: OUTDATED}) { clientMutationId } }",
        "variables": {"id": node_id}})


# --- modes ---------------------------------------------------------------

def cmd_pr(args, entries):
    repo, pr = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("PR_NUMBER")
    old = previous_comments(repo, pr) if pr else []
    prev = {}
    if old:
        m = DATA_RE.search(old[-1]["body"])
        prev = json.loads(m.group(1)) if m else {}

    blocks = blocks_from_diff(args.base, args.head)
    by_hash, note = run_model(blocks, entries, prev.get("model", {}))
    items = collect(blocks, by_hash, entries)

    if not items and old and prev.get("count") == 0 and not note:
        print("no missing terms, same as the previous comment: not commenting")
        return

    sha = args.head[:7]
    url = f"https://github.com/{repo}/blob/{args.head}" if repo else None
    lines = [MARKER]
    if items:
        lines.append(f"**Glossario** · `{sha}` · {len(items)} "
                     f"termin{'e' if len(items) == 1 else 'i'} da valutare")
        for i in items:
            (f, n), more = i["occ"][0], len(i["occ"]) - 1
            loc = f"[`{f}:{n}`]({url}/{f}#L{n})" if url else f"`{f}:{n}`"
            lines.append(f"- **{i['term']}**: {loc}" + (f" (+{more})" if more else "")
                         + f": {reason(i)}")
    else:
        lines.append(f"**Glossario** · `{sha}` · nessun termine mancante")
    if note:
        lines.append(f"\n_{note}_")
    lines.append(f"\n<sub>Per ignorare un termine aggiungilo a `{IGNORE.relative_to(ROOT)}`.</sub>")
    data = {"count": len(items), "model": by_hash}
    lines.append("<!-- glossary-data: " + json.dumps(data).replace(">", "\\u003e") + " -->")
    body = "\n".join(lines)

    if not pr:
        print(body)
        return
    github("POST", f"/repos/{repo}/issues/{pr}/comments", {"body": body})
    for c in old:
        try:
            minimize(c["node_id"])
        except urllib.error.HTTPError as e:
            print(f"::warning::comment {c['id']} not minimized: HTTP {e.code}")


def cmd_full(args, entries):
    docs = sorted(p.parent for p in ROOT.glob("**/main.tex") if ".latex" not in p.parts)
    blocks = [b for d in docs for f in input_order(d) for b in blocks_from_file(f)]
    by_hash, note = run_model(blocks, entries, {})
    items = collect(blocks, by_hash, entries)

    # entries never used outside the glossary and aliases claimed twice: rules only
    regex, forms, lookup = build_matcher(entries)
    used = set()
    for b in blocks:
        if not b["glossary"]:
            for m in regex.finditer("\n".join(b["lines"])):
                used.add(lookup[forms[int(m.lastgroup[1:])].lower()])
    unused = [t for s, t, _ in entries if s not in used]
    owners = {}
    for _, t, aliases in entries:
        for form in [t] + aliases:
            owners.setdefault(form.lower(), []).append(t)
    conflicts = {f: ts for f, ts in owners.items() if len(set(ts)) > 1}

    def doc_of(file):
        return next(str(d.relative_to(ROOT)) for d in docs if (ROOT / file).is_relative_to(d))

    missing = [i for i in items if i["kind"] != "undefined_term"]
    undefined = [i for i in items if i["kind"] == "undefined_term"]
    out = ["# Glossario: controllo completo", "",
           f"Modello: `{MODEL}`. {len(missing)} termini mancanti, {len(undefined)} `\\term{{}}` "
           f"senza voce, {len(unused)} voci mai usate, {len(conflicts)} alias in conflitto."]
    if note:
        out += ["", f"_{note}_"]
    if missing:
        out += ["", "## Termini mancanti"]
        by_doc = {}
        for i in missing:
            by_doc.setdefault(doc_of(i["occ"][0][0]), []).append(i)
        for d, its in sorted(by_doc.items()):
            out += ["", f"### {d}"]
            for i in its:
                (f, n), more = i["occ"][0], len(i["occ"]) - 1
                f = str(Path(f).relative_to(d))
                out.append(f"- **{i['term']}**: `{f}:{n}`" + (f" (+{more})" if more else "")
                           + f": {reason(i)}")
    if undefined:
        out += ["", "## `\\term{}` senza voce"]
        out += [f"- **{i['term']}**: " + ", ".join(f"`{f}:{n}`" for f, n in i["occ"])
                for i in undefined]
    if unused:
        out += ["", "## Voci mai usate nei documenti", "", ", ".join(unused)]
    if conflicts:
        out += ["", "## Alias in conflitto"]
        out += [f"- **{f}**: " + ", ".join(sorted(set(ts))) for f, ts in conflicts.items()]
    out += ["", f"Per ignorare un termine aggiungilo a `{IGNORE.relative_to(ROOT)}`."]

    text = "\n".join(out) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(text)
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("pr", help="check the lines added by a PR")
    pr.add_argument("--base", required=True)
    pr.add_argument("--head", required=True)
    sub.add_parser("full", help="check every document")
    args = ap.parse_args()

    entries = [e for f in input_order(GLOSSARY_DIR) for e in parse_glossary(f)]
    if not entries:
        sys.exit("no \\glossentry found in the glossary")
    {"pr": cmd_pr, "full": cmd_full}[args.cmd](args, entries)


if __name__ == "__main__":
    main()
