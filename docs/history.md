# 前期工作全记录（2026-10-10 – 2026-11-22）

本文件是《莎木 II》Xbox 美版文本/字库研究的**完整工作记录总览**，整理自两个工作会话的全部产物：

- `2026-10-20\new-chat-2`：272 个 txt（4.9 MB）、265 个 py（0.7 MB）、248 个 png（55.3 MB）、48 个 tsv（14 MB）、2 个 md
- `2026-11-22\new-chat-4`：PC 重制版字幕表探针

**标注约定**：每条结论都注明来源文件名。「复算」= 本仓库脚本在 2026-11-24 现场重跑；「旧记录」= 原会话产物原样转述，本仓库未重跑；「实机」= xemu 0.8.138 截图取证。凡旧记录与本次结果口径不同，两套数字并列，不合并。

---

## 0. 一句话结论

Xbox 美版《莎木 II》的文本层已被逆向到可读、可写、可回读校验的程度：四章字幕容器结构、`EXTD` 内嵌日文母本、`COLD.BIN@15328` 字库位置、HUMANS 的语音 ID 对齐、超长句容量模型，全部有实测数据支撑；中文显示的 PoC 已在实机跑通。真正的瓶颈不是"能不能读",而是**容量**——四章共约 2.6 万条真超长句放不进原始槽位，其中约 1.7 万条无法原地救回。

---

## 1. 数据基座

| 对象 | 规模 | 来源 |
|---|---|---|
| Xbox 美版解包 | 10,219 文件 / 305 目录 | `_enum3.txt`、`filelist.tsv` |
| Xbox AFS 分章 | 01: 107、02: 128、03: 157、04: 53 | `audit_01..04.txt` |
| DC 日版解包 | 3,380 文件 | `dc_xb_compare.txt`、`cd1tree.txt` |
| DC 汉化版 | 4 碟；`STREAM` 明文可读，`HUMANS` 为私压缩 | `盘1核查结论.txt`、`_hcn.txt` |
| PC 重制版字幕表 | 223,749 行 × 14 列 | `_stats_subs.txt`、`_probe_sh2subs.txt` |

重制版表结构（`Subtitles` 工作表）：

```
CONV ID | CONV ORDER | STRING ID | CHAR ID | Gender | Long Name |
English | Korean | T.Chinese | S.Chinese | French | German | Japanese | DUPLICATE CHECK
```

各语言列非空行数：English 222,825、T.Chinese 222,826、S.Chinese 222,825、Japanese 223,417；另有 `System` 表 89 行。`CONV ID` 有 1,067 个取值，其中空值 24,276 行。

> 意义：这是目前唯一一份官方简体/繁体双列母表，可直接当"繁中→简中"的转换源，不需要另做翻译。

---

## 2. 容器格式考古

### 2.1 AFS

```
+0  "AFS\0"
+4  uint32 LE  count
+8  count × { uint32 LE offset, uint32 LE length }
```

陷阱：长度字段是小端，DC 版和 Xbox 版一致；`S2BV.afs`、`SY07.afs` 两条不是 AFS 头（`00 00 00 00`），需跳过（`audit_01..04.txt`）。

### 2.2 CHID 记录

```
+0    "CHID"
+4    char[8]  name（如 RYO_STDL / RYO_EXTD / KYG_CLIP）
+12   uint32 LE  alen
+16   uint32 LE  off16  → 子标签相对 @20 的偏移
+20   main text（EUC-JP 双字节 / ASCII）
```

子标签（`EXTD` / `CLIP` / `FIGH`）位于 `20 + off16`，长度在标签后 4 字节；记录以 `ENDC` 收尾。

实测分布（`_tags.txt`）：有效记录 7,699，首标签 EXTD 7,206 / CLIP 99 / FIGH 3；首标签位置相对 `off+12`，7,305 条为 0，3 条为 −8。
DC 侧（`_tagsdc.txt`）：7,616 条有效，白名单 7,485，被过滤 131（`*_CLIP` 系列，len=16 只有 `ENDC`）。

### 2.3 不是紧密链式

