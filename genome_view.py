"""
Genome visualisation components.

The embedded **JBrowse 2** linear view is the genome explorer: it carries the
flattened annotation (TASK-09) plus the WHO catalogue, GC content and
selection tracks built by :mod:`browser_tracks`. A toolbar above it sets the
focus (gene, flanking window or selected mutation) and the visible tracks,
and a legend and usage guide sit below it.
"""
from typing import Dict, List, Optional

import dash_bootstrap_components as dbc
import dash_jbrowse
from dash import dcc, html

import browser_tracks
from data_utils import GeneInfo

# Default flank for sequence retrieval and for the browser's opening view.
DEFAULT_FLANK_BP = 500

# Bases shown either side of a selected mutation: enough to read the codon
# and the six-frame translation.
MUTATION_FLANK_BP = 40

FOCUS_GENE = "gene"
FOCUS_MUTATION = "mutation"
FOCUS_CHOICES = [
    {"label": "Gene", "value": FOCUS_GENE},
    {"label": "± 500 bp", "value": "500"},
    {"label": "± 2 kb", "value": "2000"},
    {"label": "± 10 kb", "value": "10000"},
    {"label": "± 50 kb", "value": "50000"},
    {"label": "Selected mutation", "value": FOCUS_MUTATION},
]
DEFAULT_FOCUS = str(DEFAULT_FLANK_BP)

JBROWSE_ID = "jbrowse-linear-view"


