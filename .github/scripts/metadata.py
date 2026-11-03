#!/usr/bin/env python3
# Uso: metadata.py <cartella-documento> <output.json>
#
# Scrive il metadata.json pubblicato sul sito: quello della cartella, completato con
#   createdAt  primo merge su main che ha introdotto il documento
#   approved   PR dell'ultima modifica al documento: approvazioni (o chi ha fatto il merge, se nessuna)
# I campi gia' presenti nel metadata.json sorgente (es. version, important) hanno la precedenza.
# Le modifiche al solo metadata.json e gli spostamenti di cartella non contano come modifiche.
# Serve la history completa (fetch-depth: 0) e `gh` autenticato (GH_TOKEN) con pull-requests: read.
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def utc(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def doc_file(path, prefix):
    """Path relative to the document folder, or None if outside it (or metadata.json)."""
    if not path.startswith(prefix + "/"):
        return None
    rel = path[len(prefix) + 1 :]
    return None if rel == "metadata.json" else rel


def history(folder):
    """(content-change commits newest first, commit that introduced the document), on first-parent HEAD."""
    changes, created = [], None
    path, rev = folder, "HEAD"
    while True:
        commits = git("log", "--first-parent", "--format=%H", rev, "--", path).split()
        moved_from = None
        for c in commits:
            parents = git("rev-list", "--parents", "-n1", c).split()[1:]
            if not parents:  # root commit
                if any(doc_file(f, path) for f in git("ls-tree", "-r", "--name-only", c, "--", path).splitlines()):
                    changes.append(c)
                    created = c
                break
            out = git("diff", "--find-renames", "--name-status", "-z", parents[0], c).split("\0")[:-1]
            changed, origins = False, Counter()
            i = 0
            while i < len(out):
                status = out[i]
                if status[0] in "RC":
                    src, dst = out[i + 1], out[i + 2]
                    i += 3
                else:
                    src = dst = out[i + 1]
                    i += 2
                rel = doc_file(dst, path)
                if status[0] in "RC" and rel and src.endswith("/" + rel):
                    origins[src[: -len(rel) - 1]] += 1
                if rel and status != "R100":
                    changed = True
            existed = any(doc_file(f, path) for f in git("ls-tree", "-r", "--name-only", parents[0], "--", path).splitlines())
            if changed:
                changes.append(c)
            if not existed:
                if origins:
                    moved_from = (origins.most_common(1)[0][0], parents[0])
                elif changed:
                    created = c
                break
        if not moved_from:
            return changes, created
        path, rev = moved_from


pulls_cache = {}


def gh(endpoint, *flags):
    return json.loads(subprocess.run(["gh", "api", *flags, endpoint], check=True, capture_output=True, text=True).stdout)


def pull_request(commit):
    """The merged PR that brought `commit` into main, or None."""
    try:
        pulls = gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/commits/{commit}/pulls")
    except subprocess.CalledProcessError:  # es. merge commit sintetico delle build di PR
        return None
    merged = [p for p in pulls if p.get("merged_at")]
    return next((p for p in merged if p.get("merge_commit_sha") == commit), merged[0] if merged else None)


def approval(commit):
    if commit in pulls_cache:
        return pulls_cache[commit]
    pr, result = pull_request(commit), None
    if pr:
        reviews = gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{pr['number']}/reviews", "--paginate", "--slurp")
        # stato finale di ogni revisore (i commenti semplici non cambiano il verdetto)
        latest = {}
        for r in (r for page in reviews for r in page):
            if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED") and r.get("submitted_at"):
                latest[r["user"]["login"]] = r
        approvals = sorted((r for r in latest.values() if r["state"] == "APPROVED"), key=lambda r: r["submitted_at"])
        if approvals:
            by, at = [r["user"]["login"] for r in approvals], approvals[-1]["submitted_at"]
        else:
            # merged_by non c'e' nella lista restituita da commits/{sha}/pulls
            pr = gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{pr['number']}")
            by, at = [pr["merged_by"]["login"]] if pr.get("merged_by") else [], pr["merged_at"]
        result = {"approvedAt": utc(at), "by": by, "prLink": pr["html_url"], "prNumber": pr["number"]}
    pulls_cache[commit] = result
    return result


def main(folder, output):
    if not os.environ.get("GITHUB_REPOSITORY"):
        sys.exit("GITHUB_REPOSITORY non impostata (owner/nome del repo, per le PR)")
    folder = os.path.relpath(folder)
    with open(os.path.join(folder, "metadata.json"), encoding="utf-8") as f:
        source = json.load(f)

    changes, created = history(folder)
    derived = {}
    if created:
        derived["createdAt"] = utc(git("log", "-1", "--format=%cI", created).strip())
    approved = approval(changes[0]) if changes else None
    if approved:
        derived["approved"] = approved

    metadata = {**source, **{k: v for k, v in derived.items() if k not in source}}
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent="\t", ensure_ascii=False)
        f.write("\n")
    print(f"{folder}: derivati {', '.join(k for k in derived if k not in source) or 'nessuno'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: metadata.py <cartella-documento> <output.json>")
    main(*sys.argv[1:])
