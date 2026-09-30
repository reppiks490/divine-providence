from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import zipfile

from .archive import ZipCorpusCatalog
from .contracts import StreamManifest
from .integrity import IntegrityPolicy, assess_manifest
from .quality import quality_score
from .review_queue import build_representation_review_queue
from .universe import build_factor_universe
from .validation_handoff import build_daedalus_validation_handoff
from .lineage_resolution import build_representation_lineage_resolution
from .session_semantics import build_session_gap_resolution, build_session_semantic_blocker_report
from .residual_gap_triage import build_residual_gap_triage
from .review_triage import build_representation_review_triage
from .representation_evidence import build_representation_source_evidence
from .representation_attestation import build_representation_attestation_status
from .corpus_recovery import HistoricalCorpusAnchor, build_corpus_recovery_plan


LOOP_SCHEMA = "nexus.advanced-csv-research-loop.v1"
LOOP_CODE_VERSION = "1.20.0"

CORE_ARTIFACT_NAMES = (
    "corpus_manifest.json",
    "integrity_report.json",
    "factor_universe.json",
    "representation_review_queue.json",
    "stream_descriptive_sweep.json",
    "research_queue.json",
    "representation_lineage_resolution.json",
    "session_gap_resolution.json",
    "session_semantics_blockers.json",
    "residual_gap_triage.json",
    "representation_review_triage.json",
    "representation_source_evidence.json",
    "representation_attestation_status.json",
    "corpus_recovery_plan.json",
)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _is_sha256(value: Any) -> bool:
    if not isinstance(value,str) or len(value)!=64:
        return False
    try:
        int(value,16)
    except ValueError:
        return False
    return True


def _path_within(root: Path, relative: str) -> Path:
    p=Path(relative)
    if p.is_absolute():
        raise ValueError("state artifact paths must be relative")
    root_resolved=root.resolve()
    candidate=(root/p).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("state artifact path escapes state_dir")
    return candidate


def _candidate_ids(payload: dict[str, Any] | None) -> set[str]:
    if not payload:
        return set()
    out: set[str] = set()
    for row in payload.get("candidates", []):
        if isinstance(row, dict) and row.get("candidate_id"):
            out.add(str(row["candidate_id"]))
    return out


def _review_ids(payload: dict[str, Any] | None) -> set[str]:
    if not payload:
        return set()
    out: set[str] = set()
    for row in payload.get("candidates", []):
        if isinstance(row, dict) and row.get("stream_id"):
            out.add(str(row["stream_id"]))
    return out