def focus_location(
    gene_info: GeneInfo, focus: Optional[str], selection: Optional[Dict] = None
) -> str:
    """Locus string for a focus choice, falling back to the gene."""
    position = (selection or {}).get("position")
    if focus == FOCUS_MUTATION and position:
        return browser_tracks.locus_string(
            gene_info.chromosome,
            int(position) - MUTATION_FLANK_BP,
            int(position) + MUTATION_FLANK_BP,
        )
    if focus and focus.isdigit():
        flank = int(focus)
    else:
        # A little padding keeps the gene's ends clear of the view edges.
        flank = max(20, gene_info.length // 20)
    return browser_tracks.locus_string(
        gene_info.chromosome, gene_info.start - flank, gene_info.end + flank
    )


def jbrowse_view(
    tracks: browser_tracks.BrowserTracks,
    gene_info: GeneInfo,
    focus: Optional[str] = DEFAULT_FOCUS,
    visible_tracks: Optional[List[str]] = None,
    drug_tracks: Optional[List[str]] = None,
    selection: Optional[Dict] = None,
) -> dash_jbrowse.LinearGenomeView:
    """The JBrowse 2 linear view for a gene, focus and track selection."""
    visible = list(visible_tracks if visible_tracks is not None else browser_tracks.DEFAULT_TRACKS)
    visible += [browser_tracks.drug_track_id(drug) for drug in (drug_tracks or [])]
    config = tracks.config(
        visible_tracks=visible,
        selection_features=browser_tracks.selection_features(gene_info, selection),
    )
    return dash_jbrowse.LinearGenomeView(
        id=JBROWSE_ID,
        assembly=config["assembly"],
        tracks=config["tracks"],
        defaultSession=config["defaultSession"],
        aggregateTextSearchAdapters=config["aggregateTextSearchAdapters"],
        configuration=config["configuration"],
        location=focus_location(gene_info, focus, selection),
    )


def jbrowse_card(jbrowse_component, drugs: List[str]) -> dbc.Card:
    """Card wrapping the embedded JBrowse 2 linear genome view and its controls."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col(
                    html.H5(
                        [html.I(className="bi bi-eye me-2"), "Genome Browser"],
                        className="card-header-title",
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.RadioItems(
                        id="genome-focus",
                        options=FOCUS_CHOICES,
                        value=DEFAULT_FOCUS,
                        inline=True,
                        className="window-toggle",
                        inputClassName="btn-check",
                        labelClassName="btn btn-sm window-toggle-btn",
                        labelCheckedClassName="active",
                    ),
                    md=8,
                    className="text-md-end",
                ),
            ], align="center", className="g-2"),
        ], className="card-header-custom"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Tracks", className="small text-muted d-block mb-1"),
                    dbc.Checklist(
                        id="genome-tracks",
                        options=browser_tracks.TRACK_CHOICES,
                        value=list(browser_tracks.DEFAULT_TRACKS),
                        inline=True,
                        switch=True,
                        className="track-toggle small",
                    ),
                ], lg=8),
                dbc.Col([
                    html.Label(
                        "Resistance variants by drug",
                        className="small text-muted d-block mb-1",
                        htmlFor="genome-drug-tracks",
                    ),
                    dcc.Dropdown(
                        id="genome-drug-tracks",
                        options=[{"label": drug, "value": drug} for drug in drugs],
                        value=[],
                        multi=True,
                        placeholder="Add a track per drug…",
                        className="drug-track-picker",
                    ),
                ], lg=4),
            ], className="g-3 mb-3"),

            html.Div(jbrowse_component, id="jbrowse-view", className="jbrowse-container"),

            browser_legend(),
            browser_guide(),
        ]),
    ], id="genome-browser-card", className="result-card")


def _swatch(color: str, label: str) -> html.Span:
    return html.Span([
        html.Span(className="legend-swatch", style={"backgroundColor": color}),
        label,
    ], className="d-inline-flex align-items-center")


def browser_legend() -> html.Div:
    """Colour key shared by the gene and catalogue tracks."""
    grades = browser_tracks.GRADE_COLORS
    labels = browser_tracks.GRADE_LABELS
    genes = browser_tracks.GENE_COLORS
    return html.Div([
        html.Div([
            html.Span("Genes", className="legend-heading"),
            _swatch(genes["forward"], "Forward strand"),
            _swatch(genes["reverse"], "Reverse strand"),
            _swatch(genes["noncoding"], "rRNA / tRNA / ncRNA"),
            _swatch(genes["pseudogene"], "Pseudogene"),
            _swatch(browser_tracks.SELECTION_COLOR, "Selected mutation"),
        ], className="legend-row"),
        html.Div([
            html.Span("WHO grading", className="legend-heading"),
            *[_swatch(grades[group], f"{group}) {labels[group]}") for group in sorted(grades)],
        ], className="legend-row"),
        html.Div([
            html.Span("Catalogue genes", className="legend-heading"),
            _swatch(browser_tracks.TIER_COLORS["1"], "Tier 1"),
            _swatch(browser_tracks.TIER_COLORS["2"], "Tier 2"),
        ], className="legend-row"),
    ], className="browser-legend small text-muted mt-3")


def browser_guide() -> html.Details:
    """Short guide to the browser's built-in tools."""
    tips = [
        ("bi-search", "Search", [
            "Type a gene name, locus tag, product word or catalogue variant "
            "(e.g. ", html.Code("katG_p.Ser315Thr"), ") into the browser's "
            "location box.",
        ]),
        ("bi-arrows-move", "Navigate", [
            "Drag the tracks to pan, use the zoom buttons or the overview bar, "
            "or drag across the ruler to select a region and zoom into it or "
            "get its sequence.",
        ]),
        ("bi-card-text", "Feature details", [
            "Click any gene or variant for its product, functional note, WHO "
            "grading per drug and a link to the Mycobrowser gene page.",
        ]),
        ("bi-layers", "More tracks", [
            "Open the track selector from the view menu (",
            html.I(className="bi bi-list"),
            ") for every grading and per-drug track, grouped by category.",
        ]),
        ("bi-sliders", "Track options", [
            "Use a track's menu to switch between normal, compact and collapsed "
            "layouts, show or hide labels, or rescale quantitative tracks.",
        ]),
        ("bi-tools", "Tools", [
            "The view menu also offers motif search (adds a track of matches), "
            "SVG export for figures and horizontal flipping, so reverse-strand "
            "genes read 5'→3'. Zoom to base level to see the six-frame translation.",
        ]),
    ]
    return html.Details([
        html.Summary([html.I(className="bi bi-question-circle me-2"), "Using the genome browser"],
                     className="small text-primary"),
        dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"bi {icon} browser-tip-icon"),
                html.Div([html.Strong(title, className="d-block small"),
                          html.Span(body, className="small text-muted")]),
            ], className="d-flex gap-2"), md=6, lg=4)
            for icon, title, body in tips
        ], className="g-3 mt-1"),
        html.P([
            html.I(className="bi bi-info-circle me-2"),
            "The annotation is flattened to one feature per locus: in ",
            html.I("M. tuberculosis"),
            " a CDS is the gene, so no separate CDS track or intron controls are shown.",
        ], className="text-muted small mb-0 mt-3"),
    ], className="browser-guide mt-3")


