"""Reproducible real-data development comparison; never spends protected tails."""
from dataclasses import replace
from pathlib import Path
import argparse
import hashlib
import sys
import tempfile
import time
import zipfile
import platform
from statistics import median

from . import common


def benchmark(archive, member, root):
    sys.path.insert(0, str(root / "systems/daedalus/src"))
    from daedalus.config import DaedalusConfig
    from daedalus.data import load_bars_with_quality
    from daedalus.features import build_causal_features
    from daedalus.models import default_model_specs
    from daedalus.validation import walk_forward_validate, split_development_holdout
    from threadpoolctl import threadpool_limits
    cfg = DaedalusConfig()
    with zipfile.ZipFile(archive) as z:
        info = z.getinfo(member)
        if info.file_size > 12_000_000:
            raise ValueError("Benchmark exceeds source budget")
        raw = z.read(info)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "source.csv"
        path.write_bytes(raw)
        bars, quality = load_bars_with_quality(path)
    x, y, returns = build_causal_features(bars, cfg.features)
    dev_end, holdout_start = split_development_holdout(len(x), cfg.validation, cfg.features.target_horizon)
    results = {}
    with threadpool_limits(limits=1):
        for name, placement, window in [("baseline_sequential", "sequential", None),
                                        ("spread_unbounded", "spread", None),
                                        ("spread_bounded", "spread", 2000)]:
            validation = replace(cfg.validation, fold_placement=placement, max_train_size=window)
            samples = []
            for _ in range(3):
                start = time.perf_counter()
                value = walk_forward_validate("logistic", default_model_specs()[0].factory(42),
                                               x, y, returns, validation, cfg.features.target_horizon)
                samples.append(time.perf_counter() - start)
            results[name] = {"seconds": median(samples), "seconds_samples": samples, "validation": value.to_dict(),
                             "fold_training_rows": [f.train_end-f.train_start+1 for f in value.folds]}
    return {"schema": "icarus.engine_upgrade.benchmark.v1", **common.AUTHORITY,
            "observed_at": common.now(), "source": {"archive": archive.name, "member": member,
            "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(bars), "price_basis": "CANDLE_PROXY"},
            "configuration": cfg.to_dict(), "scientific_context": common.context(root),
            "benchmark_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "runtime": {"python": sys.version, "platform": platform.platform(), "threads": 1},
            "quality": quality.to_dict(), "development_feature_rows": dev_end,
            "protected_rows_reserved": len(x)-holdout_start, "models_benchmarked": ["logistic"],
            "contexts": results,
            "span_ratio": results["spread_bounded"]["validation"]["coverage"]["source_row_span"] /
                          results["baseline_sequential"]["validation"]["coverage"]["source_row_span"],
            "bounded_vs_unbounded_runtime_ratio": results["spread_unbounded"]["seconds"] /
                                                  results["spread_bounded"]["seconds"],
            "interpretation": "One real source and one model, median of three timing samples per configuration. "
                              "Span is not sample count; a bounded training window changes the model. "
                              "No inference of confirmed alpha, accuracy improvement, or general runtime guarantee."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--member", required=True)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = benchmark(args.archive, args.member, Path.cwd())
    common.write_json(args.output, common.seal(result))
    print({"rows": result["source"]["rows"], "span_ratio": result["span_ratio"],
           "bounded_vs_unbounded_runtime_ratio": result["bounded_vs_unbounded_runtime_ratio"]})


if __name__ == "__main__":
    main()
