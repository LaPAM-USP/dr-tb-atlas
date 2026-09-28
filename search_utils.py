"""
Query parsing and normalisation for the DR-TBAtlas search bar.

The search bar accepts three input formats (TASK-02):

1. Locus tag / gene ID        e.g. ``Rv0677c``
2. Gene name / symbol         e.g. ``mmpS5``
3. Variant name               e.g. ``katG_Ser315Thr``

Mutations are normalised to the three-letter amino acid notation used by the
WHO catalogue (``katG_p.Ser315Thr``), so legacy one-letter input such as
``katG_S315T`` still resolves.
"""
import re
from dataclasses import dataclass
from typing import Optional

# Three-letter amino acid code is the WHO catalogue standard. The one-letter
# map exists only so that legacy/abbreviated user input can be up-converted.
ONE_TO_THREE_LETTER_AA = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys",
    "Q": "Gln", "E": "Glu", "G": "Gly", "H": "His", "I": "Ile",
    "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro",
    "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val",
    "X": "Xaa", "*": "Ter",
}

THREE_LETTER_AA = {v.lower(): v for v in ONE_TO_THREE_LETTER_AA.values()}
THREE_LETTER_AA["ter"] = "Ter"
THREE_LETTER_AA["stop"] = "Ter"

# A mutation typed without its gene prefix, e.g. "Ser315Thr", "p.Ser315Thr",
# "S315T", "Asp47fs", "Met1?". Used only for the advisory alert (TASK-03).
# The residue codes are validated separately by ``looks_like_mutation`` so that
# an unknown identifier such as "abc123" is reported as a missing gene rather
# than as a malformed mutation.
STANDALONE_MUTATION_REGEX = re.compile(
    r"^(?:p\.)?"
    r"([A-Z][a-z]{2}|[A-Z])"            # reference residue (3-letter or 1-letter)
    r"(\d+)"                            # codon position
    r"([A-Z][a-z]{2}|[A-Z]|fs|del|dup|ins|LoF|\?|\*|=)?$",  # replacement / consequence
    re.IGNORECASE,
)

# Valid residue tokens, in both notations, used to validate a match.
_VALID_RESIDUES = (
    {code.lower() for code in ONE_TO_THREE_LETTER_AA}
    | set(THREE_LETTER_AA)
    | {"fs", "del", "dup", "ins", "ext", "lof", "?", "*", "="}
)

# Nucleotide-level mutation typed without its gene prefix, e.g. "c.-15C>T".
STANDALONE_NUCLEOTIDE_REGEX = re.compile(
    r"^[cn]\.-?\d+[ACGT]*(?:>[ACGT]+|del[ACGT]*|dup[ACGT]*|ins[ACGT]+)?$",
    re.IGNORECASE,
)

# H37Rv locus tags: Rv0001, Rv0677c, Rv1963A, Rvnr01, Rvnt02, RVnc0001 ...
LOCUS_TAG_REGEX = re.compile(r"^R[Vv](?:\d{4}[A-Da-d]?|n[rstc]\d{2,4})$")


def looks_like_mutation(token: str) -> bool:
    """
    Whether a token is a protein- or nucleotide-level mutation on its own.

    Beyond the regex shape, the residue codes have to be real amino acid
    abbreviations, so an arbitrary identifier is not mistaken for a mutation.
    """
    if STANDALONE_NUCLEOTIDE_REGEX.match(token):
        return True

    match = STANDALONE_MUTATION_REGEX.match(token)
    if not match:
        return False

    reference, _, consequence = match.groups()
    if reference.lower() not in _VALID_RESIDUES:
        return False
    if consequence and consequence.lower() not in _VALID_RESIDUES:
        return False
    return True


MUTATION_ADVICE = (
    "Please specify the gene name followed by an underscore and the mutation "
    "(e.g., katG_Ser315Thr). A mutation alone cannot be resolved uniquely "
    "across the genome."
)


@dataclass
class ParsedQuery:
    """Structured result of parsing a raw search string."""

    raw: str
    kind: str  # "empty" | "gene" | "variant" | "standalone_mutation"
    gene_token: Optional[str] = None
    mutation: Optional[str] = None  # normalised, e.g. "p.Ser315Thr"
    message: Optional[str] = None

    @property
    def variant(self) -> Optional[str]:
        """Full variant identifier as used by the catalogue, if applicable."""
        if self.gene_token and self.mutation:
            return f"{self.gene_token}_{self.mutation}"
        return None


def normalize_query(raw: Optional[str]) -> str:
    """Strip whitespace and stray leading/trailing separators (TASK-02.3)."""
    if not raw:
        return ""
    cleaned = re.sub(r"\s+", "", str(raw))
    return cleaned.strip("_.,;:|/\\-")