def sequence_card(gene_info: GeneInfo) -> dbc.Card:
    """
    Sequence retrieval panel.

    Replaces the browser's eukaryotic "gene w/ introns" options with the two
    that are meaningful for a bacterium — the coding sequence and its protein
    translation — while keeping adjustable upstream/downstream flanking
    extraction at the ±500 bp default (TASK-09).
    """
    options = [
        {"label": "Coding sequence (CDS = gene)", "value": "cds"},
        {"label": "CDS + flanks", "value": "cds_flank"},
        {"label": "Upstream flank only", "value": "upstream"},
        {"label": "Downstream flank only", "value": "downstream"},
    ]
    if gene_info.is_protein_coding:
        options.insert(2, {"label": "Protein translation", "value": "protein"})

    return dbc.Card([
        dbc.CardHeader([
            html.H5(
                [html.I(className="bi bi-code-square me-2"), "Sequence Retrieval"],
                className="card-header-title",
            )
        ], className="card-header-custom"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Sequence", className="small text-muted mb-1"),
                    dbc.Select(id="sequence-kind", options=options, value="cds", size="sm"),
                ], md=5),
                dbc.Col([
                    dbc.Label("Flanking bases (± bp)", className="small text-muted mb-1"),
                    dbc.Input(
                        id="sequence-flank",
                        type="number",
                        value=DEFAULT_FLANK_BP,
                        min=0,
                        max=10000,
                        step=50,
                        size="sm",
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label(" ", className="small d-block mb-1"),
                    html.Div([
                        dcc.Clipboard(
                            id="sequence-clipboard",
                            title="Copy sequence",
                            className="copy-btn",
                        ),
                        html.Span("Copy", className="small text-muted ms-1"),
                    ], className="d-flex align-items-center"),
                ], md=3),
            ], className="g-2 align-items-end"),
            html.Div(id="sequence-meta", className="small text-muted mt-3"),
            html.Pre(id="sequence-output", className="sequence-output mt-2"),
        ]),
    ], className="result-card")


def format_sequence(sequence: str, block: int = 10, per_line: int = 60) -> str:
    """Format a sequence into spaced blocks for readable, copyable output."""
    if not sequence:
        return ""
    lines = []
    for offset in range(0, len(sequence), per_line):
        chunk = sequence[offset:offset + per_line]
        blocks = " ".join(chunk[i:i + block] for i in range(0, len(chunk), block))
        lines.append(f"{offset + 1:>9,}  {blocks}")
    return "\n".join(lines)


def neighbor_navigation(
    previous: Optional[GeneInfo], following: Optional[GeneInfo]
) -> html.Div:
    """Previous/next gene shortcuts for keyboard-free neighbourhood browsing."""
    def button(gene: Optional[GeneInfo], direction: str) -> dbc.Button:
        if gene is None:
            return dbc.Button("—", size="sm", disabled=True, className="neighbor-btn")
        icon = "bi-chevron-left" if direction == "prev" else "bi-chevron-right"
        content = [html.I(className=f"bi {icon} me-1"), gene.display_name]
        if direction == "next":
            content = [gene.display_name, html.I(className=f"bi {icon} ms-1")]
        return dbc.Button(
            content,
            id={"type": "neighbor-link", "index": gene.locus_tag},
            size="sm",
            className="neighbor-btn",
            title=f"{gene.display_name} ({gene.locus_tag}) · {gene.product or 'no product'}",
        )

    return html.Div([
        html.Span("Neighbouring genes:", className="text-muted small me-2"),
        button(previous, "prev"),
        button(following, "next"),
    ], className="d-flex align-items-center gap-2 flex-wrap")
