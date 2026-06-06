"""Externalized impact-classification rules.

All classification policy lives in two plain data tables plus one documented
default. There are no if/else decision trees: classification is dictionary
lookup. To change policy, edit a table — the logic in ``graph.py`` does not
change. This is what makes the system auditable: the rules ARE the data.
"""

from __future__ import annotations

from ..models.enums import ComponentCategory
from ..diff.models import ChangeType
from .models import ImpactDomain

# --- Rule table 1: component category -> impact domain --------------------- #
# Used for every COMPONENT_* change. Keyed by the component's category, so a
# change to any component is classified by what kind of component it is.
CATEGORY_IMPACT: dict[ComponentCategory, ImpactDomain] = {
    # Anything that affects how reads become variant calls is analytical.
    ComponentCategory.BASECALLER: ImpactDomain.ANALYTICAL,
    ComponentCategory.DEMULTIPLEXER: ImpactDomain.ANALYTICAL,
    ComponentCategory.READ_TRIMMER: ImpactDomain.ANALYTICAL,
    ComponentCategory.ALIGNER: ImpactDomain.ANALYTICAL,
    ComponentCategory.DUPLICATE_MARKER: ImpactDomain.ANALYTICAL,
    ComponentCategory.BASE_RECALIBRATOR: ImpactDomain.ANALYTICAL,
    ComponentCategory.VARIANT_CALLER: ImpactDomain.ANALYTICAL,
    ComponentCategory.CNV_CALLER: ImpactDomain.ANALYTICAL,
    ComponentCategory.SV_CALLER: ImpactDomain.ANALYTICAL,
    ComponentCategory.VARIANT_FILTER: ImpactDomain.ANALYTICAL,
    ComponentCategory.REFERENCE_GENOME: ImpactDomain.ANALYTICAL,
    ComponentCategory.KNOWN_SITES: ImpactDomain.ANALYTICAL,
    # Anything that affects annotation / classification is interpretive.
    ComponentCategory.ANNOTATION: ImpactDomain.INTERPRETIVE,
    ComponentCategory.TRANSCRIPT_SET: ImpactDomain.INTERPRETIVE,
    # QC tooling affects quality acceptance.
    ComponentCategory.QC_TOOL: ImpactDomain.QUALITY,
}

# Domain applied when a component category has no explicit rule (e.g., a future
# category). Conservative-by-design: an unknown analysis component is treated as
# analytically impacting until a lab defines a rule for it. The rationale always
# discloses that the default — not an explicit rule — was applied.
DEFAULT_COMPONENT_DOMAIN: ImpactDomain = ImpactDomain.ANALYTICAL

# --- Rule table 2: non-component change type -> impact domain -------------- #
CHANGE_TYPE_IMPACT: dict[ChangeType, ImpactDomain] = {
    ChangeType.QC_THRESHOLD_ADDED: ImpactDomain.QUALITY,
    ChangeType.QC_THRESHOLD_REMOVED: ImpactDomain.QUALITY,
    ChangeType.QC_THRESHOLD_CHANGED: ImpactDomain.QUALITY,
    ChangeType.PANEL_CHANGED: ImpactDomain.ANALYTICAL,
    ChangeType.PIPELINE_CHANGED: ImpactDomain.INFRASTRUCTURE,
    ChangeType.ENVIRONMENT_CHANGED: ImpactDomain.INFRASTRUCTURE,
    ChangeType.CLAIM_ADDED: ImpactDomain.DOCUMENTATION,
    ChangeType.CLAIM_REMOVED: ImpactDomain.DOCUMENTATION,
    ChangeType.CLAIM_CHANGED: ImpactDomain.DOCUMENTATION,
}