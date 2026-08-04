"""
Benchmark resource definitions.

Every row/column XPath used below was hand-verified against the real,
live DOM of one representative page per site (see inspect_dom.py and the
README's investigation notes) before being templated here. Templates are
reused across different search queries on the *same* site because the page
structure is per-site, not per-query -- this is the same positional/class
style a human CroW user produces via the two-click tool plus optional
manual class-based refinement through the Text-Based Edit Modal (both real,
documented CroW features -- see final.tex Sec. 5.1, 7.6).

category values match the paper's five life-science categories:
  genomic | disease | protein | clinical | biomedical_search
"""

import re


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def pubmed(term, sort="date", retmax=10):
    import urllib.parse
    return {
        "id": f"pubmed_{_slug(term)}",
        "name": f"PubMed — {term}",
        "category": "biomedical_search",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote_plus(term)}&sort={sort}",
        "mode": "A",
        "row_xpath": "//article[contains(@class,'full-docsum')]",
        "columns": [
            {"name": "Title", "xpath": ".//a[@class='docsum-title']"},
            {"name": "Authors", "xpath": ".//span[contains(@class,'docsum-authors')]"},
            {"name": "Journal", "xpath": ".//span[contains(@class,'docsum-journal-citation')]"},
            {"name": "PMID", "xpath": ".//span[@class='docsum-pmid']"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "pubmed_eutils", "term": term, "sort": sort, "retmax": retmax},
        "key_field": "PMID",
    }


