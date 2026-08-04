"""
Fetches ground truth for each benchmark resource from an official public API
-- independent of CroW's own extraction path, so comparing against it is a
real check rather than circular. Saves one JSON file per resource under
ground_truth/. Rerun any time to refresh; every value here is retrieved live
from the cited public API, not hand-typed.
"""
import json, os, sys, time
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))
from resources import RESOURCES

OUT_DIR = os.path.join(os.path.dirname(__file__), "ground_truth")
os.makedirs(OUT_DIR, exist_ok=True)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CroW-benchmark/1.0 (mailto:kallolnaha@gmail.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def ground_truth_pubmed(term, sort, retmax):
    import urllib.parse
    esearch = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={urllib.parse.quote(term)}&retmax={retmax}"
        f"&sort={'most+recent' if sort == 'date' else 'relevance'}&retmode=json"
    )
    ids = json.loads(_get(esearch))["esearchresult"]["idlist"]
    time.sleep(0.4)
    esummary = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&id={','.join(ids)}&retmode=json"
    )
    data = json.loads(_get(esummary))["result"]
    records = []
    for pmid in ids:
        rec = data.get(pmid)
        if not rec:
            continue
        authors = ", ".join(a["name"] for a in rec.get("authors", []))
        records.append({
            "PMID": pmid,
            "Title": rec.get("title", "").rstrip("."),
            "Authors": authors,
            "Journal": rec.get("fulljournalname", ""),
        })
    return records


def ground_truth_clinicaltrials(term, page_size):
    import urllib.parse
    url = (
        "https://clinicaltrials.gov/api/v2/studies"
        f"?query.term={urllib.parse.quote(term)}&pageSize={page_size}"
        "&sort=%40relevance&fields=NCTId,BriefTitle,OverallStatus"
    )
    data = json.loads(_get(url))
    records = []
    for s in data.get("studies", []):
        ps = s.get("protocolSection", {})
        idm = ps.get("identificationModule", {})
        stm = ps.get("statusModule", {})
        records.append({
            "NCT_ID": idm.get("nctId", ""),
            "Title": idm.get("briefTitle", ""),
            "Status": stm.get("overallStatus", ""),
        })
    return records


def ground_truth_ncbi_gene(term, retmax):
    import urllib.parse
    esearch = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gene&term={urllib.parse.quote(term)}&retmax={retmax}&sort=relevance&retmode=json"
    )
    ids = json.loads(_get(esearch))["esearchresult"]["idlist"]
    time.sleep(0.4)
    esummary = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=gene&id={','.join(ids)}&retmode=json"
    )
    data = json.loads(_get(esummary))["result"]
    records = []
    for gid in ids:
        rec = data.get(gid)
        if not rec:
            continue
        records.append({
            "Symbol": rec.get("name", ""),
            "GeneID": f"ID: {gid}",
            "Description": rec.get("description", ""),
        })
    return records


def ground_truth_uniprot(query, size):
    import urllib.parse
    url = (
        "https://rest.uniprot.org/uniprotkb/search"
        f"?query={urllib.parse.quote(query)}&format=json&size={size}"
        "&fields=accession,id,gene_names"
    )
    data = json.loads(_get(url))
    records = []
    for r in data.get("results", []):
        genes = r.get("genes", [])
        gene_name = genes[0].get("geneName", {}).get("value", "") if genes else ""
        records.append({
            "Accession": r.get("primaryAccession", ""),
            "EntryName": r.get("uniProtkbId", ""),
            "GeneName": gene_name,
        })
    return records


METHODS = {
    "pubmed_eutils": lambda gt: ground_truth_pubmed(gt["term"], gt["sort"], gt["retmax"]),
    "clinicaltrials_api": lambda gt: ground_truth_clinicaltrials(gt["term"], gt["pageSize"]),
    "uniprot_api": lambda gt: ground_truth_uniprot(gt["query"], gt["size"]),
    "ncbi_gene_eutils": lambda gt: ground_truth_ncbi_gene(gt["term"], gt["retmax"]),
}


def main():
    for res in RESOURCES:
        method = res["ground_truth"]["method"]
        fn = METHODS.get(method)
        if not fn:
            print(f"SKIP {res['id']}: no ground-truth method implemented for {method!r}")
            continue
        try:
            records = fn(res["ground_truth"])
        except Exception as e:
            print(f"FAIL {res['id']}: {e}")
            continue
        out_path = os.path.join(OUT_DIR, f"{res['id']}.json")
        with open(out_path, "w") as f:
            json.dump({"resource_id": res["id"], "method": method, "records": records}, f, indent=2)
        print(f"OK {res['id']}: {len(records)} ground-truth records -> {out_path}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
