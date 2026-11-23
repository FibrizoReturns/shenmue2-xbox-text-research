# -*- coding: utf-8 -*-
"""font_audit.py —— 字库指纹 / 槽级差异 / RYOU 结构 的审计脚本

用法:
    python tools/font_audit.py --xbox "<Xbox 解包根>" --dc "<DC 日版解包根>" --outdir data

输出:
    font_fingerprints.csv   各文件大小与 md5（Xbox 与 DC 四碟）
    kana_slot_diff.csv      dc_kana 256 槽逐槽一致性
    ryou_analysis.csv      RYOU 结构差异的键值记录

只输出哈希与结构指标，不复制、不内嵌任何游戏原始数据。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os

COLD_OFFSET = 15328          # COLD.BIN 内嵌汉字库起始
KANJI_LEN = 351270           # 7806 槽 × 45B
CELL30 = 30                  # 16×15 点阵
SLOTS = 256


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest().upper()


def read(p: str) -> bytes:
    with open(p, "rb") as fh:
        return fh.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xbox", required=True)
    ap.add_argument("--dc", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    xb_misc = os.path.join(args.xbox, "misc")
    dc_root = args.dc

    targets = [("dc_kanji.fon", "DC_KANJI.FON"), ("dc_kana.fon", "DC_KANA.FON"),
               ("RYOU.FON", "RYOU.FON")]

    # ---- 1. fingerprints ----
    rows = []
    for xname, dname in targets:
        xp = os.path.join(xb_misc, xname)
        if os.path.exists(xp):
            xd = read(xp)
            rows.append(["Xbox US", xname, "", len(xd), md5(xd), ""])
        for disc in ("1", "2", "3", "4"):
            dp = os.path.join(dc_root, disc, "MISC", dname)
            if os.path.exists(dp):
                dd = read(dp)
                rows.append([f"DC JP disc{disc}", dname, disc, len(dd), md5(dd), ""])

    cold_p = os.path.join(xb_misc, "COLD.BIN")
    if os.path.exists(cold_p):
        cold = read(cold_p)
        seg = cold[COLD_OFFSET:COLD_OFFSET + KANJI_LEN]
        rows.append(["Xbox US", "COLD.BIN", "", len(cold), md5(cold),
                     f"embedded kanji @{COLD_OFFSET}..{COLD_OFFSET + KANJI_LEN} md5={md5(seg)}"])

    with open(os.path.join(args.outdir, "font_fingerprints.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["side", "file", "disc", "size", "md5", "note"])
        w.writerows(rows)

    # ---- 2. kana slot diff ----
    xk = read(os.path.join(xb_misc, "dc_kana.fon"))
    dk = read(os.path.join(dc_root, "1", "MISC", "DC_KANA.FON"))
    slot_rows = []
    for i in range(min(SLOTS, len(xk) // CELL30, len(dk) // CELL30)):
        a = xk[i * CELL30:(i + 1) * CELL30]
        b = dk[i * CELL30:(i + 1) * CELL30]
        slot_rows.append([i, int(a == b), md5(a), md5(b)])

    with open(os.path.join(args.outdir, "kana_slot_diff.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["slot", "same", "xbox_md5", "dc_md5"])
        w.writerows(slot_rows)

    same = sum(r[1] for r in slot_rows)
    diff = [r[0] for r in slot_rows if not r[1]]

    # ---- 3. RYOU analysis ----
    xr = read(os.path.join(xb_misc, "RYOU.FON"))
    dr = read(os.path.join(dc_root, "1", "MISC", "RYOU.FON"))
    ka = read(os.path.join(xb_misc, "dc_kanji.fon"))
    ryou_rows = [
        ["xbox_len", len(xr), ""],
        ["xbox_slots_30b", len(xr) // CELL30, ""],
        ["dc_len", len(dr), ""],
        ["dc_slots_45b", len(dr) // 45, "24x15 布局"],
        ["xbox_eq_dc_prefix", int(xr == dr[:len(xr)]), ""],
        ["xbox_eq_dc_suffix", int(xr == dr[-len(xr):]), ""],
        ["xbox_eq_kanji_prefix", int(xr == ka[:len(xr)]), ""],
        ["xbox_found_in_dc_at", dr.find(xr), "-1 表示不存在"],
        ["dc_ryou_eq_dc_kanji", int(dr == ka), ""],
    ]
    with open(os.path.join(args.outdir, "ryou_analysis.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value", "note"])
        w.writerows(ryou_rows)

    print(f"fingerprints : {len(rows)} rows")
    print(f"kana slots   : {len(slot_rows)} (same {same}, diff {len(diff)})")
    print(f"kana diff slots: {diff[:12]}{' ...' if len(diff) > 12 else ''}")
    print("ryou         : len xbox/dc = %d / %d, found_in_dc=%s"
          % (len(xr), len(dr), dr.find(xr)))


if __name__ == "__main__":
    main()
