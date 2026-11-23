# -*- coding: utf-8 -*-
"""afs.py —— 最小化 AFS / CHID 记录解析器（Shenmue II Xbox & Dreamcast）

仅依赖标准库。用于本项目所有“文本层”比对，避免重新实现第二套格式定义。

AFS 容器（一律小端）:
    0x00  'AFS\\0'
    0x04  uint32  entry_count
    0x08  entry_count × { uint32 offset, uint32 length }

每个 entry 是一个 stream 块:
    0x00  'CHID' + 0x0C 00 00 00     8 字节记录标签
    块内可含多条记录，每条记录以 CHID 标签开头:
      +8   speaker      8 字节（如 RYO_STDL / AN01_STDL / *_CLIP）
      +16  uint32 sub_offset   相对记录起点的子标签偏移
      +20  主文本，止于 (记录起点 + sub_offset + 12)
    子标签位于 (记录起点 + sub_offset + 12)，取 4 字节:
      EXTD / CLIP / FIGH / ENDC ...

EXTD 段承载 Xbox 版残留的日文文本（DC 版没有该子标签，主文本即日文）。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

CHID_TAG = b"CHID\x0c\x00\x00\x00"
SUB_TAGS = (b"EXTD", b"CLIP", b"FIGH", b"ENDC", b"STDL", b"CHID")


@dataclass
class Record:
    speaker: bytes
    main: bytes = b""
    extd: bytes = b""
    sub_tag: bytes = b""
    cap: int = 0

    @property
    def speaker_name(self) -> str:
        return self.speaker.decode("latin1", "ignore")


@dataclass
class Block:
    index: int
    offset: int
    length: int
    records: list[Record] = field(default_factory=list)


def _chid_starts(blob: bytes) -> list[int]:
    starts, pos = [], 0
    while True:
        j = blob.find(CHID_TAG, pos)
        if j < 0:
            break
        starts.append(j)
        pos = j + 4
    return starts


def _next_tag(blob: bytes, pos: int, end: int) -> int:
    """返回 pos 之后最近的已知子标签位置，找不到则返回 end。"""
    best = end
    for tag in SUB_TAGS:
        j = blob.find(tag, pos, end)
        if j >= 0 and j < best:
            best = j
    return best


def _read_record(blob: bytes, start: int, end: int) -> Record:
    rec = Record(speaker=b"")
    if start + 20 > end:
        return rec

    rec.speaker = blob[start + 8 : start + 16]
    sub_off = struct.unpack_from("<I", blob, start + 16)[0]
    if not (0 < sub_off <= 16384):
        return rec

    sub_pos = start + sub_off + 12
    if sub_pos + 4 > end:
        return rec

    tag = blob[sub_pos : sub_pos + 4]
    rec.sub_tag = tag
    rec.cap = sub_off - 8                      # 主文本区字节数（含结尾 00）
    rec.main = blob[start + 20 : sub_pos].rstrip(b"\x00")

    if tag == b"EXTD":
        pay_start = sub_pos + 8
        pay_end = _next_tag(blob, pay_start, end)
        rec.extd = blob[pay_start:pay_end].rstrip(b"\x00")

    return rec


def parse_afs(data: bytes) -> list[Block] | None:
    """解析 AFS 容器；结构不符时返回 None。"""
    if data[:4] != b"AFS\x00":
        return None
    count = struct.unpack_from("<I", data, 4)[0]
    if count > 100_000:
        return None

    entries = [struct.unpack_from("<II", data, 8 + i * 8) for i in range(count)]
    blocks: list[Block] = []

    for idx, (off, length) in enumerate(entries):
        if length <= 0 or off + length > len(data):
            continue
        blob = data[off : off + length]
        if blob[:4] != b"CHID":
            continue

        starts = _chid_starts(blob)
        ends = starts[1:] + [len(blob)]
        recs = [_read_record(blob, s, e) for s, e in zip(starts, ends)]
        blocks.append(Block(index=idx, offset=off, length=length, records=recs))

    return blocks


def load(path: str) -> list[Block] | None:
    with open(path, "rb") as fh:
        return parse_afs(fh.read())


if __name__ == "__main__":
    import sys

    for p in sys.argv[1:]:
        blocks = load(p)
        if blocks is None:
            print(f"{p}: not an AFS container")
            continue
        nrec = sum(len(b.records) for b in blocks)
        nextd = sum(1 for b in blocks for r in b.records if r.extd)
        print(f"{p}: blocks={len(blocks)} records={nrec} with_EXTD={nextd}")