def _counter_from_candidates(rows: Iterable[ResearchCandidate], field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = getattr(row, field, None)
        if value is not None:
            counter[str(value)] += 1
    return dict(sorted(counter.items()))


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _corr_from_sums(n: int, sx: float, sy: float, sxx: float, syy: float, sxy: float) -> float | None:
    if n < 3:
        return None
    vx = n * sxx - sx * sx
    vy = n * syy - sy * sy
    if vx <= 0.0 or vy <= 0.0:
        return None
    return max(-1.0, min(1.0, (n * sxy - sx * sy) / math.sqrt(vx * vy)))


@dataclass(frozen=True, slots=True)
class CoverageAnchor:
    name: str
    usable_entries: int
    usable_rows: int


@dataclass(frozen=True, slots=True)
class AdvancedLoopConfig:
    state_dir: str
    prior_anchor: CoverageAnchor = CoverageAnchor("PARALLAX_TEN_ARCHIVE_CHECKPOINT", 659, 13_788_256)
    min_owner_expected_entries: int = 659
    owner_expected_physical_entries: int = 803
    excluded_model_symbols: tuple[str, ...] = (
        "ETHUSD", "ETHUSDT", "ETH1!",
        "SOLUSD", "SOLUSDT", "SOL1!",
        "MBT", "MBT1!",
    )
    max_candidates_per_family: int = 100
    min_returns_for_behavior_candidate: int = 200
    persistence_abs_threshold: float = 0.15
    regime_vol_ratio_threshold: float = 2.0


@dataclass(frozen=True, slots=True)
class StreamSweep:
    stream_id: str
    symbol: str
    venue: str | None
    source_path: str
    row_count: int
    usable_close_rows: int
    return_count: int
    mean_log_return: float | None
    std_log_return: float | None
    lag1_return_corr: float | None
    sign_persistence: float | None
    efficiency_ratio: float | None
    mean_range_fraction: float | None
    gap_rate: float | None
    first_half_return_std: float | None
    second_half_return_std: float | None
    regime_vol_ratio: float | None
    volume_nonmissing_fraction: float | None
    quality_score: float
    admitted: bool
    descriptive_only: bool = True
    production_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResearchCandidate:
    candidate_id: str
    family: str
    priority: str
    score: float
    scope: tuple[str, ...]
    rationale: str
    required_next_test: str
    descriptive_only: bool = True
    production_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scope"] = list(self.scope)
        return d


@dataclass(frozen=True, slots=True)
class LoopResult:
    iteration: int
    corpus_manifest_hash: str
    iteration_hash: str
    summary_path: str
    state_path: str
    artifact_paths: tuple[str, ...]
    summary: dict[str, Any]


def _variance(n: int, s: float, ss: float) -> float | None:
    if n < 2:
        return None
    v = (ss - (s * s) / n) / (n - 1)
    return max(0.0, v)


def _std(n: int, s: float, ss: float) -> float | None:
    v = _variance(n, s, ss)
    return None if v is None else math.sqrt(v)


def _sweep_member(zf: zipfile.ZipFile, manifest: StreamManifest, admitted: bool) -> StreamSweep:
    member = str(manifest.metadata.get("archive_member") or "")
    if not member:
        raise ValueError(f"archive member missing for {manifest.identity.source_path}")
    rows = max(0, int(manifest.row_count))
    split_row = max(1, rows // 2)

    nret = 0
    sr = srr = 0.0
    lag_n = 0
    lag_sx = lag_sy = lag_sxx = lag_syy = lag_sxy = 0.0
    prev_ret: float | None = None
    prev_close: float | None = None
    first_close: float | None = None
    last_close: float | None = None
    abs_path = 0.0
    sign_pairs = sign_same = 0
    prev_sign = 0
    range_sum = 0.0
    range_n = 0
    gap_count = time_diff_count = 0
    prev_time: float | None = None
    cadence_s = (manifest.observed_cadence_ns / 1e9) if manifest.observed_cadence_ns else None
    vol_present = vol_nonmissing = 0
    usable_close = 0

    h1_n = h2_n = 0
    h1_s = h1_ss = h2_s = h2_ss = 0.0

    with zf.open(member, "r") as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = next(reader, [])
        lower = [str(x).strip().lower() for x in header]
        idx = {k: next((i for i, c in enumerate(lower) if c == k), None) for k in ("time", "open", "high", "low", "close", "volume")}
        if idx["close"] is None:
            return StreamSweep(manifest.identity.stream_id, manifest.identity.symbol, manifest.identity.venue, manifest.identity.source_path,
                               manifest.row_count, 0, 0, None, None, None, None, None, None, None, None, None, None, None,
                               quality_score(manifest), admitted)

        logical_row = 0
        for row in reader:
            if not row:
                continue
            ci = idx["close"]
            if ci is None or ci >= len(row):
                continue
            close = _safe_float(row[ci])
            if close is None or close <= 0.0:
                continue
            logical_row += 1
            usable_close += 1
            if first_close is None:
                first_close = close
            last_close = close

            if idx["high"] is not None and idx["low"] is not None and idx["high"] < len(row) and idx["low"] < len(row):
                high = _safe_float(row[idx["high"]])
                low = _safe_float(row[idx["low"]])
                if high is not None and low is not None and close != 0.0 and high >= low:
                    range_sum += (high - low) / abs(close)
                    range_n += 1

            if idx["volume"] is not None:
                vol_present += 1
                vi = idx["volume"]
                if vi < len(row) and row[vi].strip() != "" and _safe_float(row[vi]) is not None:
                    vol_nonmissing += 1

            if idx["time"] is not None and idx["time"] < len(row):
                t = _safe_float(row[idx["time"]])
                if t is not None and prev_time is not None and t > prev_time:
                    dt = t - prev_time
                    time_diff_count += 1
                    if cadence_s and dt > cadence_s * 1.5:
                        gap_count += 1
                if t is not None:
                    prev_time = t

            if prev_close is not None and prev_close > 0.0:
                r = math.log(close / prev_close)
                if math.isfinite(r):
                    nret += 1
                    sr += r
                    srr += r * r
                    abs_path += abs(r)
                    if logical_row <= split_row:
                        h1_n += 1; h1_s += r; h1_ss += r * r
                    else:
                        h2_n += 1; h2_s += r; h2_ss += r * r
                    sign = 1 if r > 0 else (-1 if r < 0 else 0)
                    if sign and prev_sign:
                        sign_pairs += 1
                        sign_same += int(sign == prev_sign)
                    if sign:
                        prev_sign = sign
                    if prev_ret is not None:
                        lag_n += 1
                        lag_sx += prev_ret; lag_sy += r
                        lag_sxx += prev_ret * prev_ret; lag_syy += r * r; lag_sxy += prev_ret * r
                    prev_ret = r
            prev_close = close

    mean_r = sr / nret if nret else None
    std_r = _std(nret, sr, srr)
    lag_corr = _corr_from_sums(lag_n, lag_sx, lag_sy, lag_sxx, lag_syy, lag_sxy)
    sign_persist = (sign_same / sign_pairs) if sign_pairs else None
    efficiency = None
    if first_close and last_close and first_close > 0 and last_close > 0 and abs_path > 0:
        efficiency = min(1.0, abs(math.log(last_close / first_close)) / abs_path)
    h1_std = _std(h1_n, h1_s, h1_ss)
    h2_std = _std(h2_n, h2_s, h2_ss)
    ratio = None
    if h1_std is not None and h2_std is not None and h1_std > 0 and h2_std > 0:
        ratio = max(h1_std, h2_std) / min(h1_std, h2_std)

    return StreamSweep(
        stream_id=manifest.identity.stream_id,
        symbol=manifest.identity.symbol,
        venue=manifest.identity.venue,
        source_path=manifest.identity.source_path,
        row_count=manifest.row_count,
        usable_close_rows=usable_close,
        return_count=nret,
        mean_log_return=mean_r,
        std_log_return=std_r,
        lag1_return_corr=lag_corr,
        sign_persistence=sign_persist,
        efficiency_ratio=efficiency,
        mean_range_fraction=(range_sum / range_n) if range_n else None,
        gap_rate=(gap_count / time_diff_count) if time_diff_count else None,
        first_half_return_std=h1_std,
        second_half_return_std=h2_std,
        regime_vol_ratio=ratio,
        volume_nonmissing_fraction=(vol_nonmissing / vol_present) if vol_present else None,
        quality_score=quality_score(manifest),
        admitted=admitted,
    )


def _candidate_id(family: str, scope: Iterable[str], rationale: str) -> str:
    return hashlib.sha256(_json_bytes({"family": family, "scope": sorted(scope), "rationale": rationale})).hexdigest()[:20]


def _build_candidates(
    manifests: list[StreamManifest],
    sweeps: list[StreamSweep],
    *,
    config: AdvancedLoopConfig,
    usable_entries: int,
    usable_rows: int,
    admitted_count: int,
    review_counts: Counter[str],
) -> list[ResearchCandidate]:
    out: list[ResearchCandidate] = []

    def add(family: str, priority: str, score: float, scope: Iterable[str], rationale: str, next_test: str) -> None:
        scope_t = tuple(sorted(str(x) for x in scope))
        out.append(ResearchCandidate(_candidate_id(family, scope_t, rationale), family, priority, float(score), scope_t, rationale, next_test))

    anchor = config.prior_anchor
    if usable_entries < anchor.usable_entries or usable_rows < anchor.usable_rows:
        add(
            "corpus_recovery", "P0", 1000.0,
            ["corpus"],
            f"Accessible corpus has {usable_entries} usable streams/{usable_rows} rows versus {anchor.name} {anchor.usable_entries}/{anchor.usable_rows}.",
            "Recover additional archives by hash and reconcile every member against prior manifests before any full-coverage claim.",
        )
    if usable_entries < config.min_owner_expected_entries:
        add(
            "owner_coverage_gap", "P0", 950.0,
            ["corpus"],
            f"Usable stream count {usable_entries} is below owner expectation of roughly {config.min_owner_expected_entries}+ files/streams.",
            "Locate remaining batches/archives and update the content-addressed corpus reconciliation report.",
        )
    if review_counts.get("P0", 0):
        add(
            "representation_review", "P0", 900.0 + review_counts["P0"],
            ["representation_registry"],
            f"{review_counts['P0']} streams require P0 representation/timestamp/identity review.",
            "Attach source/vendor evidence for representation type, timestamp semantics, timezone/session and volume semantics; keep unknowns blocked.",
        )
    rejected = max(0, usable_entries - admitted_count)
    if rejected:
        add(
            "integrity_rejections", "P0", 800.0 + rejected,
            ["integrity_gate"],
            f"{rejected} usable streams are withheld by the default NEXUS integrity policy.",
            "Triage blockers by source; repair evidence/contracts rather than weakening the integrity gate globally.",
        )

    manifest_by_id = {m.identity.stream_id: m for m in manifests}

    for s in sweeps:
        if s.return_count < config.min_returns_for_behavior_candidate or not s.admitted:
            continue
        if s.lag1_return_corr is not None and abs(s.lag1_return_corr) >= config.persistence_abs_threshold:
            family = "return_persistence" if s.lag1_return_corr > 0 else "return_reversal"
            add(
                family, "P1", 100.0 + abs(s.lag1_return_corr) * 100.0,
                [s.stream_id],
                f"Descriptive lag-1 log-return correlation is {s.lag1_return_corr:.4f} over {s.return_count} returns for {s.symbol}.",
                "Send to DAEDALUS for chronological walk-forward validation with multiple-testing control; do not promote from this descriptive statistic.",
            )
        if s.regime_vol_ratio is not None and s.regime_vol_ratio >= config.regime_vol_ratio_threshold:
            add(
                "regime_volatility_shift", "P1", 90.0 + min(100.0, s.regime_vol_ratio * 10.0),
                [s.stream_id],
                f"First-half vs second-half return-volatility ratio is {s.regime_vol_ratio:.3f} for {s.symbol}.",
                "Test expanding/rolling volatility-state segmentation chronologically and verify stability on held-out periods.",
            )
        if s.gap_rate is not None and s.gap_rate >= 0.05:
            manifest = manifest_by_id.get(s.stream_id)
            hypothesis = (manifest.metadata.get("representation_hypothesis", {}) if manifest else {})
            # Gap-rate semantics require a fixed-time representation. Event/transformed
            # streams can be irregular by construction; applying an inferred cadence to
            # them manufactures false "missing interval" candidates. Keep those streams
            # in representation review instead of treating irregularity as data loss.
            if hypothesis.get("kind") == "fixed_time_candidate":
                add(
                    "sampling_gap_sensitivity", "P1", 80.0 + s.gap_rate * 100.0,
                    [s.stream_id],
                    f"Observed positive timestamp gaps exceed 1.5x inferred cadence on {s.gap_rate:.2%} of comparable intervals for {s.symbol}.",
                    "Separate session/calendar gaps from data loss before using fixed-cadence transforms or alignment.",
                )

    # Representation disagreement candidates: compare same symbol + filename claim without treating copies as votes.
    groups: dict[tuple[str, str | None], list[StreamSweep]] = defaultdict(list)
    for s in sweeps:
        m = manifest_by_id.get(s.stream_id)
        if m and s.admitted and s.std_log_return is not None:
            groups[(s.symbol, m.identity.filename_claim)].append(s)
    for (symbol, claim), group in groups.items():
        vals = [s.std_log_return for s in group if s.std_log_return is not None and s.std_log_return > 0]
        if len(vals) < 2:
            continue
        dispersion = max(vals) / min(vals)
        if dispersion >= 1.5:
            scope = [s.stream_id for s in group]
            add(
                "representation_family_disagreement", "P1", 120.0 + min(200.0, dispersion * 20.0),
                scope,
                f"{symbol} claim={claim or '?'} has {len(group)} admitted representations with return-volatility dispersion ratio {dispersion:.3f}.",
                "Resolve representation identity/copy lineage, then compare causally aligned views before any symbol-level fusion.",
            )

    # Deduplicate and cap noisy families deterministically.
    dedup: dict[str, ResearchCandidate] = {}
    for c in out:
        old = dedup.get(c.candidate_id)
        if old is None or (c.score, c.priority) > (old.score, old.priority):
            dedup[c.candidate_id] = c
    buckets: dict[str, list[ResearchCandidate]] = defaultdict(list)
    for c in dedup.values():
        buckets[c.family].append(c)
    final: list[ResearchCandidate] = []
    p_rank = {"P0": 0, "P1": 1, "P2": 2}
    for family in sorted(buckets):
        rows = sorted(buckets[family], key=lambda c: (p_rank.get(c.priority, 9), -c.score, c.candidate_id))
        final.extend(rows[: max(1, int(config.max_candidates_per_family))])
    return sorted(final, key=lambda c: (p_rank.get(c.priority, 9), -c.score, c.family, c.candidate_id))


class AdvancedCSVResearchLoop:
    """Resumable orchestration loop over the CSV/ZIP corpus.

    This layer deliberately generates research candidates only. It does not infer
    authoritative bar timestamp semantics, bypass NEXUS integrity gates, perform
    statistical promotion, or authorize execution.
    """

    def __init__(self, corpus_root: str | Path, config: AdvancedLoopConfig):
        self.corpus_root = Path(corpus_root)
        self.config = config
        self.state_dir = Path(config.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _state_path(self) -> Path:
        return self.state_dir / "loop_state.json"

    def _load_previous_state(self) -> dict[str, Any] | None:
        if not self._state_path.exists():
            return None
        try:
            state=json.loads(self._state_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("loop_state.json exists but is unreadable") from exc
        if not isinstance(state,dict):
            raise RuntimeError("loop_state.json must contain an object")

        supplied_state_hash=state.get("state_hash")
        if supplied_state_hash is not None:
            if not _is_sha256(supplied_state_hash):
                raise RuntimeError("loop state_hash is invalid")
            state_body=dict(state);state_body.pop("state_hash",None)
            if _digest(state_body)!=supplied_state_hash:
                raise RuntimeError("loop state_hash mismatch")

        if (
            state.get("schema") != LOOP_SCHEMA
            or state.get("status") != "completed"
            or state.get("production_authorized") is not False
            or type(state.get("iteration")) is not int
            or state["iteration"] < 1
            or not _is_sha256(state.get("iteration_hash"))
            or not _is_sha256(state.get("corpus_manifest_hash"))
            or not isinstance(state.get("artifact_hashes"),dict)
        ):
            raise RuntimeError("loop state failed semantic validation")

        summary_rel=state.get("latest_summary_path")
        if not isinstance(summary_rel,str) or not summary_rel:
            raise RuntimeError("loop state is missing latest_summary_path")
        try:
            summary_path=_path_within(self.state_dir,summary_rel)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        summary=_read_json(summary_path)
        if summary is None:
            raise RuntimeError("referenced previous iteration summary is missing/unreadable")
        supplied_iteration_hash=summary.get("iteration_hash")
        if not _is_sha256(supplied_iteration_hash):
            raise RuntimeError("previous iteration summary hash is invalid")
        summary_body=dict(summary);summary_body.pop("iteration_hash",None)
        if _digest(summary_body)!=supplied_iteration_hash:
            raise RuntimeError("previous iteration summary hash mismatch")
        if (
            supplied_iteration_hash != state["iteration_hash"]
            or summary.get("schema") != LOOP_SCHEMA
            or summary.get("iteration") != state["iteration"]
            or summary.get("loop_code_version") != state.get("loop_code_version")
            or summary.get("corpus_manifest_hash") != state["corpus_manifest_hash"]
            or summary.get("artifact_hashes") != state["artifact_hashes"]
            or summary.get("production_authorized") is not False
        ):
            raise RuntimeError("loop state and previous summary disagree")

        iteration_dir=summary_path.parent
        for name,expected in state["artifact_hashes"].items():
            if not isinstance(name,str) or not name or not _is_sha256(expected):
                raise RuntimeError("loop state contains invalid artifact hash metadata")
            artifact_path=iteration_dir/name
            payload=_read_json(artifact_path)
            if payload is None or _digest(payload)!=expected:
                raise RuntimeError(f"previous artifact failed hash verification: {name}")

        # Legacy state files without state_hash are accepted only after the full
        # summary/artifact verification above. The next successful run migrates
        # them to a sealed state automatically.
        return state

    def _sweep_all(self, manifests: list[StreamManifest], admitted_ids: set[str]) -> list[StreamSweep]:
        by_archive: dict[str, list[StreamManifest]] = defaultdict(list)
        for m in manifests:
            if m.row_count <= 0 or "appledouble" in m.quality_flags:
                continue
            archive_rel = str(m.metadata.get("archive_path") or "")
            if archive_rel:
                by_archive[archive_rel].append(m)
        out: list[StreamSweep] = []
        for archive_rel in sorted(by_archive):
            archive = self.corpus_root / archive_rel
            with zipfile.ZipFile(archive) as zf:
                for m in sorted(by_archive[archive_rel], key=lambda x: x.identity.source_path):
                    out.append(_sweep_member(zf, m, m.identity.stream_id in admitted_ids))
        return out

    def run_once(self) -> LoopResult:
        previous = self._load_previous_state()
        iteration = int(previous.get("iteration", 0)) + 1 if previous else 1

        manifests = ZipCorpusCatalog(self.corpus_root).build()
        # stream_id intentionally uses a compact raw-hash prefix for readability.
        # Fail closed before producing any artifact if that prefix collides across
        # different raw contents.
        stream_hashes:dict[str,str]={}
        for m in manifests:
            sid=m.identity.stream_id
            prior_raw_sha=stream_hashes.get(sid)
            if prior_raw_sha is not None and prior_raw_sha != m.identity.raw_sha256:
                raise RuntimeError(
                    f"stream_id collision across distinct raw contents: {sid}"
                )
            stream_hashes[sid]=m.identity.raw_sha256
        # ZIP-native cataloging preserves the raw forensic pass. Attach the same
        # non-authoritative representation hypotheses used by extracted catalogs
        # before integrity/review triage so both paths produce equivalent queues.
        from .representation import infer_representation_claim, infer_representation_hypothesis
        for m in manifests:
            if m.row_count <= 0 or "appledouble" in m.quality_flags:
                continue
            if "representation_claim" not in m.metadata:
                rep = infer_representation_claim(m)
                m.metadata["representation_claim"] = rep.to_dict()
            if "representation_hypothesis" not in m.metadata:
                hyp = infer_representation_hypothesis(m)
                m.metadata["representation_hypothesis"] = {
                    "kind": hyp.kind, "confidence": hyp.confidence,
                    "reasons": list(hyp.reasons), "authoritative": False,
                }
        manifest_payload = [m.to_dict() for m in manifests]
        corpus_manifest_hash = _digest(manifest_payload)
        usable = [m for m in manifests if m.row_count > 0 and "appledouble" not in m.quality_flags]
        usable_rows = sum(int(m.row_count) for m in usable)

        assessments = [assess_manifest(m, IntegrityPolicy()) for m in manifests]
        admitted_ids = {a.stream_id for a in assessments if a.admitted}
        excluded_model_symbols = {x.upper() for x in self.config.excluded_model_symbols}
        excluded_model_ids = {
            m.identity.stream_id for m in manifests
            if m.identity.symbol.upper() in excluded_model_symbols
        }
        model_admitted_ids = admitted_ids - excluded_model_ids
        admitted_count = sum(1 for m in usable if m.identity.stream_id in admitted_ids)
        model_admitted_count = sum(1 for m in usable if m.identity.stream_id in model_admitted_ids)
        rejected = [a.to_dict() for a in assessments if not a.admitted]
        selected_universe, universe_decisions = build_factor_universe(
            manifests, excluded_symbols=self.config.excluded_model_symbols
        )

        review_queue = build_representation_review_queue(manifests)
        review_counts = Counter(c.priority for c in review_queue.candidates)
        representation_review_triage = build_representation_review_triage(review_queue.to_dict())
        representation_source_evidence = build_representation_source_evidence(representation_review_triage)
        attestation_input_path = self.state_dir / "representation_attestations.json"
        representation_attestation_status = build_representation_attestation_status(
            manifests, review_queue.to_dict(), _read_json(attestation_input_path) if attestation_input_path.exists() else None
        )
        if self.config.prior_anchor.name == "PARALLAX_TEN_ARCHIVE_CHECKPOINT":
            historical_distinct, historical_archives = 542, 10
        elif self.config.prior_anchor.name == "AION_PRIOR_CHECKPOINT":
            historical_distinct, historical_archives = 513, 9
        else:
            historical_distinct, historical_archives = None, None
        recovery_anchor = HistoricalCorpusAnchor(
            usable_entries=self.config.prior_anchor.usable_entries,
            usable_rows=self.config.prior_anchor.usable_rows,
            distinct_byte_contents=historical_distinct,
            archive_count=historical_archives,
            label=self.config.prior_anchor.name,
        )
        corpus_recovery_plan = build_corpus_recovery_plan(
            manifests, recovery_anchor, owner_expected_min_entries=self.config.min_owner_expected_entries
        )

        sweeps = self._sweep_all(manifests, model_admitted_ids)
        candidates = _build_candidates(
            manifests, sweeps, config=self.config, usable_entries=len(usable), usable_rows=usable_rows,
            admitted_count=model_admitted_count, review_counts=review_counts,
        )
        representation_lineage_resolution = build_representation_lineage_resolution(
            self.corpus_root, manifests, candidates
        )
        session_gap_resolution = build_session_gap_resolution(
            self.corpus_root, manifests, candidates
        )
        session_semantics_blockers = build_session_semantic_blocker_report(session_gap_resolution)
        residual_gap_triage = build_residual_gap_triage(
            self.corpus_root, manifests, session_gap_resolution
        )

        flags = Counter(flag for m in usable for flag in m.quality_flags)
        symbols = Counter(m.identity.symbol for m in usable)
        venues = Counter((m.identity.venue or "?") for m in usable)
        claims = Counter((m.identity.filename_claim or "?") for m in usable)
        representation_families = Counter(
            str(m.metadata.get("representation_claim", {}).get("family", "unknown")) for m in usable
        )
        price_geometries = Counter(
            str(m.metadata.get("representation_claim", {}).get("price_geometry", "unknown")) for m in usable
        )
        sampling_domains = Counter(
            str(m.metadata.get("representation_claim", {}).get("sampling_domain", "unknown")) for m in usable
        )
        sampling_constructions = Counter(
            str(m.metadata.get("representation_claim", {}).get("construction", "unknown")) for m in usable
        )
        prior_hash = previous.get("corpus_manifest_hash") if previous else None
        delta = {
            "previous_iteration": previous.get("iteration") if previous else None,
            "corpus_changed": bool(previous and prior_hash != corpus_manifest_hash),
            "previous_corpus_manifest_hash": prior_hash,
            "current_corpus_manifest_hash": corpus_manifest_hash,
            "previous_loop_code_version": previous.get("loop_code_version") if previous else None,
            "current_loop_code_version": LOOP_CODE_VERSION,
            "loop_code_changed": bool(previous and previous.get("loop_code_version") != LOOP_CODE_VERSION),
        }

        summary = {
            "schema": LOOP_SCHEMA,
            "loop_code_version": LOOP_CODE_VERSION,
            "iteration": iteration,
            "historical_checkpoint_reconciled": bool(
                corpus_recovery_plan["acceptance"]["historical_anchor_reconciled"]
            ),
            "coverage_claim_allowed": False,
            "coverage_claim_reason": "Historical count/hash reconciliation does not by itself prove semantic matrix completeness; require reviewed identity/session/contract coverage.",
            "physical_csv_entries": len(manifests),
            "usable_entries": len(usable),
            "usable_rows": usable_rows,
            "admitted_entries_default_integrity": admitted_count,
            "model_admitted_entries_after_owner_exclusions": model_admitted_count,
            "owner_excluded_model_symbols": list(self.config.excluded_model_symbols),
            "owner_excluded_stream_count": len(excluded_model_ids),
            "withheld_usable_entries_default_integrity": len(usable) - admitted_count,
            "factor_universe_streams": len(selected_universe),
            "representation_review_counts": dict(sorted(review_counts.items())),
            "research_candidate_count": len(candidates),
            "quality_flag_counts": dict(sorted(flags.items())),
            "symbol_counts": dict(sorted(symbols.items())),
            "venue_counts": dict(sorted(venues.items())),
            "filename_claim_counts": dict(sorted(claims.items())),
            "representation_family_counts": dict(sorted(representation_families.items())),
            "price_geometry_counts": dict(sorted(price_geometries.items())),
            "sampling_domain_counts": dict(sorted(sampling_domains.items())),
            "sampling_construction_counts": dict(sorted(sampling_constructions.items())),
            "prior_anchor": asdict(self.config.prior_anchor),
            "owner_expected_min_entries": self.config.min_owner_expected_entries,
            "owner_expected_physical_entries": self.config.owner_expected_physical_entries,
            "delta": delta,
            "descriptive_only": True,
            "statistical_promotion_performed": False,
            "production_authorized": False,
        }

        iter_dir = self.state_dir / f"iteration_{iteration:04d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        validation_handoff = build_daedalus_validation_handoff(
            manifests, candidates, admitted_ids=model_admitted_ids, corpus_manifest_hash=corpus_manifest_hash,
            source_iteration=iteration, loop_code_version=LOOP_CODE_VERSION,
            representation_lineage_resolution=representation_lineage_resolution,
            session_gap_resolution=session_gap_resolution,
            residual_gap_triage=residual_gap_triage,
        )
        # The handoff carries iteration provenance, so its full artifact hash is expected
        # to change each run. Compare a semantic hash that excludes only source_iteration.
        validation_handoff_semantic_hash = _digest({
            k: v for k, v in validation_handoff.items() if k != "source_iteration"
        })
        artifacts: dict[str, Any] = {
            "corpus_manifest.json": {"schema": "nexus.corpus-manifest.loop.v1", "corpus_manifest_hash": corpus_manifest_hash, "streams": manifest_payload},
            "integrity_report.json": {"schema": "nexus.integrity-loop.v1", "admitted_stream_ids": sorted(admitted_ids), "rejected": rejected},
            "factor_universe.json": {
                "schema": "nexus.factor-universe.loop.v2",
                "selected_stream_ids": list(selected_universe),
                "selected_stream_ids_are_independent_components": False,
                "model_plane_ready": False,
                "model_plane_blocker": "Raw selected streams require reviewed hierarchical representation fusion before model use.",
                "decisions": [asdict(x) for x in universe_decisions],
                "representation_aggregation_contract": {
                    "raw_representations_are_independent_votes": False,
                    "within_symbol_rule": "Fuse streams within sampling construction; fuse constructions within price geometry; fuse geometries within reviewed chart/view family; fuse chart/view families to one symbol plane; then perform cross-asset weighting.",
                    "orthogonal_identity_axes": ["chart_view_family", "price_geometry", "sampling_domain", "sampling_construction"],
                    "required_engine": "HierarchicalFactorEngine.build_from_manifests",
                    "native_clock_rule": "Tick, range, Renko and other event/profile constructions retain native completion boundaries; never coerce them to fixed minute/hour cadence.",
                    "missing_values_rule": "Missing representation observations remain missing; never replace them with zero merely to create agreement.",
                    "duplicate_rule": "Exact/logical duplicates may share compute but never receive additional evidence weight.",
                },
                "production_authorized": False,
            },
            "representation_review_queue.json": review_queue.to_dict(),
            "representation_review_triage.json": representation_review_triage,
            "representation_source_evidence.json": representation_source_evidence,
            "representation_attestation_status.json": representation_attestation_status,
            "corpus_recovery_plan.json": corpus_recovery_plan,
            "stream_descriptive_sweep.json": {"schema": "nexus.stream-descriptive-sweep.v1", "streams": [x.to_dict() for x in sweeps], "descriptive_only": True, "production_authorized": False},
            "research_queue.json": {"schema": "nexus.research-candidate-queue.v1", "candidates": [x.to_dict() for x in candidates], "statistical_promotion_performed": False, "production_authorized": False},
            "representation_lineage_resolution.json": representation_lineage_resolution,
            "session_gap_resolution.json": session_gap_resolution,
            "session_semantics_blockers.json": session_semantics_blockers,
            "residual_gap_triage.json": residual_gap_triage,
            "daedalus_validation_handoff.json": validation_handoff,
        }
        artifact_hashes: dict[str, str] = {}
        artifact_paths: list[str] = []
        for name, payload in artifacts.items():
            path = iter_dir / name
            path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False))
            artifact_hashes[name] = _digest(payload)
            artifact_paths.append(str(path))

        previous_iteration_dir: Path | None = None
        if previous and previous.get("iteration") is not None:
            previous_iteration_dir = self.state_dir / f"iteration_{int(previous['iteration']):04d}"

        previous_artifact_hashes = dict(previous.get("artifact_hashes", {})) if previous else {}
        changed_core_artifacts = sorted(
            name for name in CORE_ARTIFACT_NAMES
            if previous and previous_artifact_hashes.get(name) != artifact_hashes.get(name)
        )
        missing_previous_hashes = sorted(
            name for name in CORE_ARTIFACT_NAMES
            if previous and name not in previous_artifact_hashes
        )

        prev_research = _read_json(previous_iteration_dir / "research_queue.json") if previous_iteration_dir else None
        prev_review = _read_json(previous_iteration_dir / "representation_review_queue.json") if previous_iteration_dir else None
        if previous_iteration_dir and (prev_research is None or prev_review is None):
            raise RuntimeError("verified previous iteration is missing required stability artifacts")
        current_candidate_ids = {c.candidate_id for c in candidates}
        previous_candidate_ids = _candidate_ids(prev_research)
        current_review_ids = {str(c.stream_id) for c in review_queue.candidates}
        previous_review_ids = _review_ids(prev_review)

        same_corpus_reproducible: bool | None = None
        # Reproducibility is only meaningful under the same corpus *and* the same
        # loop implementation. A deliberate code migration may legitimately change
        # core artifacts and must never be mislabeled as nondeterminism.
        if (
            previous
            and prior_hash == corpus_manifest_hash
            and previous.get("loop_code_version") == LOOP_CODE_VERSION
            and not missing_previous_hashes
        ):
            same_corpus_reproducible = not changed_core_artifacts

        previous_validation_handoff_semantic_hash = previous.get("validation_handoff_semantic_hash") if previous else None
        validation_handoff_same_semantics: bool | None = None
        if previous_validation_handoff_semantic_hash:
            validation_handoff_same_semantics = previous_validation_handoff_semantic_hash == validation_handoff_semantic_hash

        stability_report = {
            "schema": "nexus.loop-stability.v1",
            "iteration": iteration,
            "previous_iteration": previous.get("iteration") if previous else None,
            "corpus_changed": delta["corpus_changed"],
            "loop_code_changed": delta["loop_code_changed"],
            "same_corpus_reproducible": same_corpus_reproducible,
            "unexpected_nondeterminism": bool(
                previous
                and prior_hash == corpus_manifest_hash
                and previous.get("loop_code_version") == LOOP_CODE_VERSION
                and (
                    same_corpus_reproducible is False
                    or validation_handoff_same_semantics is False
                )
            ),
            "validation_handoff_semantic_hash": validation_handoff_semantic_hash,
            "validation_handoff_same_semantics": validation_handoff_same_semantics,
            "changed_core_artifacts": changed_core_artifacts,
            "missing_previous_core_hashes": missing_previous_hashes,
            "research_candidates": {
                "current_count": len(current_candidate_ids),
                "previous_count": len(previous_candidate_ids) if previous else None,
                "persistent_count": len(current_candidate_ids & previous_candidate_ids),
                "new_ids": sorted(current_candidate_ids - previous_candidate_ids) if previous else sorted(current_candidate_ids),
                "resolved_ids": sorted(previous_candidate_ids - current_candidate_ids) if previous else [],
                "family_counts": _counter_from_candidates(candidates, "family"),
                "priority_counts": _counter_from_candidates(candidates, "priority"),
            },
            "representation_review": {
                "current_count": len(current_review_ids),
                "previous_count": len(previous_review_ids) if previous else None,
                "persistent_count": len(current_review_ids & previous_review_ids),
                "new_stream_ids": sorted(current_review_ids - previous_review_ids) if previous else sorted(current_review_ids),
                "resolved_stream_ids": sorted(previous_review_ids - current_review_ids) if previous else [],
            },
            "production_authorized": False,
        }
        stability_path = iter_dir / "stability_report.json"
        stability_path.write_text(json.dumps(stability_report, sort_keys=True, indent=2, allow_nan=False))
        artifact_hashes["stability_report.json"] = _digest(stability_report)
        artifact_paths.append(str(stability_path))

        summary["stability"] = {
            "same_corpus_reproducible": same_corpus_reproducible,
            "unexpected_nondeterminism": stability_report["unexpected_nondeterminism"],
            "changed_core_artifact_count": len(changed_core_artifacts),
            "new_research_candidates": len(stability_report["research_candidates"]["new_ids"]),
            "resolved_research_candidates": len(stability_report["research_candidates"]["resolved_ids"]),
            "new_representation_reviews": len(stability_report["representation_review"]["new_stream_ids"]),
            "resolved_representation_reviews": len(stability_report["representation_review"]["resolved_stream_ids"]),
            "validation_handoff_same_semantics": validation_handoff_same_semantics,
        }
        summary["representation_review_triage"] = {
            "p0_count": representation_review_triage["p0_count"],
            "p2_count": representation_review_triage["p2_count"],
            "triage_class_counts": representation_review_triage["triage_class_counts"],
            "cluster_count": representation_review_triage["cluster_count"],
            "auto_resolved_count": 0,
            "production_authorized": False,
        }
        summary["representation_source_evidence"] = {
            "cluster_count": representation_source_evidence["cluster_count"],
            "p0_stream_count": representation_source_evidence["p0_stream_count"],
            "comparison_stream_counts": representation_source_evidence["comparison_stream_counts"],
            "standard_timeframe_cadence_compatible_stream_count": representation_source_evidence["standard_timeframe_cadence_compatible_stream_count"],
            "standard_timeframe_cadence_incompatible_stream_count": representation_source_evidence["standard_timeframe_cadence_incompatible_stream_count"],
            "auto_resolved_count": 0,
            "production_authorized": False,
        }
        summary["representation_attestation"] = {
            "p0_stream_count": representation_attestation_status["p0_stream_count"],
            "resolved_by_attestation_count": representation_attestation_status["resolved_by_attestation_count"],
            "remaining_p0_count": representation_attestation_status["remaining_p0_count"],
            "status_counts": representation_attestation_status["status_counts"],
            "attestation_input_present": attestation_input_path.exists(),
            "production_authorized": False,
        }
        summary["corpus_recovery_plan"] = {
            "current": corpus_recovery_plan["current"],
            "gaps_relative_to_historical_anchor": corpus_recovery_plan["gaps_relative_to_historical_anchor"],
            "owner_expected_min_entry_gap": corpus_recovery_plan["owner_expected_min_entry_gap"],
            "historical_archive_count": corpus_recovery_plan["historical_anchor"]["archive_count"],
            "counts_are_lower_bounds_not_completeness_proof": True,
            "production_authorized": False,
        }
        summary["representation_lineage_resolution"] = {
            "candidate_count": representation_lineage_resolution["candidate_count"],
            "resolved_count": representation_lineage_resolution["resolved_count"],
            "unresolved_count": representation_lineage_resolution["unresolved_count"],
            "production_authorized": False,
        }
        summary["session_gap_resolution"] = {
            "candidate_count": session_gap_resolution["candidate_count"],
            "session_semantics_resolved_count": session_gap_resolution["session_semantics_resolved_count"],
            "residual_diagnostic_count": session_gap_resolution["residual_diagnostic_count"],
            "still_session_blocked_count": session_gap_resolution["still_session_blocked_count"],
            "data_loss_asserted": False,
            "production_authorized": False,
        }
        summary["session_semantics_blockers"] = {
            "unresolved_candidate_count": session_semantics_blockers["unresolved_candidate_count"],
            "blocker_class_counts": session_semantics_blockers["blocker_class_counts"],
            "production_authorized": False,
        }
        summary["residual_gap_triage"] = {
            "candidate_count": residual_gap_triage["candidate_count"],
            "classification_counts": residual_gap_triage["classification_counts"],
            "cross_resolution_comparable_gap_count": residual_gap_triage["cross_resolution_comparable_gap_count"],
            "gaps_with_sibling_activity": residual_gap_triage["gaps_with_sibling_activity"],
            "aggregate_sibling_activity_ratio": residual_gap_triage["aggregate_sibling_activity_ratio"],
            "data_loss_asserted": False,
            "production_authorized": False,
        }
        summary["validation_handoff"] = {
            "schema": validation_handoff["schema"],
            "semantic_hash": validation_handoff_semantic_hash,
            "route_counts": validation_handoff["route_counts"],
            "protected_holdout_spent": False,
            "production_authorized": False,
        }

        summary["artifact_hashes"] = dict(sorted(artifact_hashes.items()))
        iteration_hash = _digest(summary)
        summary["iteration_hash"] = iteration_hash
        summary_path = iter_dir / "iteration_summary.json"
        summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))
        artifact_paths.append(str(summary_path))

        state = {
            "schema": LOOP_SCHEMA,
            "loop_code_version": LOOP_CODE_VERSION,
            "iteration": iteration,
            "status": "completed",
            # Resume metadata must survive extraction on another machine/agent.
            # The corpus root is deliberately only a hint; iteration artifact
            # locations are relative to state_dir and therefore portable.
            "corpus_root_hint": str(self.corpus_root),
            "paths_relative_to_state_dir": True,
            "corpus_manifest_hash": corpus_manifest_hash,
            "iteration_hash": iteration_hash,
            "latest_iteration_dir": iter_dir.name,
            "latest_summary_path": f"{iter_dir.name}/{summary_path.name}",
            "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "validation_handoff_semantic_hash": validation_handoff_semantic_hash,
            "coverage_claim_allowed": summary["coverage_claim_allowed"],
            "production_authorized": False,
        }
        state["state_hash"]=_digest(state)
        self._state_path.write_text(json.dumps(state, sort_keys=True, indent=2, allow_nan=False))
        artifact_paths.append(str(self._state_path))
        return LoopResult(iteration, corpus_manifest_hash, iteration_hash, str(summary_path), str(self._state_path), tuple(artifact_paths), summary)