`0007.AFS`、`0015.AFS` 的记录边界不是"上一段末尾接下一段开头"，而是 `next=b'\x04\x00\x03\x00'` 这类非标签字节（`0007_strict.txt`、`0015_strict.txt`）。按固定步长扫描会错位，必须顺序解析。

`_clip.txt` 另有一例：rec23 的 `ENDC` 终点 4016，下一条 `CHID` 在 4096 —— 记录之间存在对齐间隙。

### 2.4 其他容器

| 容器 | 结构 | 来源 |
|---|---|---|
| `HUMANS.afs` | 1,552 entry；块长 74,152；文本用 `A1D6/A1D7` 引号段，133 个；`MDCX` 34 个在文本区之后 | `parse_humans.txt`、`_parseh.txt` |
| `MEMODATA.BIN` | `MEMO` 头；count 5,412；数据基址 `0x5498`；CN 数据区 8,163 B、有效槽 2,534；JP 9,048 B | `memo_struct.txt` |
| `SYSTALK/FREETLK/COLD` | `SCNF` + `EXTR` 子容器 | `systlk_probe.txt` |
| `FREE01.afs` | 236 个 CHID 容器，24,777 条记录 | `xbp_err.txt` |

---

## 3. 内容盘点的真实规模

| 集合 | 数量 | 来源 |
|---|---|---|
| STREAM 对白记录 | 32,078（104 文件） | `master01.tsv`、`_stats_xbox.txt` |
| HUMANS 段 | 47,337 | `master_humans01.tsv` |
| 合计 | **79,415** | 上两行相加 |
| STREAM 说话者唯一 | 298（RYO_STDL 13,660） | `_stats_xbox.txt` |
| HUMANS 独立句 | 15,080；英文独立 14,626 | `_jp_match.txt`、`_humex.txt` |
| 第一章 AFS | 114 个 / 493 MB | `_mixall.txt` |
| 第一章 A1D6 台词段 | 47,439（英文 47,195、含日文 234） | `_scan01.txt` |

### 3.1 第一章主文本的状态（关键）

`_rem.txt` 对第一章 `@20` 主文本的分类：

| 状态 | 条数 |
|---|---|
| 已日文化（EUC） | **16,164** |
| 仍英文，无 EXTD（CLIP 型） | 848（FREE 库 846） |
| 仍英文，有 EXTD | 15,066 |
| 其它 | 82 |

也就是说，第一章有近一半的 `@20` 主文本已经是日文——这部份不是"英文待翻"，而是**引擎已在读日文**。后续所有"残留英文"统计都从 14,448 一路降到 6,786（`_statnow.txt` → `_statnow3.txt`），是逐步替换的结果。

残留英文独立句 5,854（`remaining_en_unique01.txt`），其中 FREE 库占 4,954、仅主线 900。长度分布：<12 字符 490、12–23 共 1,839、24–39 共 2,920、40–63 共 605。

### 3.2 `EXTD` 日文覆盖率（两个不同口径，勿混用）

| 口径 | 范围 | 数字 | 来源 |
|---|---|---|---|
| A：单文件"带日文记录" | FREE01 24,777 条 | 4,547 条含内嵌日文（18.4%）；其中 **4,541 / 4,547 = 99.9%** 与 DC 日版字节完全一致，未命中 6 | `xb_jp_extract.txt`、`盘1盘点.txt` |
| B：全库"日文台词对齐" | 340 个 AFS | 日文台词 43,168，按内容＋语种对齐命中 40,593 = **94.03%**；主线 334 文件 99.84% | 本仓库 `extd_align.py`（复算） |

口径 A 说的是"FREE01 里本来就只有 18.4% 的记录带日文母本，而这部分几乎 100% 与 DC 同源"；口径 B 说的是"把四章所有日文台词拿出来做对齐，命中率 94%"。**分母完全不同**，不能互相印证，也不能说"A 是 99.9% 所以 B 应该更高"。

### 3.3 对齐为何会错位（量化）

`_alignstat.txt` 按"英文长度 / 日文长度"比值标定可疑错位：

