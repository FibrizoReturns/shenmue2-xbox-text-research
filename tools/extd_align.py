# -*- coding: utf-8 -*-
"""extd_align.py —— Xbox 美版 EXTD 段 与 DC 日版主文本 的比对

两个必须先做的判定（否则数字会失真）：

1) 语种判定。EXTD 并不总是日文。0120.afs 等文件里 EXTD 装的是英文
   （如 "Okay.＆Goodbye."、"Southeast?"），那是备用语言段，不能算进日文命中率。

2) 记录对齐。两平台记录顺序/条数不同（0102.afs 出现 2→3、3→4 的整体偏移），
   所以主口径是内容命中，不是序号对齐。

分层：
    jp_sent   日文、>=10B（台词级）—— 主结论
    jp_short  日文、<10B（人名/单词条目）
    other     非日文（英文等），只计数

用法:
    python tools/extd_align.py --xbox "<Xbox 解包根>" --dc "<DC 解包根>" \
        --out data/extd_align_summary.csv --detail data/extd_miss_long.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import afs  # noqa: E402

SCENES = ("01", "02", "03", "04")
SENT_MIN = 10


def norm(b: bytes) -> bytes:
    b = b.rstrip(b"\x00\x20")
    while b.endswith(b"\xa1\xa1"):
        b = b[:-2].rstrip(b"\x00\x20")
    return b


def is_japanese(b: bytes) -> bool:
    """EUC-JP 字节层判定：出现假名区(A4/A5)或汉字区(B0-FE)即视为日文。"""
    i = 0
    while i < len(b):
        c = b[i]
        if c < 0x80:
            i += 1
            continue
        if i + 1 >= len(b):
            return False
        c2 = b[i + 1]
        if 0xA4 <= c <= 0xA5 and 0xA1 <= c2 <= 0xF6:
            return True                       # 平假名/片假名
        if 0xB0 <= c <= 0xFE and 0xA1 <= c2 <= 0xFE:
            return True                       # 汉字
        i += 2
    return False


def pairs(xbox_root: str, dc_root: str):
    """按文件名去重：同一 AFS 会在多碟 scene 目录重复出现，只取首次匹配。"""
    seen: set[str] = set()
    for disc, scene in enumerate(SCENES, start=1):
        xdir = os.path.join(xbox_root, "scene", scene, "stream")
        ddir = os.path.join(dc_root, str(disc), "SCENE", scene, "STREAM")
        if not os.path.isdir(xdir) or not os.path.isdir(ddir):
            continue
        dc_index = {n.upper(): n for n in os.listdir(ddir) if n.upper().endswith(".AFS")}
        for name in sorted(os.listdir(xdir)):
            key = name.upper()
            if not name.lower().endswith(".afs") or key in seen:
                continue
            dc_name = dc_index.get(key)
            if dc_name is None:
                continue
            seen.add(key)
            yield name, os.path.join(xdir, name), os.path.join(ddir, dc_name)


def compare_file(xname, xpath, dpath, long_miss):
    xb = afs.load(xpath)
    dc = afs.load(dpath)
    if not xb or not dc:
        return {"file": xname, "status": "parse_fail"}

    by_pair, by_text = set(), set()
    for blk in dc:
        for rec in blk.records:
            t = norm(rec.main)
            if t:
                by_pair.add((rec.speaker, t))
                by_text.add(t)

    st = {k: 0 for k in ("dc_records", "jp_sent", "jp_sent_hit",
                         "jp_short", "jp_short_hit", "other_extd")}
    st["file"] = xname
    st["status"] = "ok"
    st["dc_records"] = sum(len(b.records) for b in dc)

    for blk in xb:
        for k, rec in enumerate(blk.records):
            if not rec.extd:
                continue
            t = norm(rec.extd)
            if not is_japanese(t):
                st["other_extd"] += 1
                continue

            hit = (rec.speaker, t) in by_pair or t in by_text
            bucket = "jp_sent" if len(t) >= SENT_MIN else "jp_short"
            st[bucket] += 1
            if hit:
                st[f"{bucket}_hit"] += 1
            elif bucket == "jp_sent" and len(long_miss) < 30000:
                long_miss.append({
                    "file": xname, "block": blk.index, "record": k,
                    "speaker": rec.speaker_name, "len": len(t),
                    "text": t.decode("euc_jp", "replace"), "hex": t.hex(),
                })
    return st


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xbox", required=True)
    ap.add_argument("--dc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--detail", default="")
    args = ap.parse_args()

    rows, misses = [], []
    for i, (name, xp, dp) in enumerate(pairs(args.xbox, args.dc), start=1):
        rows.append(compare_file(name, xp, dp, misses))
        if i % 50 == 0:
            print(f"  ... {i} files", flush=True)

    keys = ("dc_records", "jp_sent", "jp_sent_hit", "jp_short", "jp_short_hit", "other_extd")
    total = {k: sum(r.get(k, 0) for r in rows) for k in keys}

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "status"] + list(keys))
        for r in rows:
            w.writerow([r.get("file", ""), r.get("status", "")] + [r.get(k, 0) for k in keys])

    def rate(h, n):
        return f"{h / n:.2%}" if n else "-"

    print("\n===== EXTD alignment (Japanese only, content mode) =====")
    print(f"files            : {len(rows)}")
    print(f"DC records       : {total['dc_records']}")
    print(f"非日文 EXTD      : {total['other_extd']}")
    for b, label in (("jp_sent", "日文台词 >=10B"), ("jp_short", "日文短条 <10B")):
        e, h = total[b], total[f"{b}_hit"]
        print(f"{label:<16}: {e}  hit {h} ({rate(h, e)})  miss {e - h}")

    if args.detail and misses:
        with open(args.detail, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(misses[0].keys()))
            w.writeheader()
            w.writerows(misses)
        print(f"long miss list   : {len(misses)} -> {args.detail}")


if __name__ == "__main__":
    main()
