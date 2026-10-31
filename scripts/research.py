#!/usr/bin/env python3
"""Research a topic before drawing it: free scholarly sources, no API key, standard library only.

  python research.py "ferroptosis"                     # brief: overview, key terms, numbered references with DOIs
  python research.py "PLA hydrolytic degradation" --n 10 --recent 5 --review
  python research.py "silver nanoparticle wound dressing" --json > refs.json

Sources: OpenAlex (papers, citation counts, open-access links), Europe PMC (biomedical abstracts, PubMed ids) and
Wikipedia (a plain-language overview). Only the topic string is sent to these public APIs.
The brief ranks papers by relevance and citations, lists the terms that recur across their abstracts (candidate
elements for the figure), and prints references in a numbered list the spec can cite as [n].
"""
import argparse
import collections
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "scientific-illustration/1.0 (research.py; https://github.com/charaflokman/scientific-illustration)"}
STOP = set("""a an the of and or in on for to with by from at as is are was were be been this that these those we our
their its it into via using use used than then also can may which between within without both such not more most
less based study studies results result effect effects role new show shows shown here during after before over under
through among however two three one high low different increased decreased significantly significant potential
including including review analysis data model models method methods approach approaches paper present presents mechanism
mechanisms disease diseases involved several form forms association associated recent recently various key novel
important main current future type types process processes factor factors level levels many well known cells cell""".split())


def get_json(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  (source skipped: {url.split('/')[2]}: {e})", file=sys.stderr)
        return None


def openalex(q, n, since, review):
    flt = [f"from_publication_date:{since}-01-01"] if since else []
    if review:
        flt.append("type:review")
    url = ("https://api.openalex.org/works?per-page=%d&search=%s%s&select=id,doi,title,publication_year,cited_by_count,"
           "authorships,primary_location,open_access,abstract_inverted_index,type"
           % (min(50, n * 3), urllib.parse.quote(q), "&filter=" + ",".join(flt) if flt else ""))
    d = get_json(url) or {}
    out = []
    for w in d.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        words = sorted(((p, k) for k, ps in inv.items() for p in ps))
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])[:3]]
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        out.append({"title": w.get("title") or "", "year": w.get("publication_year"), "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "cites": w.get("cited_by_count", 0), "authors": authors, "journal": src,
                    "oa": (w.get("open_access") or {}).get("oa_url"), "abstract": " ".join(k for _, k in words),
                    "type": w.get("type"), "from": "OpenAlex"})
    return out


def europepmc(q, n, since, review):
    query = q + (f" AND PUB_YEAR:[{since} TO 3000]" if since else "") + (" AND PUB_TYPE:review" if review else "")
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=core&pageSize=%d&query=%s"
           % (min(25, n * 2), urllib.parse.quote(query)))
    d = get_json(url) or {}
    out = []
    for r in (d.get("resultList") or {}).get("result", []):
        out.append({"title": r.get("title", "").rstrip("."), "year": int(r["pubYear"]) if r.get("pubYear", "").isdigit() else None,
                    "doi": r.get("doi", ""), "cites": r.get("citedByCount", 0), "authors": (r.get("authorString") or "").split(", ")[:3],
                    "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title", ""), "pmid": r.get("pmid"),
                    "oa": None, "abstract": re.sub("<[^>]+>", "", r.get("abstractText", "")), "type": "review" if review else "",
                    "from": "Europe PMC"})
    return out


def wikipedia(q):
    words = q.split()
    page = None
    for k in range(len(words), 0, -1):  # "ferroptosis mechanism" -> "ferroptosis"
        s = get_json("https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&format=json&search="
                     + urllib.parse.quote(" ".join(words[:k])))
        if s and s[1]:
            page = s[1][0]
            break
    if not page:
        return None
    d = get_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(page.replace(" ", "_")))
    return d and {"title": d.get("title"), "extract": d.get("extract", ""), "url": (d.get("content_urls") or {}).get("desktop", {}).get("page")}