def looks_like_locus_tag(token: str) -> bool:
    """True when the token has the shape of an H37Rv locus tag."""
    return bool(LOCUS_TAG_REGEX.match(token))


def normalize_mutation(mutation: str) -> str:
    """
    Normalise a mutation string to WHO catalogue notation.

    ``Ser315Thr``  -> ``p.Ser315Thr``
    ``S315T``      -> ``p.Ser315Thr``
    ``p.ser315thr``-> ``p.Ser315Thr``
    ``c.1349C>T``  -> ``c.1349C>T``
    ``LoF``        -> ``LoF``
    """
    if not mutation:
        return ""

    token = mutation.strip()

    if token.lower() == "lof":
        return "LoF"
    if token.lower() in ("deletion", "feature_ablation"):
        return "deletion"

    # Nucleotide notation is passed through with a normalised prefix and
    # upper-case bases, e.g. "c.-15c>t" -> "c.-15C>T".
    nucleotide = re.match(r"^([cn])\.(-?\d+)(.*)$", token, re.IGNORECASE)
    if nucleotide:
        prefix, position, rest = nucleotide.groups()
        return f"{prefix.lower()}.{position}{rest.upper()}"

    has_prefix = token.lower().startswith("p.")
    body = token[2:] if has_prefix else token

    protein = re.match(
        r"^([A-Za-z*]{1,3})(\d+)([A-Za-z*?=]{0,4})$",
        body,
    )
    if not protein:
        # Unrecognised shape (e.g. "Glu107_Asp109del"); keep it but make sure a
        # protein-level mutation carries its "p." prefix.
        return f"p.{body}" if has_prefix else body

    ref, position, alt = protein.groups()
    return f"p.{_normalize_residue(ref)}{position}{_normalize_consequence(alt)}"


def _normalize_residue(residue: str) -> str:
    """Convert a one- or three-letter residue code to three-letter form."""
    if len(residue) == 1:
        return ONE_TO_THREE_LETTER_AA.get(residue.upper(), residue.upper())
    return THREE_LETTER_AA.get(residue.lower(), residue.capitalize())


def _normalize_consequence(alt: str) -> str:
    """Normalise the replacement residue or consequence suffix."""
    if not alt:
        return ""
    lowered = alt.lower()
    if lowered in ("fs", "del", "dup", "ins", "ext"):
        return lowered
    if lowered == "lof":
        return "LoF"
    if alt in ("?", "*", "="):
        return alt
    return _normalize_residue(alt)


def strip_mutation_prefix(mutation: Optional[str]) -> str:
    """Return the mutation without a leading ``p.``/``c.``/``n.`` prefix."""
    if not mutation:
        return ""
    return re.sub(r"^[pcn]\.", "", mutation.strip(), flags=re.IGNORECASE)


def parse_query(raw: Optional[str], gene_resolver=None) -> ParsedQuery:
    """
    Parse a raw search string into a structured query.

    ``gene_resolver`` is an optional callable ``str -> bool`` that reports
    whether a token is a known gene name or locus tag. It is consulted before
    the standalone-mutation heuristic so that real gene identifiers are never
    mistaken for mutations.
    """
    cleaned = normalize_query(raw)
    if not cleaned:
        return ParsedQuery(raw=raw or "", kind="empty")

    # Format 3: variant, "gene_mutation".
    if "_" in cleaned:
        gene_token, mutation = cleaned.split("_", 1)
        gene_token = gene_token.strip()
        mutation = mutation.strip()
        if gene_token and mutation:
            return ParsedQuery(
                raw=cleaned,
                kind="variant",
                gene_token=gene_token,
                mutation=normalize_mutation(mutation),
            )
        cleaned = gene_token or mutation

    # Formats 1 and 2: locus tag or gene symbol. Checking the annotation first
    # keeps genes such as "Rv0678" or "whiB7" out of the mutation branch.
    if looks_like_locus_tag(cleaned):
        return ParsedQuery(raw=cleaned, kind="gene", gene_token=cleaned)
    if gene_resolver is not None and gene_resolver(cleaned):
        return ParsedQuery(raw=cleaned, kind="gene", gene_token=cleaned)

    # A mutation with no gene prefix cannot be resolved uniquely (TASK-03).
    if looks_like_mutation(cleaned):
        return ParsedQuery(
            raw=cleaned,
            kind="standalone_mutation",
            mutation=normalize_mutation(cleaned),
            message=MUTATION_ADVICE,
        )

    return ParsedQuery(raw=cleaned, kind="gene", gene_token=cleaned)
