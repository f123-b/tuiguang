#!/usr/bin/env python3
"""Read *sanitized* JSONL trace receipts and produce an evidence-only report.

No network, no model calls, no production actions. This is a starter example.
"""
import argparse, json, re
from pathlib import Path

SAFE=re.compile(r"^[a-zA-Z0-9_.:-]{1,128}$")
REQUIRED={"trace_id","creator_run_id","stage","status","release_id","event_time"}

def collect(path,run_id):
    if not SAFE.fullmatch(run_id):
        raise ValueError("run id must be alphanumeric with _ . : -")
    events=[]
    with open(path,encoding="utf-8") as stream:
        for ln,row in enumerate(stream,1):
            if not row.strip(): continue
            x=json.loads(row)
            if not isinstance(x,dict) or not REQUIRED.issubset(x):
                raise ValueError(f"invalid event schema at line {ln}")
            if x["creator_run_id"]==run_id: events.append(x)
    return sorted(events,key=lambda x:x.get("event_time", ""))

def _safe_cell(s):
    # Never echo arbitrary evidence from a foreign log into the report.
    return str(s or "-").replace("|","/").replace("\n"," ")[:160]

def report(run_id,events):
    out=[f"# 诊断报告：{run_id}","","> 仅从提供的脱敏样例事件归纳事实；不是自动根因确认，更没有任何生产修复。","",f"事件数：{len(events)}",""]
    if not events:return "\n".join(out+["未找到这个任务 ID 的日志，不能推断错误原因。"])
    out += [f"Trace ID：`{_safe_cell(events[0].get('trace_id'))}`",f"运行发行：`{_safe_cell(events[0].get('release_id'))}`", "", "| 阶段 | 状态 | 镜头 | 错误码 |", "|---|---|---|---|"]
    for x in events:
        out.append(f"| {_safe_cell(x['stage'])} | {_safe_cell(x['status'])} | {_safe_cell(x.get('shot_id'))} | {_safe_cell(x.get('error_code'))} |")
    failures=[x for x in events if x.get("status")=="error"]
    out += ["", "## 失败事件（仅观察）"]
    if not failures:out.append("所给事件中没有显式失败；不代表整体任务已完成。")
    for x in failures:
        out.append(f"- **阶段** `{_safe_cell(x['stage'])}`；**镜头** `{_safe_cell(x.get('shot_id'))}`；**错误码** `{_safe_cell(x.get('error_code'))}`；**Provider** `{_safe_cell(x.get('provider'))}`。")
        # Avoid untrusted raw log content, show only an evidence fingerprint placeholder.
        if x.get("evidence"):
            out.append("  - 收到证据摘要（原文已省略；应在有权限的观测平台核实）。")
    out += ["", "## 下一步", "1. 在有权限的日志平台查看相关 trace 的首次失败 span 和脱敏错误原文。", "2. 将当前发行号与 Provider/模型/Prompt/镜头版本进行关联。", "3. 在隔离环境使用合法测试资产复现；若未复现，收集更多指标。", "4. 修复后运行相关回归测试；生产操作仍须人工审批。", "", "**结论：尚无充分证据证明最终根因。**"]
    return "\n".join(out)+"\n"

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument('--input',required=True,type=Path)
    a.add_argument('--run-id',required=True)
    a.add_argument('--out',required=True,type=Path)
    args=a.parse_args()
    text=report(args.run_id,collect(args.input,args.run_id))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(text,encoding="utf-8")
    print(f"已生成脱敏诊断示例报告：{args.out}")