| 章 | 有日文记录 | 可疑错位 | 占比 |
|---|---|---|---|
| 01 | 11,531 | 2,153 | 18.7% |
| 02 | 19,558 | 3,335 | 17.1% |
| 03 | 21,588 | 3,515 | 16.3% |
| 04 | 2,287 | 521 | 22.8% |

`align_free01.txt`：DC 汉化 24,802 条 / DC 日版 24,802 条，说话者名 24,802 全同，字节完全相同 24,714 —— 剩下 88 条是 DC 汉化自己手改过的（`free01_edited88.tsv`、`ta2.txt`）。

`_align.txt`：Xbox FREE01 序列长度 **24,772** vs DC **24,802**，差 30 条 —— 少的是开场被删的记录，不是翻译差异。

---

## 4. 记录编排差异：必须按内容匹配

`struct_diag.txt` 给出逐文件的差异类型：

| 文件 | 中日条数 | 差异性质 |
|---|---|---|
| `0104KOW/SNN/SSA/SYO/SYY/YM1` | 52 / 53 | Xbox 少第 0 条 `RYO_STDL「落し玉、どうですか？」` |
| `0007.AFS` | 18 / 18 | 说话者整段错位，需 delete/replace/insert |
| `0015.AFS` | 49 / 49 | 同上，`日[17:19]` 对 `中[5:17]`，位置完全对不上 |

`name_diff.txt` 给出错位形态：`0007` 中文说话者序列是 `RYO×7, JOP×N`，日文是 `JOP, RYO, JOP, RYO…` 交替——DC 把分支对话集中排，Xbox 按台词流排。

`recheck.txt` 另记：`0104KOW` 等首句都是「落し玉、どうですか？」但中文容器 key 是 `[53]`，日文是 53 条/中文 52 条。

结论：**任何"按记录序号直灌"的方案都会在这 8 个文件上失败**，必须按 speaker + 内容做匹配。这与本仓库 `docs/extd.md` 的 71.68% 序号口径互相印证。

---

## 5. 容量：整条工程线的真正瓶颈

### 5.1 四章真超长句

`_cond.txt`（"真超长"= 日文 EUC 字节数超过该记录可用槽）：

| 章 | 真超长 | 平均超出 | 最大超出 |
|---|---|---|---|
| 01 | 6,065 | 10.0 B | 63 B |
| 02 | 9,613 | 10.4 B | 59 B |
| 03 | 9,560 | 10.0 B | 53 B |
| 04 | 1,041 | 4.9 B | 29 B |

需砍字节分布（第 01 章）：0–2 字节 703、2–4 共 898、4–8 共 1,583、8–14 共 1,459、14–24 共 958、24–40 共 394、40–70 共 70。

### 5.2 能不能原地救

`_insitu2.txt`（页尾/块尾零位移延长）：

| 章 | 可救 | 不可救 |
|---|---|---|
| 01 | 363 | 4,101 |
| 02 | 579 | 6,382 |
| 03 | 596 | 6,255 |
| 04 | 43 | 436 |

`_pg_01..04.txt`（页内重排、不延长块长）：

| 章 | 可容纳 | 放不下 |
|---|---|---|
| 01 | 382 句 | 4,584 句 |
| 02 | 638 | 7,087 |
| 03 | 803 | 6,804 |
| 04 | 290 | 318 |

### 5.3 中文侧的容量

中文普遍比英文短，但仍有一批放不下（`_fit_probe.txt`、`_fit2.txt`）：

- 可映射到官方表的记录 22,532 条
- 装得进 `cap-2` 的 17,670 条（78.4%）
- 超出 4,862 条（21.6%），其中 FREE01 占 4,136

DC 汉化自身的中文容量：`_cnstat.txt` —— 7,121 行译文、72,415 个双字节字符、去重 1,679 槽、越界 0。符号用量：`A1F5` 换行 2,340、`A1A3` 句号 4,828、`A1A2` 逗号 2,623、`A1C4` 省略号 1,965、`A1A9` 问号 1,087、`A1AA` 引号 1,282、`A1A1` 顿号 267。

---

## 6. 写盘实现与实测结果

### 6.1 已实现的工具链（脚本清单）

