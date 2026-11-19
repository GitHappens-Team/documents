#!/usr/bin/env python3
"""Marks glossary terms in the documents, right before the build.

Usage: glossary.py [--scope section|document|all] <glossary-dir> <doc-dir>...

Edits the .tex files in place: run it on a copy (build.sh) or on the CI
checkout, never on the committed sources.

- reads the entries \\glossentry{Title}{alias, ...} from the glossary
- in the glossary, adds the slug to each entry (\\glossentry[slug]{...}) to create the anchors
- in the documents, replaces occurrences with \\term[slug]{text}, only the first one
  per section (--scope), from the first \\section on (skips the header and the
  change log)
- adds the slug to hand-written \\term{X} when X is an entry or an alias
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

# commands whose arguments are left untouched
SKIP_ARGS = {
    "section", "subsection", "subsubsection", "paragraph", "caption",
    "href", "url", "texttt", "label", "ref", "hyperlink", "hypertarget",
    "input", "include", "includegraphics", "begin", "end", "cite",
    "term", "noterm", "glossentry", "newcommand", "renewcommand", "usepackage",
    "documentclass", "hypersetup", "setcounter", "setlength", "definecolor",
    "tipodoc", "datadoc", "versione", "modalita", "orario", "redattori",
    "verificatori", "amministratore", "responsabile", "destinatari", "partecipanti",
}
SKIP_ENVS = {"verbatim", "lstlisting", "minted", "comment"}
SECTION = {"section"}
ENTRY_RE = re.compile(r"\\glossentry(?:\[[^\]]*\])?\{([^}]*)\}\{([^}]*)\}")


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def read_arg(text, i, open_ch="{", close_ch="}"):
    """Returns the end of the argument starting at text[i] (== open_ch)."""
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def skip_args(text, i):
    """Skips the *, [optional] and {arguments} following a command."""
    while i < len(text):
        j = i
        while j < len(text) and text[j] in " \t":
            j += 1
        if j < len(text) and text[j] == "*":
            i = j + 1
        elif j < len(text) and text[j] == "[":
            i = read_arg(text, j, "[", "]")
        elif j < len(text) and text[j] == "{":
            i = read_arg(text, j)
        else:
            return i
    return i


def parse_glossary(path):
    entries = []
    for m in ENTRY_RE.finditer(path.read_text()):
        title = m.group(1).strip()
        aliases = [a.strip() for a in m.group(2).split(",") if a.strip()]
        entries.append((slugify(title), title, aliases))
    return entries


def build_matcher(entries):
    lookup = {}
    patterns = []
    for slug, title, aliases in entries:
        for form in [title] + aliases:
            lookup[form.lower()] = slug
            body = r"[\s~]+".join(re.escape(w) for w in form.split())
            # acronyms and names like GitHub, LaTeX: exact case
            exact = " " not in form and any(c.isupper() for c in form[1:])
            patterns.append((len(form), body if exact else f"(?i:{body})", form))
    patterns.sort(key=lambda p: -p[0])
    alt = "|".join(f"(?P<p{n}>{p[1]})" for n, p in enumerate(patterns))
    regex = re.compile(rf"(?<![\w\\/])(?:{alt})(?![\w/])")
    forms = [p[2] for p in patterns]
    return regex, forms, lookup


class Tagger:
    def __init__(self, regex, forms, lookup, scope, auto):
        self.regex, self.forms, self.lookup = regex, forms, lookup
        self.scope, self.auto = scope, auto
        self.seen = set()
        self.started = False
        self.added = 0
        self.unknown = []

    def slug_of(self, m):
        form = self.forms[int(m.lastgroup[1:])]
        return self.lookup[form.lower()]

    def tag_plain(self, chunk):
        if not (self.auto and self.started):
            return chunk

        def repl(m):
            slug = self.slug_of(m)
            if self.scope != "all" and slug in self.seen:
                return m.group(0)
            self.seen.add(slug)
            self.added += 1
            return f"\\term[{slug}]{{{m.group(0)}}}"

        return self.regex.sub(repl, chunk)

    def process(self, text):
        out = []
        i = plain = 0
        while i < len(text):
            c = text[i]
            if c == "%":
                end = text.find("\n", i)
                end = len(text) if end < 0 else end
                out.append(self.tag_plain(text[plain:i]))
                out.append(text[i:end])
                i = plain = end
                continue
            if c != "\\":
                i += 1
                continue
            m = re.match(r"\\([A-Za-z]+)|\\.", text[i:])
            name = m.group(1)
            end = i + m.end()
            if name is None or name not in SKIP_ARGS:
                if name is None:  # \%, \\, \& ...
                    i = end
                    continue
                out.append(self.tag_plain(text[plain:i]))
                out.append(text[i:end])
                i = plain = end
                continue
            out.append(self.tag_plain(text[plain:i]))
            if name == "begin":
                env = re.match(r"\{(\w+\*?)\}", text[end:])
                if env and env.group(1) in SKIP_ENVS:
                    close = text.find(f"\\end{{{env.group(1)}}}", end)
                    end = len(text) if close < 0 else close
                else:
                    end = skip_args(text, end)
            elif name == "term":
                end = skip_args(text, end)
                out.append(self.fix_term(text[i:end]))
                i = plain = end
                continue
            else:
                end = skip_args(text, end)
            if name in SECTION:
                self.started = True
                if self.scope == "section":
                    self.seen = set()
            out.append(text[i:end])
            i = plain = end
        out.append(self.tag_plain(text[plain:]))
        return "".join(out)

    def fix_term(self, cmd):
        """Hand-written \\term{X}: adds the slug if X is in the glossary."""
        m = re.fullmatch(r"\\term\s*\{(.*)\}", cmd, re.S)
        if not m:
            return cmd  # already has a slug
        slug = self.lookup.get(" ".join(m.group(1).split()).lower())
        if slug is None:
            self.unknown.append(m.group(1))
            return cmd
        self.seen.add(slug)
        return f"\\term[{slug}]{{{m.group(1)}}}"


def input_order(doc):
    """The document's .tex files in \\input order, starting from main.tex."""
    files = []

    def visit(path):
        if not path.exists() or path in files:
            return
        files.append(path)
        text = re.sub(r"(?<!\\)%.*", "", path.read_text())
        for m in re.finditer(r"\\(?:input|include)\{([^}]*)\}", text):
            name = m.group(1).strip()
            visit(doc / (name if name.endswith(".tex") else name + ".tex"))

    visit(doc / "main.tex")
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", choices=["section", "document", "all"], default="section",
                    help="which occurrences to mark: first per section (default), per document, all")
    ap.add_argument("glossary", type=Path)
    ap.add_argument("docs", type=Path, nargs="+")
    args = ap.parse_args()

    gdir = args.glossary.resolve()
    entries = [e for f in input_order(gdir) for e in parse_glossary(f)]
    if not entries:
        sys.exit(f"no \\glossentry found in {gdir}")
    regex, forms, lookup = build_matcher(entries)

    for doc in args.docs:
        doc = doc.resolve()
        is_glossary = doc == gdir
        tagger = Tagger(regex, forms, lookup, args.scope, auto=not is_glossary)
        for f in input_order(doc):
            text = f.read_text()
            if is_glossary:
                text = re.sub(r"\\glossentry\{([^}]*)\}",
                              lambda m: f"\\glossentry[{slugify(m.group(1))}]{{{m.group(1)}}}", text)
            new = tagger.process(text)
            if new != text:
                f.write_text(new)
        print(f"{doc.name}: {tagger.added} terms marked")
        for u in sorted(set(tagger.unknown)):
            print(f"::warning::{doc.name}: \\term{{{u}}} is not a glossary entry")


if __name__ == "__main__":
    main()
