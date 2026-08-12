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


def medlineplus(term, retmax=10):
    import urllib.parse
    # binning-state=group==Health Topics restricts the federated Vivisimo search
    # to the same single source (healthTopics) the wsearch.nlm.nih.gov ground-truth
    # API queries. Without this filter the website blends in Genetics/Medical
    # Encyclopedia/etc. results the API never returns -- verified by hand for
    # "epilepsy" (0% overlap unfiltered vs. exact 10/10 match filtered).
    binning = urllib.parse.quote("group==Health Topics")
    return {
        "id": f"medlineplus_{_slug(term)}",
        "name": f"MedlinePlus — {term}",
        "category": "disease",
        "url": f"https://vsearch.nlm.nih.gov/vivisimo/cgi-bin/query-meta?v%3Aproject=medlineplus&v%3Asources=medlineplus-bundle&query={urllib.parse.quote_plus(term)}&binning-state={binning}",
        "mode": "A",
        "row_xpath": "//ol[contains(@class,'results')]/li",
        "columns": [
            {"name": "Title", "xpath": ".//a[@class='title']"},
            {"name": "URL", "xpath": ".//span[@class='url']"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "medlineplus_api", "term": term, "retmax": retmax},
        "key_field": "URL",
    }


def uniprot_entry(accession):
    # Single Page Mode: absolute XPath per field, no row selector, one record
    # per page. Field selectors navigate from a stable data-article-id label
    # to its sibling value div -- hand-verified against the real rendered
    # entry page (see README) before being templated here.
    def field(article_id):
        return f"(//span[@data-article-id='{article_id}'])[1]/parent::div/following-sibling::div[1]"
    return {
        "id": f"uniprot_entry_{_slug(accession)}",
        "name": f"UniProt Entry — {accession}",
        "category": "protein",
        "url": f"https://www.uniprot.org/uniprotkb/{accession}/entry",
        "mode": "B",
        "row_xpath": None,
        "columns": [
            {"name": "ProteinName", "xpath": field("protein_names")},
            {"name": "GeneName", "xpath": field("gene_name")},
            {"name": "Organism", "xpath": field("organism-name")},
            {"name": "Status", "xpath": field("entry_status")},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "uniprot_entry_api", "accession": accession},
        "key_field": None,  # single-page mode: field-level comparison, not row matching
    }


def clinicaltrials_study(nct_id):
    # Single Page Mode: absolute XPath per field on an individual study page.
    # Selectors hand-verified against the real rendered page for NCT03057912
    # (see README): the visible title is an <h2 class="brief-title">, not an
    # <h1>; status is a span with class "overall-status" whose display text
    # ("Unknown status") differs in wording from the API's raw enum value
    # ("UNKNOWN") -- normalized via STATUS_DISPLAY in fetch_ground_truth.py.
    return {
        "id": f"clinicaltrials_study_{_slug(nct_id)}",
        "name": f"ClinicalTrials.gov Study — {nct_id}",
        "category": "clinical",
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
        "mode": "B",
        "row_xpath": None,
        "columns": [
            {"name": "Title", "xpath": "(//h2[@class='brief-title'])[1]"},
            {"name": "Status", "xpath": "(//*[contains(@class,'overall-status')])[1]"},
        ],
        "pagination": {"type": "none"},
        "ground_truth": {"method": "clinicaltrials_study_api", "nct_id": nct_id},
        "key_field": None,
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

    # clinical, Single Page Mode (ClinicalTrials.gov individual study pages)
    clinicaltrials_study("NCT03057912"),
    clinicaltrials_study("NCT04535648"),
    clinicaltrials_study("NCT06783270"),
    clinicaltrials_study("NCT04074369"),
    clinicaltrials_study("NCT06208878"),
    clinicaltrials_study("NCT07053488"),
    clinicaltrials_study("NCT04178382"),
    clinicaltrials_study("NCT03167450"),
    clinicaltrials_study("NCT07580001"),
    clinicaltrials_study("NCT07053462"),

    # protein, Single Page Mode (UniProt individual entry pages)
    uniprot_entry("P01308"),  # Insulin (INS)
    uniprot_entry("P04637"),  # Cellular tumor antigen p53 (TP53)
    uniprot_entry("P38398"),  # BRCA1
    uniprot_entry("P00533"),  # EGFR
    uniprot_entry("P60484"),  # PTEN
    uniprot_entry("P01116"),  # KRAS
    uniprot_entry("P01106"),  # MYC
    uniprot_entry("P15692"),  # VEGFA
    uniprot_entry("P13569"),  # CFTR
    uniprot_entry("P01375"),  # TNF
    uniprot_entry("P05231"),  # IL6
    uniprot_entry("P42336"),  # PIK3CA
    uniprot_entry("P15056"),  # BRAF

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

    # disease (MedlinePlus)
    medlineplus("diabetes"),
    medlineplus("hypertension"),
    medlineplus("asthma"),
    medlineplus("epilepsy"),
    medlineplus("migraine"),
    medlineplus("osteoporosis"),
    medlineplus("anemia"),
    medlineplus("thyroid disease"),
    medlineplus("hepatitis"),
    medlineplus("tuberculosis"),
    medlineplus("malaria"),
    medlineplus("influenza"),
    medlineplus("pneumonia"),
    medlineplus("rheumatoid arthritis"),
    medlineplus("depression"),
    medlineplus("anxiety disorder"),
    medlineplus("obesity"),
    medlineplus("stroke"),
    medlineplus("multiple sclerosis"),
    medlineplus("cystic fibrosis"),
    medlineplus("sickle cell disease"),
    medlineplus("lupus"),
]
