"""Builds a realistic germline hereditary-cancer panel manifest example.

Used by the web demo's Sample Manifest Library as the germline counterpart to
``examples.build`` (somatic). Run from the repo root:
`python -m examples.build_germline`.
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
    h = "d" * 64

    return AssayManifest(
        manifest_id=UUID("22222222-2222-2222-2222-222222222222"),
        generated_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
        generated_by="ci-pipeline@lab.example",
        status="validated",
        change_reason="Initial validated baseline for HereditaryCancer76 v1.4.",
        tags=("germline", "hereditary_cancer"),
        assay=AssayMetadata(
            assay_name="HereditaryCancer76",
            assay_version="1.4.0",
            assay_type=AssayType.GERMLINE,
            intended_use=IntendedUse.DIAGNOSTIC,
            laboratory_name="Example Molecular Diagnostics Lab",
            laboratory_id="99D9999999",
            regulatory_contexts=(RegulatoryContext.CLIA_LDT, RegulatoryContext.CAP_ACCREDITED),
            specimen_types=("Blood", "Saliva"),
        ),
        pipeline=PipelineMetadata(
            pipeline_name="germline-hc-wf",
            pipeline_version="1.4.0",
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
                    name="gnomAD",
                    version="4.1",
                    source="Broad gnomAD",
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
                name="HaplotypeCaller",
                version="4.5.0.0",
                vendor="GATK",
                parameters={"mode": "germline", "min_base_quality_score": 20},
            ),
            additional_components=(
                SoftwareComponent(
                    category=ComponentCategory.VARIANT_FILTER,
                    name="VariantFiltration",
                    version="4.5.0.0",
                    vendor="GATK",
                ),
            ),
        ),
        assay_scope=AssayScope(
            sequencing_scope=SequencingScope.TARGETED_PANEL,
            panel_name="HereditaryCancer76",
            panel_version="1.4",
            bed_file=FileResource(
                path="assets/hereditarycancer76_v1.4.targets.bed",
                checksum=sha("e" * 64),
                line_count=5120,
            ),
            target_regions_hash=sha("e" * 64),
        ),
        qc=QCConfiguration(
            thresholds=(
                QCThreshold(
                    metric="minimum_coverage",
                    comparator=Comparator.GE,
                    threshold=100,
                    unit="x",
                    severity=QCSeverity.BLOCKING,
                ),
                QCThreshold(
                    metric="callable_fraction",
                    comparator=Comparator.GE,
                    threshold=0.98,
                    unit="fraction",
                    severity=QCSeverity.BLOCKING,
                ),
            )
        ),
        environment=Environment(
            container_runtime=ContainerRuntime.DOCKER,
            container_image="registry.example.com/lab/germline-hc",
            container_version="1.4.0",
            image_digest=sha("f" * 64),
            git_commit="3a7d004",
            build_date=date(2026, 1, 10),
        ),
        claims=(
            AssayClaim(
                claim_id="CLAIM-SNV-001",
                claim_type=ClaimType.SNV_DETECTION,
                title="Germline SNV detection sensitivity",
                variant_types=(VariantType.SNV,),
                genomic_scope="panel target regions",
                claimed_performance=(
                    PerformanceMetric(
                        metric=PerformanceMetricType.SENSITIVITY,
                        value=0.995,
                        variant_type=VariantType.SNV,
                        confidence_interval=ConfidenceInterval(lower=0.99, upper=0.999),
                        evidence_reference="VAL-2025-GL-SNV-04",
                    ),
                ),
                depends_on_categories=(
                    ComponentCategory.ALIGNER,
                    ComponentCategory.VARIANT_CALLER,
                    ComponentCategory.REFERENCE_GENOME,
                ),
                depends_on_components=("variant_caller:haplotypecaller",),
                evidence_references=("VAL-2025-GL-SNV-04",),
            ),
            AssayClaim(
                claim_id="CLAIM-INDEL-001",
                claim_type=ClaimType.INDEL_DETECTION,
                title="Germline indel detection sensitivity",
                variant_types=(VariantType.INDEL,),
                genomic_scope="panel target regions",
                depends_on_categories=(
                    ComponentCategory.ALIGNER,
                    ComponentCategory.VARIANT_CALLER,
                    ComponentCategory.REFERENCE_GENOME,
                ),
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


if __name__ == "__main__":  # pragma: no cover
    out = Path(__file__).parent
    m = build()
    dump_manifest(m, out / "manifest_germline.json")
    print("content sha256:", m.content_hash())
    print("wrote manifest_germline.json")