| 阶段 | 脚本 | 作用 |
|---|---|---|
| 枚举 | `enum_classify01.py`、`enum_humans01.py`、`enum_tags.py`、`enum_xdvdfs.py` | 生成 `master01.tsv`、`master_humans01.tsv`、标签统计 |
| 结构 | `afs_validate.py`、`scene_audit.py`、`analyze_clip.py`、`check_gap.py` | CHID/AFS 结构与间隙校验 |
| 对齐 | `align_free01.py`、`align_seq_free.py`、`stat_align.py`、`analyze_jpfit.py` | 序号/内容/语音 ID 三种对齐 |
| 容量 | `analyze_pack.py`、`analyze_page.py`、`analyze_repack.py`、`stat_insitu2.py`、`free_budget.py`、`slack_plan.py` | 槽位预算与重排可行性 |
| 构建 | `build_stage1.py`、`build_stageB.py`、`build_stageC.py`、`free_rebuild2.py` | 块内重排 / 分页打包 / FREE 大库重建 |
| 日文回填 | `build_stream_jp.py`、`build_stream_jp2.py`、`gen_fixed.py`、`build_safe.py` | 英文→日文（规则翻译 / 等长替换） |
| HUMANS | `build_humans_jpA.py`、`build_humans_jpB1.py`、`build_humans_manual.py`、`build_humans_greet.py`、`build_humans_cn.py` | A 批 / B1 缩约 / 人工映射 / 寒暄 / 中文 |
| 中文 | `build_stream_cn.py`、`apply_trans01.py`、`apply_cold_font.py`、`build_cn_poc.py` | STREAM 中文灌入、字库替换、PoC |
| 校验 | `verify_safe.py`、`verify_stageB.py`、`verify_stageC.py`、`verify_stageC2.py`、`verify_cold.py`、`verify_jp_full.py` | 独立回读比对 |

### 6.2 回读校验通过记录（旧记录）

| 操作 | 结果 | 来源 |
|---|---|---|
| 阶段 B 块内重建 130 块、救回 4,203 句 | 写回 0 不符 | `_b2_apply.txt` |
| 阶段 B 二次 134 块、救回 4,357 句 | 写回 0 不符 | `_stageB_apply.txt` |
| 阶段 C 分页打包 106 块、救回 3,372 句 | 回读/目录 0 不符 | `_c_apply.txt` |
| 安全等长 6,566 句 + padding 501 句 | 153 块 0 不符、XDVDFS 差异 0 | `_b2_safe.txt`、`_ref_safe.txt` |
| HUMANS 日文 A 批 34,434 段 | 335 块 0 不符、块长不变 | `_jpA2.txt` |
| HUMANS 寒暄补丁 2,254 段 | 335 块 0 不符 | `_greetA.txt` |
| 人工映射 89→2,360 条分 30+ 批 | 每批均 0 不符 | `_man1.._manApp4.txt` |
| STREAM 日文回填 7,581 句 | 306 块 0 不符 | `_sjApp.txt` |
| 尾部空格转 00（6 句） | 2 块 0 不符 | `_fixpad2.txt` |
| 阶段 B 验收 | 变长块 130、超长记录 4,687、违规 0 | `_b2_verify.txt` |

### 6.3 失败与修复记录（重要，说明不是纸面方案）

- `_vc.txt`：0005 等 31 条回读不符（"ワンチャイを＆探してるんだ。探してます。" 被拼串）→ 换成 `_vc3.txt` 的严格重打包后 0 不符。
- `_vc2.txt`：超槽块被改动（FREE01 876/7276/7862/8481/8740），重算 24 条不符 → FAIL，随后用页级方案修正。
- `_stuck.txt`：仍有 68 个文件待写，最小复现 `0005.AFS`（1 句、槽 4/需 4）。
- `_vnew.txt`：`already 4,546 / overflow 1,127 / jp_left 401 / empty_cn 6` —— 401 条日文残留是明确缺口。

---

## 7. 字库

### 7.1 三处字节同一

| 位置 | 大小 | MD5 |
|---|---|---|
| `misc/dc_kanji.fon` | 351,270 | `8669109EE72543CDEF91305A6D0CA018` |
| DC 日版四碟 `DC_KANJI.FON` | 351,270 | 同上 |
| `misc/COLD.BIN@15328` 嵌入段 | 351,270 | 同上 |

