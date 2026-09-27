from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .catalog import CorpusCatalog
from .quality import quality_score
from .research_loop import AdvancedCSVResearchLoop, AdvancedLoopConfig, CoverageAnchor

def main(argv=None):
    p=argparse.ArgumentParser(prog="nexus")
    sub=p.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("catalog"); c.add_argument("root"); c.add_argument("--json",dest="json_path")
    l=sub.add_parser("loop-once"); l.add_argument("root"); l.add_argument("--state-dir",required=True); l.add_argument("--anchor-entries",type=int,default=626); l.add_argument("--anchor-rows",type=int,default=12588290); l.add_argument("--owner-expected-min",type=int,default=800)
    args=p.parse_args(argv)
    if args.cmd=="catalog":
        manifests=CorpusCatalog(args.root).build()
        payload=[{**m.to_dict(),"quality_score":quality_score(m)} for m in manifests]
        summary={
            "physical_csv_entries":len(payload),
            "usable_entries":sum("appledouble" not in x["quality_flags"] and x["row_count"]>0 for x in payload),
            "appledouble_entries":sum("appledouble" in x["quality_flags"] for x in payload),
            "exact_byte_duplicates":sum(bool(x["byte_duplicate_of"]) for x in payload),
            "rows":sum(x["row_count"] for x in payload),
        }
        print(json.dumps(summary,indent=2))
        if args.json_path:
            Path(args.json_path).write_text(json.dumps({"summary":summary,"streams":payload},indent=2))
    elif args.cmd=="loop-once":
        cfg=AdvancedLoopConfig(state_dir=args.state_dir, prior_anchor=CoverageAnchor("AION_PRIOR_CHECKPOINT",args.anchor_entries,args.anchor_rows), min_owner_expected_entries=args.owner_expected_min)
        result=AdvancedCSVResearchLoop(args.root,cfg).run_once()
        print(json.dumps({"iteration":result.iteration,"corpus_manifest_hash":result.corpus_manifest_hash,"iteration_hash":result.iteration_hash,"summary_path":result.summary_path,"state_path":result.state_path,"summary":result.summary},indent=2))

if __name__ == "__main__":
    main()
