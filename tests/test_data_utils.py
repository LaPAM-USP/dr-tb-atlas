import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from data_utils import DataLoader, protein_length_from_cds

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))


@pytest.fixture(scope="module")
def loader():
    instance = DataLoader(DATA_DIR)
    instance.load_gff3()
    return instance


# ----------------------------------------------------------------------
# TASK-06: protein length
# ----------------------------------------------------------------------
@pytest.mark.parametrize("cds_length,expected", [
    (429, 142),    # mmpS5 / Rv0677c
    (2223, 740),   # katG / Rv1908c
    (1524, 507),   # dnaA / Rv0001
    (3, None),     # too short to encode a protein
    (None, None),  # non-coding feature
])
def test_protein_length_excludes_the_stop_codon(cds_length, expected):
    assert protein_length_from_cds(cds_length) == expected


def test_gene_overview_reports_both_lengths(loader):
    """TASK-06: mmpS5 is 429 bp / 142 aa."""
    gene = loader.get_gene_info("Rv0677c")
    assert gene.gene_name == "mmpS5"
    assert gene.length == 429
    assert gene.protein_length == 142


def test_non_coding_gene_has_no_protein_length(loader):
    gene = loader.get_gene_info("rrs")
    assert gene.biotype == "rRNA"
    assert gene.protein_length is None


# ----------------------------------------------------------------------
# TASK-02: gene resolution by either identifier
# ----------------------------------------------------------------------
@pytest.mark.parametrize("token,name,locus_tag", [
    ("katG", "katG", "Rv1908c"),
    ("Rv1908c", "katG", "Rv1908c"),
    ("mmpS5", "mmpS5", "Rv0677c"),
    ("Rv0677c", "mmpS5", "Rv0677c"),
    ("rv0677c", "mmpS5", "Rv0677c"),  # lookups are case-insensitive
    ("Rv0678", "Rv0678", "Rv0678"),
])
def test_genes_resolve_from_symbol_or_locus_tag(loader, token, name, locus_tag):
    gene = loader.get_gene_info(token)
    assert (gene.gene_name, gene.locus_tag) == (name, locus_tag)


def test_unknown_gene_returns_none(loader):
    assert loader.get_gene_info("not_a_gene") is None


# ----------------------------------------------------------------------
# TASK-05: catalogue membership
# ----------------------------------------------------------------------
def test_every_catalogue_gene_resolves_against_the_annotation(loader):
    """The alias map is derived from the GFF3, so no gene may be left behind."""
    catalogue = loader.load_catalogue()
    unresolved = [
        gene for gene in catalogue["gene"].dropna().unique()
        if loader.get_gene_info(gene) is None
    ]
    assert unresolved == []


@pytest.mark.parametrize("token", ["katG", "Rv1908c", "mmpS5", "Rv0678", "rrs"])
def test_catalogued_genes_are_detected(loader, token):
    assert loader.is_gene_in_catalogue(loader.get_gene_info(token))


@pytest.mark.parametrize("token", ["Rv0002", "dnaN", "Rv0003", "recF"])
def test_non_catalogued_genes_are_detected(loader, token):
    """TASK-05: annotated genes with no catalogue entry must be recognised."""
    assert not loader.is_gene_in_catalogue(loader.get_gene_info(token))


def test_resistance_lookup_works_from_a_locus_tag(loader):
    """A locus-tag search must reach rows the catalogue files under a symbol."""
    by_locus = loader.get_drug_resistance_info("Rv1908c")
    by_symbol = loader.get_drug_resistance_info("katG")
    assert len(by_locus) == len(by_symbol) > 0
    assert set(by_locus["gene"].unique()) == {"katG"}


def test_resistance_lookup_for_a_non_catalogued_gene_is_empty(loader):
    assert len(loader.get_drug_resistance_info("Rv0002")) == 0