### 7.2 只有一处生效（实机）

2026-10-22 xemu 0.8.138 实测：替换 `misc/dc_kanji.fon` 后字幕**无变化**；替换 `COLD.BIN@15328` 后立即显示简体。`verify_cold.py` 逐字节比对 `diff=0`。

- `COLD.BIN` lba 66689 / 591,964 B，内嵌汉字库整段只出现 1 次。
- 全盘 10,219 文件枚举后，351,270 B 的独立 FON 只有 `misc/dc_kanji.fon` 一个（`scan_fonts.py`、`_fonts.txt`）。

### 7.3 RYOU.FON 的真实身份（与早期说法不同）

`font_diff.txt` 实测：

| 对比 | 不同槽 |
|---|---|
| 汉化 KANJI vs Xbox 原版 KANJI | 2,965 / 7,806 |
| 汉化 RYOU vs 汉化 KANJI | 3,704 / 7,806 |
| 汉化 RYOU vs Xbox 原版 KANJI | 2,775 |

`gaps_free01.txt`、`gaps2_free01.txt` 进一步说明：FREE01 24,802 条里有 82 种字形槽在 KANJI 库中为空、合计命中 12,480 次；其中 **81 种在 RYOU 库里有字（12,231 次）**，只有 1 种（`A1A1` 顿号，249 次）两库皆空。

也就是说：DC 版的 `RYOU.FON` 是 **351,270 B / 7,806 槽的第二套完整字库**，与 `DC_KANJI.FON` 分工互补（KANJI 缺的字由 RYOU 补），而不是"符号与部件表"。Xbox 美版把这个文件缩成 7,680 B（256 槽），丢掉的正是这套互补字形。

> 修正：本仓库早期版本（及最初的证据报告）把 DC 的 `RYOU.FON` 描述为"45 B/ 槽的符号+汉字部件表"，与 `font_diff.txt` 的实测不符，已在此更正。

### 7.4 假名字库

`dc_kana.fon` 两边都是 7,680 B：174/256 槽相同，82 槽不同。
Xbox 版差异槽：43、124、129–153、166–175、177–221，内容是 `Á â ü è é ë` 与 `▲★☎✿◆■♠♣↓→` 一类西文重音/图标符号。
DC 版同槽是半角片假名。

### 7.5 换库的硬约束（实机实证）

替换为汉化字库后，**仍是日文的句子会把汉字显示成错字**：

```
「桃李少老師は、ここに…」  →  「洪李绪老点は、ここに…」
```

（桃→洪、少→绪、師→点；假名不受影响，走 `dc_kana.fon`）

污染规模：`_mix.txt` 记录 cnpoc 镜像混排句 **908** 条；`_mixall.txt` 记录全第一章 **9,016** 条。

因此：字库替换必须与"全量日文→中文码位"同步完成，不能先换库后翻文本，也不能日中混排。

### 7.6 四碟字库不同

| 盘 | `DC_KANJI.FON` MD5 |
|---|---|
| Disc 1 | `a0a50d508d5f…` |
| Disc 2 / 4 | `7FF0C2CC17CE…` |
| Disc 3 | `AD1753305437…` |

按章写盘须选对应字库，或先合并字形集（`_fblob.txt`、`中文PoC结论_COLD字库.md`）。

### 7.7 第一章全量缺字终检

`第一章全量缺字终检报告.md`：

| 项 | 数值 |
|---|---|
| 含文本 AFS | 106 |
| CHID 主文本记录 | 32,418 |
| 双字节总字数 | 440,329 |
| 去重字形槽 | 2,303 |
| 越界槽（≥7,806） | 0 |
| 常用汉字区真缺字 | **0** |

82 个空槽全部非中文缺字：81 个位于 slot ≥ 3,600（JIS 第二水准生僻字，只出现在未译日文句），1 个是 slot 0 / `A1A1` 顿号。

