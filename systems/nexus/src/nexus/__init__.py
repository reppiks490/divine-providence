"""NEXUS Adaptive Market Fabric."""
from .contracts import StreamIdentity, StreamManifest, BarEvent, QualityFlag, DataPlane, ReplayInstant
from .catalog import CorpusCatalog
from .replay import ReplayBus
from .synthetic import AdaptiveTickerEngine, SyntheticTickerDefinition
from .topology import RollingTopology
from .change import ChangePointEngine

__all__ = [
    "StreamIdentity", "StreamManifest", "BarEvent", "QualityFlag", "DataPlane", "ReplayInstant",
    "CorpusCatalog", "ReplayBus", "AdaptiveTickerEngine", "SyntheticTickerDefinition",
    "RollingTopology", "ChangePointEngine", "CausalPCAFactor", "LatentFactorPoint",
    "RepresentationConsensus", "robust_representation_consensus",
    "RollingMahalanobisOOD", "KernelShiftSensor", "ReplayCheckpoint",
    "VectorEvent", "VectorStatePacket", "VectorReplayBus", "iter_numeric_events",
    "IntegrityPolicy", "IntegrityAssessment", "assess_manifest", "partition_by_integrity",
    "MultiResolutionClockLattice", "LatticeStream",
    "HierarchicalFactorEngine", "HierarchicalFusionResult", "fuse_representations_by_symbol",
    "UniverseDecision", "build_factor_universe",
    "CausalityAudit", "CausalityViolation", "audit_prefix_invariance", "audit_event_availability",
    "DerivationRecord",
    "SourceSLOPolicy", "SourceHealthSnapshot", "SourceHealthTracker", "SourceHealthPlane", "SourceHealthRegistry",
    "SiblingInstantBundle", "SiblingInstantRouter",
    "TransformSpec", "CausalityCertificate", "CausalTransformRegistry",
    "ReviewedRepresentationRecord", "ReviewedRepresentationRegistry",
    "FactorGenealogySnapshot", "ResearchRunManifest",
    "BoundaryFileFingerprint", "ContractDriftSnapshot", "ContractDriftItem", "ContractDriftReport", "compare_contract_snapshots",
    "RepresentationReviewCandidate", "RepresentationReviewQueue", "build_representation_review_queue",
]
__version__ = "0.3.0"

from .latent import CausalPCAFactor, LatentFactorPoint
from .representation import RepresentationConsensus, robust_representation_consensus
from .ood import RollingMahalanobisOOD, KernelShiftSensor
from .checkpoint import ReplayCheckpoint

from .contracts import VectorEvent, VectorStatePacket
from .tabular import iter_numeric_events
from .vector_replay import VectorReplayBus

from .integrity import IntegrityPolicy, IntegrityAssessment, assess_manifest, partition_by_integrity
from .lattice import MultiResolutionClockLattice, LatticeStream
from .hierarchy import HierarchicalFactorEngine, HierarchicalFusionResult, fuse_representations_by_symbol
from .universe import UniverseDecision, build_factor_universe
from .causality import CausalityAudit, CausalityViolation, audit_prefix_invariance, audit_event_availability
from .lineage import DerivationRecord

from .source_health import SourceSLOPolicy, SourceHealthSnapshot, SourceHealthTracker, SourceHealthPlane, SourceHealthRegistry
from .sibling_replay import SiblingInstantBundle, SiblingInstantRouter

from .promotion import TransformSpec, CausalityCertificate, CausalTransformRegistry

from .review_registry import ReviewedRepresentationRecord, ReviewedRepresentationRegistry

from .run_manifest import FactorGenealogySnapshot, ResearchRunManifest

from .contract_sentinel import BoundaryFileFingerprint, ContractDriftSnapshot, ContractDriftItem, ContractDriftReport, compare_contract_snapshots

from .review_queue import RepresentationReviewCandidate, RepresentationReviewQueue, build_representation_review_queue