@pytest.mark.parametrize("mutation", ["p.Ser315Thr", "Ser315Thr", "katG_p.Ser315Thr"])
def test_mutation_lookup_accepts_prefixed_and_bare_notation(loader, mutation):
    rows = loader.get_drug_resistance_info("katG", mutation)
    assert len(rows) > 0
    assert set(rows["mutation"].unique()) == {"p.Ser315Thr"}


def test_variant_coordinates_are_indexed_by_gene(loader):
    """TASK-04: coordinates are reachable from a locus tag as well."""
    variants = loader.search_mutations_by_gene("Rv1908c")
    assert len(variants) > 0
    assert variants["variant"].str.startswith("katG_").all()


# ----------------------------------------------------------------------
# TASK-10: neighbourhood navigation
# ----------------------------------------------------------------------
def test_neighbor_genes(loader):
    """mmpS5 sits between mmpL5 and Rv0678."""
    previous, following = loader.get_neighbor_genes(loader.get_gene_info("mmpS5"))
    assert previous.display_name == "mmpL5"
    assert following.display_name == "Rv0678"


# ----------------------------------------------------------------------
# TASK-13 / TASK-14: drug browsing and summary statistics
# ----------------------------------------------------------------------
def test_drug_gene_map_lists_first_line_drugs_first(loader):
    drug_map = loader.get_drug_gene_map()
    assert list(drug_map)[:4] == ["Isoniazid", "Rifampicin", "Pyrazinamide", "Ethambutol"]


def test_drug_gene_map_resolves_locus_tags(loader):
    """TASK-13: each chip needs a locus tag to navigate with."""
    bedaquiline = loader.get_drug_gene_map()["Bedaquiline"]
    by_gene = {entry["gene"]: entry for entry in bedaquiline}
    assert by_gene["atpE"]["locus_tag"] == "Rv1305"
    assert by_gene["Rv0678"]["locus_tag"] == "Rv0678"
    assert by_gene["pepQ"]["locus_tag"] == "Rv2535c"
    assert all(entry["variant_count"] > 0 for entry in bedaquiline)


def test_catalogue_summary_totals_are_consistent(loader):
    """TASK-14: per-gene counts must add up to the catalogue totals."""
    summary = loader.get_catalogue_summary()
    totals = loader.get_catalogue_totals()

    assert len(summary) == totals["genes"]
    assert summary["Associations"].sum() == totals["associations"]
    assert summary["Tier 1"].sum() == totals["tier_1"]
    assert summary["Tier 2"].sum() == totals["tier_2"]
    # Every association carries exactly one tier.
    assert totals["tier_1"] + totals["tier_2"] == totals["associations"]


def test_drug_summary_totals_are_consistent(loader):
    summary = loader.get_drug_summary()
    totals = loader.get_catalogue_totals()
    assert len(summary) == totals["drugs"]
    assert summary["Associations"].sum() == totals["associations"]


def test_catalogue_summary_reports_lof_counts(loader):
    summary = loader.get_catalogue_summary().set_index("Gene")
    assert summary.loc["katG", "LoF"] >= 1
    assert summary.loc["katG", "Locus tag"] == "Rv1908c"


# ----------------------------------------------------------------------
# Sequence retrieval (TASK-09.3)
# ----------------------------------------------------------------------
def test_coding_sequence_starts_with_a_start_codon(loader):
    """A minus-strand gene must be returned in its own orientation."""
    gene = loader.get_gene_info("mmpS5")
    cds = loader.get_gene_sequence(gene)
    assert len(cds) == 429
    assert cds.startswith("ATG")


def test_flanking_sequence_extraction(loader):
    gene = loader.get_gene_info("mmpS5")
    assert len(loader.get_gene_sequence(gene, flank=500)) == 429 + 1000


def test_translation_length_matches_the_reported_protein_length(loader):
    gene = loader.get_gene_info("mmpS5")
    protein = loader.translate_gene(gene).rstrip("*")
    assert len(protein) == gene.protein_length == 142
    assert protein.startswith("M")


def test_translation_is_none_for_non_coding_genes(loader):
    assert loader.translate_gene(loader.get_gene_info("rrs")) is None