> 与"需补 1,118 字形"的区别：后者是"繁中母表总用字 vs 现有简体库"的口径（面向重制版母表移植）；前者是"第一章实际译文 vs DC 汉化 Disc1 字库"的口径。第一章实测缺字为 0。

---

## 8. HUMANS：被低估的另一半

### 8.1 对齐全貌

`_jpfit.txt`：

| 项 | 数值 |
|---|---|
| entry 总数 | Xbox 1,552 / DC 1,552 |
| 段数不一致 entry | 23 |
| 顺序/vid 不完全一致 entry | 343 |
| 全对齐 entry | 1,209 |
| 可比对段 | 47,339 |
| 语音 ID 同序命中 | 45,944（**97.1%**） |
| EUC 解码失败 | 8 |

换行字节统计（关键差异）：

| 平台 | `A1F5` | `0D` | `0A` |
|---|---|---|---|
| 美版 | 15,911 | 956 | 845 |
| 日版 | 1 | 491 | 15,213 |

即：DC 日版主要用 `0A` 换行，Xbox 用 `A1F5`。文本搬运时必须换符。

`_jp_match.txt`：

| 集合 | 唯一句 | 精确命中官方表 | 覆盖率 |
|---|---|---|---|
| HUMANS | 15,080 | 10,727 | 71.1% |
| STREAM | 19,180 | 2,770 | 14.4% |

HUMANS 命中率远高于 STREAM，因为 HUMANS 的日文母本是**逐段内嵌**的（同 entry 同语音 ID），而 STREAM 要靠外部对齐。

### 8.2 已写入的部分

| 批次 | 规模 | 结果 |
|---|---|---|
| A 批（vid 对齐 34,200 + 顺序 234） | 34,434 段 | 335 块 0 不符，块长全部未变 |
| 超长留 B 批 | 12,901 句 | `humans_overflow01.tsv` |
| 寒暄补丁（Excuse me / I see / yes…） | 2,254 段 | 335 块 0 不符 |
| 人工映射（89→2,360 条，30+ 批） | 数千句 | 每批 0 不符 |

`_page` / `_exc.txt`：A 批后仍有 462 段含 "excuse me"，原因多为超 1–10 字节（`Excuse me.` 槽 10B / 日文 12B）。

### 8.3 B1 缩约（不改语义的压缩）

`_B1.txt` → `_B18.txt` 是一轮迭代序列，每轮减少待人工句数：

| 轮次 | 救回 | 仍需 B2 | 改动块 |
|---|---|---|---|
| B1 | 2,251 | 8,386 | 315 |
| B15/B15A | 1,464 | 7,068 | 278 |
| B16 | 24 | 7,044 | 24 |
| B17 | 184 | 6,860 | 109 |
| B18 | 1,244 | 5,800 | 301 |
| 最终 | — | 61 → 2 | — |

规则使用次数（B1 轮）：`r_period` 2,090、`r_final_particle` 529、`r_longuowel` 184、`r_kudasai` 193、`r_filler` 145、`r_desu` 94。全部只做不改义的收缩（句号省略、终助词、长音符、省略语）。

### 8.4 DC 汉化 HUMANS 不可直取（确认）

`_hcn.txt`：Xbox 块 1,552 / DC 块 1,552 / 对齐遍历 1,552，但 `cn_target 0`、`by_vid 0`、`by_seq 0`、`fits 0` → 可写改动块 **0**。

`_dc1full.txt`：DC 汉化 `HUMANS.AFS` 文本记录 **0** —— 整个文件被私压缩/改结构，CHID 扫描不到任何文本。

`analyze_yzb.py`、`find_plaintext_cn.py`、`diag_yzb.py` 均尝试解压，zlib/lz4/gzip 全失败。结论：HUMANS 的中文只能自己产，不能从 DC 汉化搬。

---

## 9. 中文 PoC（实机通过）

`中文PoC结论_COLD字库.md`：

- 镜像：`SM2HH\_TEST_cnpoc.iso`
- 写入：① `COLD.BIN@15328` 换成 Disc1 汉化字库（生效）；② `misc/dc_kanji.fon` 同时换（无效但无害）；③ `0005.AFS` entry 33 的 rk0 / rk2 主文本 = 「先要找到湾仔啊。」，码位 `b1e1bfedb7f3b2c0bbbab0efb4a4a1a3`
- 实机：字幕清晰显示简体，开场不卡死；纸条特写与海湾背影两处均拍到。