def merge(records, q):
    seen, out = {}, []
    terms = [t for t in re.findall(r"\w+", q.lower()) if t not in STOP]
    for r in records:
        key = (r["doi"] or re.sub(r"\W+", "", r["title"].lower())[:80]).lower()
        if not key or key in seen:
            if key in seen and not seen[key]["abstract"] and r["abstract"]:
                seen[key]["abstract"] = r["abstract"]
            continue
        hits = sum(t in (r["title"] + " " + r["abstract"]).lower() for t in terms)
        r["score"] = hits * 3 + min(r["cites"] or 0, 2000) ** .5 / 6 + (1 if r["abstract"] else 0)
        seen[key] = r
        out.append(r)
    return sorted(out, key=lambda r: -r["score"])


def key_terms(recs, q, k=18):
    """Recurring 1-3 word phrases across abstracts: candidate elements for the figure."""
    qt = set(re.findall(r"\w+", q.lower()))
    c = collections.Counter()
    for r in recs:
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", (r["title"] + ". " + r["abstract"]).lower())]
        seen = set()
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                g = words[i:i + n]
                if g[0] in STOP or g[-1] in STOP or all(w in qt for w in g) or len(g[-1]) < 3:
                    continue
                seen.add(" ".join(g))
        c.update(seen)
    # longer phrases are more specific ("lipid peroxidation" beats "lipid"), so weight them up
    ranked = sorted(c.items(), key=lambda kv: -kv[1] * (1 + .7 * (kv[0].count(" "))))
    picked = []
    for term, cnt in ranked[:300]:
        if cnt < 2 or any(term in p or p in term for p, _ in picked):
            continue
        picked.append((term, cnt))
        if len(picked) == k:
            break
    return picked


def cite(i, r):
    au = ", ".join(r["authors"][:3]) + (" et al." if len(r["authors"]) >= 3 else "")
    ids = f"doi:{r['doi']}" if r["doi"] else (f"PMID:{r['pmid']}" if r.get("pmid") else "")
    oa = f"  open access: {r['oa']}" if r.get("oa") else ""
    return f"[{i}] {au} ({r['year']}). {r['title']}. {r['journal']}. {ids}. Cited {r['cites']}×.{oa}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic")
    ap.add_argument("--n", type=int, default=8, help="references to keep")
    ap.add_argument("--recent", type=int, help="only the last N years")
    ap.add_argument("--review", action="store_true", help="prefer review articles")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    since = datetime.date.today().year - a.recent if a.recent else None
    recs = merge(openalex(a.topic, a.n, since, a.review) + europepmc(a.topic, a.n, since, a.review), a.topic)[:a.n]
    wiki = wikipedia(a.topic)
    if a.json:
        print(json.dumps({"topic": a.topic, "overview": wiki, "references": recs}, ensure_ascii=False, indent=1))
        return
    print(f"# Research brief: {a.topic}\n")
    if wiki and wiki["extract"]:
        print(f"## Overview (Wikipedia: {wiki['title']})\n{wiki['extract']}\n{wiki['url']}\n")
    if not recs:
        print("No papers found. Try a broader or more standard term (e.g. the English scientific name).")
        return
    print("## Recurring terms across the top papers (candidate figure elements)")
    print(", ".join(f"{t} ({c})" for t, c in key_terms(recs, a.topic)) + "\n")
    print("## What the top papers say (first sentences of each abstract)")
    for i, r in enumerate(recs, 1):
        s = re.split(r"(?<=[.!?])\s+", r["abstract"].strip())
        if s and s[0]:
            print(f"[{i}] " + " ".join(s[:2])[:420])
    print("\n## References (cite as [n] in the spec)")
    for i, r in enumerate(recs, 1):
        print(cite(i, r))
    print("\nUse only what these sources support; mark gaps as [? ...]. Check key claims in the full text before publishing.")


if __name__ == "__main__":
    main()
