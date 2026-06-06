"""Controlled vocabularies for the AssayTrace manifest schema.

Every enum here is a *string* enum so that serialized manifests are
human-readable and diff-friendly. Categories deliberately use coarse,
stable values: the change-impact engine (Step 3) keys off these, so
adding a value is safe but renaming one is a breaking schema change.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Base for string enums (Python 3.12 has enum.StrEnum, but we keep an
    explicit base so `.value` semantics and JSON output are unambiguous)."""

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


class AssayType(StrEnum):
    GERMLINE = "germline"
    SOMATIC = "somatic"
    GERMLINE_AND_SOMATIC = "germline_and_somatic"


class SequencingScope(StrEnum):
    TARGETED_PANEL = "targeted_panel"
    EXOME = "exome"
    GENOME = "genome"
    HOTSPOT = "hotspot"


class IntendedUse(StrEnum):
    DIAGNOSTIC = "diagnostic"
    SCREENING = "screening"
    MONITORING = "monitoring"
    COMPANION_DIAGNOSTIC = "companion_diagnostic"
    RESEARCH_USE_ONLY = "research_use_only"


class RegulatoryContext(StrEnum):
    """How the assay is operated from a quality-system standpoint."""

    CLIA_LDT = "clia_ldt"            # US laboratory-developed test
    CAP_ACCREDITED = "cap_accredited"
    FDA_CLEARED = "fda_cleared"
    IVDR = "ivdr"                    # EU In Vitro Diagnostic Regulation
    ISO_15189 = "iso_15189"
    RUO = "ruo"


class WorkflowEngine(StrEnum):
    NEXTFLOW = "nextflow"
    SNAKEMAKE = "snakemake"
    WDL = "wdl"
    CROMWELL = "cromwell"
    CWL = "cwl"
    CUSTOM = "custom"


class ComponentCategory(StrEnum):
    """The functional role of a versioned pipeline component. The change-impact
    graph is built on these categories, so they are the schema's most
    change-sensitive vocabulary."""

    BASECALLER = "basecaller"
    DEMULTIPLEXER = "demultiplexer"
    READ_TRIMMER = "read_trimmer"
    ALIGNER = "aligner"
    DUPLICATE_MARKER = "duplicate_marker"
    BASE_RECALIBRATOR = "base_recalibrator"
    VARIANT_CALLER = "variant_caller"
    CNV_CALLER = "cnv_caller"
    SV_CALLER = "sv_caller"
    VARIANT_FILTER = "variant_filter"
    ANNOTATION = "annotation"
    REFERENCE_GENOME = "reference_genome"
    KNOWN_SITES = "known_sites"        # dbSNP / gnomAD VCFs used in filtering/BQSR
    TRANSCRIPT_SET = "transcript_set"  # RefSeq / Ensembl / MANE
    QC_TOOL = "qc_tool"
    OTHER = "other"


class ReferenceGenomeBuild(StrEnum):
    GRCH37 = "GRCh37"
    GRCH38 = "GRCh38"
    HG19 = "hg19"
    HG38 = "hg38"
    T2T_CHM13 = "T2T-CHM13"
    CUSTOM = "custom"


class ContainerRuntime(StrEnum):
    DOCKER = "docker"
    SINGULARITY = "singularity"
    APPTAINER = "apptainer"
    PODMAN = "podman"
    NONE = "none"


class HashAlgorithm(StrEnum):
    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA1 = "sha1"
    MD5 = "md5"

    @property
    def hex_length(self) -> int:
        return {
            HashAlgorithm.MD5: 32,
            HashAlgorithm.SHA1: 40,
            HashAlgorithm.SHA256: 64,
            HashAlgorithm.SHA512: 128,
        }[self]


class Comparator(StrEnum):
    """Direction of a QC threshold acceptance criterion."""

    GE = ">="
    LE = "<="
    GT = ">"
    LT = "<"
    EQ = "=="
    NE = "!="


class QCSeverity(StrEnum):
    BLOCKING = "blocking"            # failing this fails the run / sample
    WARNING = "warning"
    INFORMATIONAL = "informational"


class VariantType(StrEnum):
    SNV = "snv"
    INDEL = "indel"
    MNV = "mnv"
    CNV = "cnv"
    SV = "sv"
    REPEAT_EXPANSION = "repeat_expansion"
    FUSION = "fusion"


class ClaimType(StrEnum):
    """The category of validated assay claim. The revalidation engine maps
    component changes to the subset of claims they can perturb."""

    SNV_DETECTION = "snv_detection"
    INDEL_DETECTION = "indel_detection"
    CNV_DETECTION = "cnv_detection"
    SV_DETECTION = "sv_detection"
    VARIANT_CLASSIFICATION_CONSISTENCY = "variant_classification_consistency"
    QC_DECISION_STABILITY = "qc_decision_stability"
    LIMIT_OF_DETECTION = "limit_of_detection"
    REPRODUCIBILITY = "reproducibility"
    CHANGE_CONTROL_COMPLIANCE = "change_control_compliance"


class ClaimStatus(StrEnum):
    ESTABLISHED = "established"      # validated and in effect
    PROVISIONAL = "provisional"     # asserted, validation in progress
    DEPRECATED = "deprecated"


class PerformanceMetricType(StrEnum):
    SENSITIVITY = "sensitivity"
    SPECIFICITY = "specificity"
    PPV = "ppv"
    NPV = "npv"
    F1 = "f1"
    ACCURACY = "accuracy"
    CONCORDANCE = "concordance"
    REPRODUCIBILITY = "reproducibility"
    LIMIT_OF_DETECTION_VAF = "limit_of_detection_vaf"


# Metric types that are proportions and must lie within [0, 1].
PROPORTION_METRICS: frozenset[PerformanceMetricType] = frozenset(
    {
        PerformanceMetricType.SENSITIVITY,
        PerformanceMetricType.SPECIFICITY,
        PerformanceMetricType.PPV,
        PerformanceMetricType.NPV,
        PerformanceMetricType.F1,
        PerformanceMetricType.ACCURACY,
        PerformanceMetricType.CONCORDANCE,
        PerformanceMetricType.REPRODUCIBILITY,
    }
)


class ManifestStatus(StrEnum):
    DRAFT = "draft"
    IN_VALIDATION = "in_validation"
    VALIDATED = "validated"
    SUPERSEDED = "superseded"
    RETIRED = "retired"