def clinicaltrials(term, page_size=10):
    import urllib.parse
    return {
        "id": f"clinicaltrials_{_slug(term)}",
        "name": f"ClinicalTrials.gov — {term}",
        "category": "clinical",
        "url": f"https://clinicaltrials.gov/search?term={urllib.parse.quote_plus(term)}&viewType=Table",
        "mode": "A",
        "row_xpath": "//table/tbody/tr",
        "columns": [
            {"name": "Title", "xpath": ".//td[2]"},
            {"name": "NCT_ID", "xpath": ".//td[3]"},
            {"name": "Status", "xpath": ".//td[4]"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "clinicaltrials_api", "term": term, "pageSize": page_size},
        "key_field": "NCT_ID",
    }


def uniprot(query, size=25):
    import urllib.parse
    return {
        "id": f"uniprot_{_slug(query)}",
        "name": f"UniProt — {query} (reviewed)",
        "category": "protein",
        "url": f"https://www.uniprot.org/uniprotkb?query={urllib.parse.quote_plus(query)}&facets=reviewed%3Atrue",
        "mode": "A",
        "row_xpath": "//table/tbody/tr",
        "columns": [
            {"name": "Accession", "xpath": ".//td[2]"},
            {"name": "EntryName", "xpath": ".//td[4]"},
            {"name": "GeneName", "xpath": ".//td[6]"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "uniprot_api", "query": f"{query} AND reviewed:true", "size": size},
        "key_field": "Accession",
    }


def ncbi_gene(gene, retmax=20):
    import urllib.parse
    term = f"{gene} AND human[orgn]"
    return {
        "id": f"ncbi_gene_{_slug(gene)}",
        "name": f"NCBI Gene — {gene} (human)",
        "category": "genomic",
        "url": f"https://www.ncbi.nlm.nih.gov/gene/?term={urllib.parse.quote_plus(term)}",
        "mode": "A",
        "row_xpath": "//tr[contains(@class,'rprt')]",
        "columns": [
            {"name": "Symbol", "xpath": ".//td[1]//a"},
            {"name": "GeneID", "xpath": ".//td[1]//span[@class='gene-id']"},
            {"name": "Description", "xpath": ".//td[2]"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "ncbi_gene_eutils", "term": term, "retmax": retmax},
        "key_field": "GeneID",
    }


RESOURCES = [
    # biomedical_search (PubMed)
    pubmed("TP53 tumor suppressor"),
    pubmed("BRCA1 breast cancer"),
    pubmed("CRISPR gene editing"),
    pubmed("Alzheimer amyloid beta"),
    pubmed("COVID-19 vaccine efficacy"),
    pubmed("insulin resistance type 2 diabetes"),
    pubmed("Parkinson disease dopamine"),
    pubmed("obesity leptin signaling"),
    pubmed("hepatitis C virus treatment"),
    pubmed("rheumatoid arthritis biomarkers"),
    pubmed("autism spectrum disorder genetics"),
    pubmed("malaria drug resistance"),
    pubmed("tuberculosis diagnosis"),
    pubmed("HIV antiretroviral therapy"),
    pubmed("cystic fibrosis CFTR"),
    pubmed("schizophrenia genetics"),
    pubmed("obesity GLP-1 receptor agonist"),
    pubmed("colorectal cancer screening"),
    pubmed("influenza vaccine development"),
    pubmed("sepsis biomarkers"),
    pubmed("stroke thrombolysis"),
    pubmed("epilepsy anticonvulsant"),
    pubmed("psoriasis treatment"),
    pubmed("osteoarthritis cartilage"),
    pubmed("sickle cell disease gene therapy"),
    pubmed("Huntington disease pathogenesis"),
    pubmed("melanoma checkpoint inhibitor"),
    pubmed("Zika virus microcephaly"),
    pubmed("antibiotic resistance mechanisms"),

    # clinical (ClinicalTrials.gov)
    clinicaltrials("CRISPR"),
    clinicaltrials("diabetes"),
    clinicaltrials("Alzheimer disease"),
    clinicaltrials("melanoma"),
    clinicaltrials("lung cancer immunotherapy"),
    clinicaltrials("heart failure"),
    clinicaltrials("multiple sclerosis"),
    clinicaltrials("asthma"),
    clinicaltrials("chronic kidney disease"),
    clinicaltrials("osteoporosis"),
    clinicaltrials("depression"),
    clinicaltrials("breast cancer"),
    clinicaltrials("prostate cancer"),
    clinicaltrials("COVID-19"),
    clinicaltrials("psoriasis"),
    clinicaltrials("epilepsy"),
    clinicaltrials("stroke"),
    clinicaltrials("sepsis"),
    clinicaltrials("obesity"),
    clinicaltrials("hepatitis B"),
    clinicaltrials("tuberculosis"),
    clinicaltrials("leukemia"),
    clinicaltrials("Parkinson disease"),
    clinicaltrials("cystic fibrosis"),
    clinicaltrials("schizophrenia"),
    clinicaltrials("rheumatoid arthritis"),

    # protein (UniProt)
    uniprot("insulin"),
    uniprot("hemoglobin"),
    uniprot("p53"),
    uniprot("collagen"),
    uniprot("myosin"),
    uniprot("albumin"),
    uniprot("cytochrome c"),
    uniprot("keratin"),
    uniprot("actin"),
    uniprot("amylase"),
    uniprot("lipase"),
    uniprot("trypsin"),
    uniprot("lysozyme"),
    uniprot("ferritin"),
    uniprot("transferrin"),
    uniprot("fibrinogen"),
    uniprot("immunoglobulin G"),
    uniprot("interferon gamma"),
    uniprot("tumor necrosis factor"),
    uniprot("vascular endothelial growth factor"),
    uniprot("epidermal growth factor receptor"),

    # genomic (NCBI Gene)
    ncbi_gene("insulin"),
    ncbi_gene("BRCA1"),
    ncbi_gene("APOE"),
    ncbi_gene("EGFR"),
    ncbi_gene("KRAS"),
    ncbi_gene("PTEN"),
    ncbi_gene("MYC"),
    ncbi_gene("VEGFA"),
    ncbi_gene("CFTR"),
    ncbi_gene("TNF"),
    ncbi_gene("IL6"),
    ncbi_gene("PIK3CA"),
    ncbi_gene("BRAF"),
    ncbi_gene("ALK"),
    ncbi_gene("RB1"),
    ncbi_gene("APC"),
    ncbi_gene("MLH1"),
    ncbi_gene("STAT3"),
    ncbi_gene("NOTCH1"),
    ncbi_gene("SMAD4"),
]