`PoC补丁清单.txt`：FREE01 #55 共灌 41 句开场导航台词，回读 41 全通过。
`PoC补丁清单_0005.txt`：0005 开场过场 16 句，成功 16、失败 0。

PoC 之后的逐条对照 `_cmp5.txt`：Xbox 侧主文本已是中文、`EXTD` 仍为日文；DC 汉化侧重文本为中文。

---

## 10. 尚未解决 / 未验证

| 项 | 状态 | 依据 |
|---|---|---|
| 四章超长句容量 | 不可救 4,101 / 6,382 / 6,255 / 436 | `_insitu2.txt` |
| HUMANS 超长 | 12,901 句留 B 批 | `_jpA.txt` |
| 待写文件 | 68 个（最小复现 0005） | `_stuck.txt` |
| 日文残留 | 401 条 | `_vnew.txt` |
| MEMODATA 笔记本 | 结构已知（5,412 条 / CN 8,163 B），未做写回 | `memo_struct.txt`、`memo_block_cmp.txt` |
| SCNF（SYSTALK/FREETLK） | 仅探针（日文可读 3,438 串） | `systlk_probe.txt` |
| 贴图文字 | 纸条/招牌属 SPR 图层，需重绘 | 实机截图，未处理 |
| 四碟字库合并 | 三组 md5，未合并 | `_fblob.txt` |

---

## 11. 本仓库（2026-11-24）复算了什么

只有以下四项是现场重跑，其余均为上文转述：

1. 三处字库 MD5 完全相同（Xbox / DC 四碟 / `COLD.BIN@15328`）
2. `dc_kana.fon` 174/256 槽一致、82 槽差异
3. `RYOU.FON` 美版 7,680 B / 256 槽，DC 351,270 B / 7,806 槽，DC 内无匹配片段
4. 340 个 AFS / 43,168 条日文台词 / 主线 99.84%（口径 B）

未复算但已转述的实机结论（第 7.2、7.5、9 节）建议在发布前用干净镜像再验一次。

---

## 12. 源文件索引

| 主题 | 文件 |
|---|---|
| 全盘对比 | `dc_xb_compare.txt`、`filelist.tsv`、`_enum3.txt`、`_enum4.txt` |
| 容器结构 | `afs_scan.txt`、`_clip.txt`、`0007_strict.txt`、`0015_strict.txt`、`_tags.txt` |
| 内容盘点 | `master01.tsv`、`master_humans01.tsv`、`_rem.txt`、`_statnow3.txt`、`_uniq.txt` |
| 对齐 | `xb_jp_extract.txt`、`align_free01.txt`、`_alignstat.txt`、`_jpfit.txt`、`_jp_match.txt` |
| 编排差异 | `struct_diag.txt`、`name_diff.txt`、`recheck.txt` |
| 容量 | `_cond.txt`、`_insitu2.txt`、`_pg_01..04.txt`、`_fit2.txt`、`_cnstat.txt` |
| 写盘 | `_b2_apply.txt`、`_stageB_apply.txt`、`_c_apply.txt`、`_b2_safe.txt`、`_vc3.txt` |
| 字库 | `xb_font_cmp.txt`、`font_diff.txt`、`gaps2_free01.txt`、`verify_cold.txt`、`_cnpoc.txt` |
| PoC | `中文PoC结论_COLD字库.md`、`PoC补丁清单.txt`、`PoC补丁清单_0005.txt`、`_mix.txt` |
| HUMANS | `build_humans_jpA.py`、`_jpA2.txt`、`_B1.._B18.txt`、`humans_overflow01.tsv`、`_hcn.txt` |
| 笔记本 | `memo_struct.txt`、`memo_block_cmp.txt`、`memo_jp_clean.txt`、`memo_render.py` |
| 重制版母表 | `_probe_sh2subs.txt`、`_stats_subs.txt`、`stats_subs.py` |
