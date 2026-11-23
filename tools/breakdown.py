# -*- coding: utf-8 -*-
"""breakdown.py —— 把 extd_align_summary.csv 归并为文件组，并抽样短条内容

用法:
    python tools/breakdown.py --summary data/extd_align_summary.csv \
        --out data/extd_breakdown.csv [--xbox ... --sample-out data/short_samples.tsv]
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import afs  # noqa: E402

GROUPS = {
    "FREE01-04（自由对话）": ("FREE01", "FREE02", "FREE03", "FREE04"),
    "0137（独立表）": ("0137",),
    "S2BV（独立表）": ("S2BV",),
}


def group_of(name: str) -> str:
    stem = name.split(".")[0].upper()
    for label, members in GROUPS.items():
        if stem in members:
            return label
    return "主线/过场（其余）"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--xbox", default="")
    ap.add_argument("--sample-out", default="")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.summary, encoding="utf-8")))
    agg = {}
    for r in rows:
        g = group_of(r["file"])
        a = agg.setdefault(g, {"files": 0, "jp_sent": 0, "jp_sent_hit": 0,
                               "jp_short": 0, "jp_short_hit": 0})
        a["files"] += 1
        for k in ("jp_sent", "jp_sent_hit", "jp_short", "jp_short_hit"):
            a[k] += int(r[k])

    order = list(GROUPS.keys()) + ["主线/过场（其余）"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group", "files", "jp_sent", "jp_sent_hit", "sent_rate",
                    "jp_short", "jp_short_hit", "short_rate"])
        for g in order:
            if g not in agg:
                continue
            a = agg[g]
            sr = f"{a['jp_sent_hit'] / a['jp_sent']:.2%}" if a["jp_sent"] else "-"
            shr = f"{a['jp_short_hit'] / a['jp_short']:.2%}" if a["jp_short"] else "-"
            w.writerow([g, a["files"], a["jp_sent"], a["jp_sent_hit"], sr,
                        a["jp_short"], a["jp_short_hit"], shr])

    print(f"{'group':<22}{'files':>6}{'sent':>8}{'hit':>8}{'rate':>9}")
    for g in order:
        if g not in agg:
            continue
        a = agg[g]
        sr = f"{a['jp_sent_hit'] / a['jp_sent']:.2%}" if a["jp_sent"] else "-"
        print(f"{g:<22}{a['files']:>6}{a['jp_sent']:>8}{a['jp_sent_hit']:>8}{sr:>9}")

    if args.xbox and args.sample_out:
        path = os.path.join(args.xbox, "scene", "01", "stream", "FREE01.afs")
        blocks = afs.load(path) or []
        samples = []
        for blk in blocks:
            for rec in blk.records:
                t = rec.extd.rstrip(b"\x00\x20")
                if t and len(t) < 10:
                    samples.append((rec.speaker_name, t.decode("euc_jp", "replace"), t.hex()))
        with open(args.sample_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["speaker", "text", "hex"])
            w.writerows(samples[:80])
        print(f"\nFREE01 short samples: {len(samples)} -> {args.sample_out}")
        for s in samples[:15]:
            print("  ", s[0], "|", s[1])


if __name__ == "__main__":
    main()
