"""Builds a realistic somatic solid-tumor panel manifest and writes the
example JSON and YAML files. Run from the repo root: `python -m examples.build`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from assaytrace import AssayManifest, dump_manifest
from assaytrace.models.assay import AssayMetadata
from assaytrace.models.claims import AssayClaim, ConfidenceInterval, PerformanceMetric
from assaytrace.models.common import (
    Checksum,
    FileResource,
    GenomeReference,
    ResourceComponent,
    SoftwareComponent,
)
from assaytrace.models.enums import (
    AssayType,
    ClaimType,
    Comparator,
    ComponentCategory,
    ContainerRuntime,
    HashAlgorithm,
    IntendedUse,
    PerformanceMetricType,
    QCSeverity,
    ReferenceGenomeBuild,
    RegulatoryContext,
    SequencingScope,
    VariantType,
    WorkflowEngine,
)
from assaytrace.models.pipeline import (
    AssayScope,
    CoreAnalysisComponents,
    Environment,
    PipelineMetadata,
    ReferenceResources,
)
from assaytrace.models.qc import QCConfiguration, QCThreshold


def build() -> AssayManifest:
    sha = lambda h: Checksum(algorithm=HashAlgorithm.SHA256, value=h)  # noqa: E731
    h = "a" * 64  # placeholder digests for the example

    return AssayManifest(
        manifest_id=UUID("11111111-1111-1111-1111-111111111111"),
        generated_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
        generated_by="ci-pipeline@lab.example",
        status="validated",
        change_reason="Initial validated baseline for SolidTumor500 v2.3.",
        tags=("oncology", "somatic", "solid_tumor"),
        assay=AssayMetadata(
            assay_name="SolidTumor500",
            assay_version="2.3.0",
            assay_type=AssayType.SOMATIC,
            intended_use=IntendedUse.DIAGNOSTIC,
            laboratory_name="Example Molecular Diagnostics Lab",
            laboratory_id="99D9999999",
            regulatory_contexts=(RegulatoryContext.CLIA_LDT, RegulatoryContext.CAP_ACCREDITED),
            specimen_types=("FFPE",),
        ),
        pipeline=PipelineMetadata(
            pipeline_name="solidtumor-somatic-wf",
            pipeline_version="2.3.0",
            workflow_engine=WorkflowEngine.NEXTFLOW,
            workflow_version="24.10.1",
        ),
        reference_resources=ReferenceResources(
            reference_genome=GenomeReference(
                build=ReferenceGenomeBuild.GRCH38,
                version="GRCh38.p14-analysis-set",
                source="GENCODE/NCBI",
                checksum=sha(h),
            ),
            annotation_resources=(
                ResourceComponent(
                    category=ComponentCategory.ANNOTATION,
                    name="ClinVar",
                    version="2025-12-01",
                    source="NCBI ClinVar",
                ),
                ResourceComponent(
                    category=ComponentCategory.ANNOTATION,
                    name="VEP cache",
                    version="111",
                    source="Ensembl",
                ),
                ResourceComponent(
                    category=ComponentCategory.ANNOTATION,
                    name="COSMIC",
                    version="v99",
                    source="Sanger COSMIC",
                ),
                ResourceComponent(
                    category=ComponentCategory.KNOWN_SITES,
                    name="dbSNP",
                    version="156",
                    source="NCBI dbSNP",
                ),
                ResourceComponent(
                    category=ComponentCategory.TRANSCRIPT_SET,
                    name="MANE Select",
                    version="1.3",
                    source="NCBI/EMBL-EBI",
                ),
            ),
        ),
        analysis_components=CoreAnalysisComponents(
            aligner=SoftwareComponent(
                category=ComponentCategory.ALIGNER,
                name="BWA-MEM2",
                version="2.2.1",
                parameters={"-M": True, "threads": 16},
            ),
            variant_caller=SoftwareComponent(
                category=ComponentCategory.VARIANT_CALLER,
                name="Mutect2",
                version="4.5.0.0",
                vendor="GATK",
                parameters={"mode": "tumor_only", "min_base_quality_score": 20},
            ),
            cnv_caller=SoftwareComponent(
                category=ComponentCategory.CNV_CALLER,
                name="CNVkit",
                version="0.9.10",
            ),
            sv_caller=SoftwareComponent(
                category=ComponentCategory.SV_CALLER,
                name="Manta",
                version="1.6.0",
            ),
            additional_components=(
                SoftwareComponent(
                    category=ComponentCategory.VARIANT_FILTER,
                    name="FilterMutectCalls",
                    version="4.5.0.0",
                    vendor="GATK",
                ),
            ),
        ),
        assay_scope=AssayScope(
            sequencing_scope=SequencingScope.TARGETED_PANEL,
            panel_name="SolidTumor500",
            panel_version="2.3",
            bed_file=FileResource(
                path="assets/solidtumor500_v2.3.targets.bed",
                checksum=sha("b" * 64),
                line_count=18432,
            ),
            target_regions_hash=sha("b" * 64),
        ),
        qc=QCConfiguration(
            thresholds=(
                QCThreshold(
                    metric="minimum_coverage",
                    comparator=Comparator.GE,
                    threshold=500,
                    unit="x",
                    severity=QCSeverity.BLOCKING,
                ),
                QCThreshold(
                    metric="minimum_vaf",
                    comparator=Comparator.GE,
                    threshold=0.05,
                    unit="fraction",
                    severity=QCSeverity.BLOCKING,
                    applies_to=(VariantType.SNV, VariantType.INDEL),
                ),
                QCThreshold(
                    metric="maximum_contamination",
                    comparator=Comparator.LE,
                    threshold=0.02,
                    unit="fraction",
                    severity=QCSeverity.WARNING,
                ),
            )
        ),
        environment=Environment(
            container_runtime=ContainerRuntime.DOCKER,
            container_image="registry.example.com/lab/solidtumor",
            container_version="2.3.0",
            image_digest=sha("c" * 64),
            git_commit="9f2c1ab",
            build_date=date(2026, 1, 10),
        ),
        claims=(
            AssayClaim(
                claim_id="CLAIM-SNV-001",
                claim_type=ClaimType.SNV_DETECTION,
                title="SNV detection sensitivity at >=5% VAF",
                variant_types=(VariantType.SNV,),
                genomic_scope="panel target regions",
                claimed_performance=(
                    PerformanceMetric(
                        metric=PerformanceMetricType.SENSITIVITY,
                        value=0.985,
                        variant_type=VariantType.SNV,
                        confidence_interval=ConfidenceInterval(lower=0.97, upper=0.995),
                        evidence_reference="VAL-2025-SNV-12",
                    ),
                ),
                depends_on_categories=(
                    ComponentCategory.ALIGNER,
                    ComponentCategory.VARIANT_CALLER,
                    ComponentCategory.REFERENCE_GENOME,
                ),
                depends_on_components=("variant_caller:mutect2",),
                evidence_references=("VAL-2025-SNV-12",),
            ),
            AssayClaim(
                claim_id="CLAIM-INDEL-001",
                claim_type=ClaimType.INDEL_DETECTION,
                title="Indel detection sensitivity at >=5% VAF",
                variant_types=(VariantType.INDEL,),
                genomic_scope="panel target regions",
                claimed_performance=(
                    PerformanceMetric(
                        metric=PerformanceMetricType.SENSITIVITY,
                        value=0.94,
                        variant_type=VariantType.INDEL,
                    ),
                ),
                depends_on_categories=(
                    ComponentCategory.ALIGNER,
                    ComponentCategory.VARIANT_CALLER,
                    ComponentCategory.REFERENCE_GENOME,
                ),
            ),
            AssayClaim(
                claim_id="CLAIM-CNV-001",
                claim_type=ClaimType.CNV_DETECTION,
                title="Gene-level copy-number gain detection",
                variant_types=(VariantType.CNV,),
                depends_on_categories=(ComponentCategory.CNV_CALLER,),
                depends_on_components=("cnv_caller:cnvkit",),
            ),
            AssayClaim(
                claim_id="CLAIM-CLASS-001",
                claim_type=ClaimType.VARIANT_CLASSIFICATION_CONSISTENCY,
                title="Clinical classification consistency across annotation updates",
                depends_on_categories=(
                    ComponentCategory.ANNOTATION,
                    ComponentCategory.TRANSCRIPT_SET,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    out = Path(__file__).parent
    m = build()
    dump_manifest(m, out / "manifest.json")
    dump_manifest(m, out / "manifest.yaml")
    print("content sha256:", m.content_hash())
    print("wrote manifest.json and manifest.yaml")
