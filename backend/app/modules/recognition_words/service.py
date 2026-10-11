# -*- coding: utf-8 -*-
"""识别词生成：锚点 → 正则 → 规则文本的组装逻辑。

对应原桌面工具 MainWindow 中 _rule_for / _current_rules / _refresh_output 的业务部分。
"""

import datetime

from .anchor import build_anchor, is_anchor_valid
from .pattern import build_pattern
from .schemas import AnchorRow, GenerateRequest, GenerateResponse


def build_rule(anchor: str, tmdbid: str, mtype: str, season: str,
               loose: bool, boundary: bool) -> str:
    tmdb = (tmdbid or "").strip() or "xxxx"
    sn = (season or "").strip() or "x"
    pattern = build_pattern(anchor, loose, boundary)
    return f"{pattern} => {{[tmdbid={tmdb};type={mtype};s={sn}]}}"


def generate_rules(req: GenerateRequest) -> GenerateResponse:
    filenames = [line.strip() for line in req.filenames if line and line.strip()]

    # 锚点：请求带 anchors（前端手动编辑过）则原样使用，否则按文件名自动提取
    manual = req.anchors is not None and len(req.anchors) == len(req.filenames)
    anchors: list[str] = []
    for i, line in enumerate(req.filenames):
        if not line or not line.strip():
            continue
        if manual:
            anchors.append((req.anchors[i] or "").strip())
        else:
            anchors.append(build_anchor(line, req.keep_group))

    # 按锚点去重、保持顺序，生成规则
    rules: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in anchors:
        if not anchor or anchor in seen:
            continue
        seen.add(anchor)
        rules.append((anchor, build_rule(anchor, req.tmdbid, req.mtype, req.season,
                                         req.loose, req.boundary)))
    rule_of = dict(rules)

    rows = [
        AnchorRow(filename=name, anchor=anchor,
                  valid=bool(anchor) and is_anchor_valid(anchor),
                  rule=rule_of.get(anchor, ""))
        for name, anchor in zip(filenames, anchors)
    ]

    lines = [rule for _, rule in rules]
    if rules and req.date_comment:
        lines.insert(0, f"#[自动生成] {datetime.date.today().isoformat()}")
    rules_text = "\n".join(lines)

    warnings: list[str] = []
    bad = [a for a, _ in rules if not is_anchor_valid(a)]
    if bad:
        warnings.append("锚点过短可能误伤其他文件，请手动修改锚点后再使用：" + "、".join(bad))

    hint = ""
    if rules:
        mode_hint = ("宽松匹配：空格/点/横线/下划线/· 等分隔符互相等价，可省略；冒号全/半角等价。"
                     if req.loose else
                     "绝对匹配：逐字符字面对应，空格数量与符号必须完全一致。")
        hint = f"共 {len(rules)} 条规则（{mode_hint}）tmdbid / s 里的 xxxx / x 请替换为真实值后使用。"

    return GenerateResponse(rules_text=rules_text, rows=rows, warnings=warnings, hint=hint)
