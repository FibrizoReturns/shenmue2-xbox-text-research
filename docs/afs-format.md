# AFS / CHID 文本结构

Shenmue II 的 Xbox 版与 DC 版共用 AFS 容器格式，差异只出现在记录内部的子标签。以下为实测结构，`tools/afs.py` 即按此实现。

## 1. 容器头

| 偏移 | 长度 | 内容 |
|---|---|---|
| 0x00 | 4 | `"AFS\0"` |
| 0x04 | 4 | entry 数量（**小端** uint32） |
| 0x08 | 8 × N | entry 表：`{ uint32 offset, uint32 length }`（均小端） |

示例（美版 `scene/01/stream/0005.afs`，前 16 字节）：

```
41 46 53 00 | 22 00 00 00 | 00 00 08 00 | 35 4E 00 00
"AFS\0"      34 (0x22)      0x00080000    0x00004E35
```

- entry 数 = 34
- entry[0] = `offset 0x00080000 (524288)`，`length 0x4E35 (20021)`
- `524288 + 20021 = 544309 ≤ 890880`（文件总长），成立

> 注意：不同工具对这段有"大端/小端"两种读法，读错会得到 570425344 这类荒谬的 entry 数。**偏移与长度都是小端**。

## 2. 块结构

每个 entry 指向一个块，块首为 8 字节记录标签：

```
43 48 49 44 0C 00 00 00      "CHID" + 0x0C + 000000
```

一个块内可含多条记录，每条记录都从 `CHID` 标签重新开始。因此"块内记录数"用 `CHID` 出现次数统计，而不是靠长度推算。

## 3. 记录结构

以记录起点 `S` 为基准：

| 偏移 | 长度 | 字段 |
|---|---|---|
| S+0 | 8 | `CHID` 标签 |
| S+8 | 8 | speaker，如 `RYO_STDL`、`JOP_STDL`、`SNC_STDL` |
| S+16 | 4 | `sub_offset`（小端），相对 `S` 的子标签偏移 |
| S+20 | `sub_offset - 8` | 主文本（含尾部 `00` 填充） |

子标签位置 = `S + sub_offset + 12`，取 4 字节，常见值：

| 标签 | 含义 |
|---|---|
| `EXTD` | 附带的原文段（美版为日文，少数文件为英文） |
| `CLIP` | 动作／音效段 |
| `FIGH` | 战斗相关 |
| `ENDC` | 块结束 |

`cap`（主文本可写字节数）= `sub_offset - 8`。子标签若为 `CLIP`／`FIGH`，该记录通常不是对白，不应写入。

## 4. 两个平台的差异

同一个 AFS、同一个 entry，两侧结构对照：

**DC 日版**

```
CHID | RYO_STDL | 0x28 | <日文主文本 20B> | CLIP ...
```

**Xbox 美版**

```
STDL | <英文主文本> | EXTD | <日文 20B> | CLIP ...
```

即 DC 的"主文本"在美版被挪进了 `EXTD`，主文本位置换成英文。这就是"美版残留日文"的来源，也是本项目所有比对的锚点。

## 5. 已知陷阱

1. **不是每个 entry 都是文本块**。只处理首 4 字节为 `CHID` 的块，否则会解析出垃圾。
2. **同名 AFS 会在多碟目录重复**。`scene/01..04` 与 `SCENE/01..04` 之间存在重复文件名，统计前必须按文件名去重，否则总数会被放大（实测 441 → 340）。
3. **记录条数两平台不等**。`0102.afs` 出现整体一位偏移（`2→3`、`3→4`），按序号对齐会制造大量假差异。
4. **`EXTD` 不总是日文**。`0120.afs` 等文件里装的是英文（`Okay.＆Goodbye.`），必须先判语种。

## 6. 最小解析代码

见 `tools/afs.py`，核心逻辑：

```python
count = struct.unpack_from("<I", data, 4)[0]
entries = [struct.unpack_from("<II", data, 8 + i * 8) for i in range(count)]

for off, length in entries:
    blob = data[off:off + length]
    if blob[:4] != b"CHID":
        continue
    for start in chid_positions(blob):
        speaker = blob[start + 8 : start + 16]
        sub_off = struct.unpack_from("<I", blob, start + 16)[0]
        main = blob[start + 20 : start + sub_off + 12].rstrip(b"\x00")
```
