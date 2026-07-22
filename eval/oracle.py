#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle.py — JavaScript → TypeScript 移行（migration）エージェントの決定的オラクル（差分テスト）。

評価基準は「元の JavaScript（input.js）を実行した出力」そのもの。
候補となる移行後コード（.ts）が、各 corpus ケースについて
  (a) tsc --strict でコンパイルが通り、かつ
  (b) node で実行すると、元の input.js と同じ標準出力になる
ときだけ PASS とする。
＝ 差分テスト（differential testing）：元のプログラム自身をオラクルにする。
手書きの期待値を使わないので、人手のズレが入らない。LLM 審査なし・乱数なし・完全に決定的。

golden.txt は「元の出力の控え（人が読む用の記録）」。--selftest で
input.js の実行出力と一致するか検証し、控えが古びていないかを確認する。

使い方:
  python oracle.py                  # 各ケースの reference.ts（正例＝陽性対照）を採点
  python oracle.py --candidate NAME # 各ケースの NAME.ts（エージェントの出力）を採点
  python oracle.py --selftest       # オラクル自身を検証（正しい移行→PASS / 壊れた移行→FAIL ＋ 控え整合）

終了コード: 全ケース PASS（または selftest が期待どおり）で 0、それ以外 1。
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows コンソール(cp932)でも日本語・記号を出せるよう出力を UTF-8 に統一。
# Linux/Mac は元から UTF-8 なので無害。これが無いと Windows で print が落ちる。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

LANG = "JavaScript → TypeScript（移行）"
EXT = ".ts"
REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(__file__).resolve().parent / "corpus"
# subprocess の上限秒数。移行ミスで無限ループ化した candidate を採点しても
# オラクルがハングしないための安全弁。超過は FAIL 扱い。
TIMEOUT_SEC = 30
# tsc に渡すコンパイルフラグ。★実際に効くのはここ★
# オラクルは tsc にファイル名を直接渡すため、tsc の仕様で tsconfig.json は読まれない。
# ルートの tsconfig.json はエディタ（VS Code 等）用の鏡写しであり、
# フラグを変えるときは必ず両方を同じ内容に揃えること。
TSC_FLAGS = ["--target", "es2020", "--module", "commonjs",
             "--strict", "--noEmitOnError", "--skipLibCheck"]
# selftest 用の汎用ミューテーション（ファイル非依存で壊す）
OUTPUT_BREAK = '\nconsole.log("__ORACLE_SELFTEST_EXTRA__");\n'
COMPILE_BREAK = '\nconst __oracle_selftest_broken__: = ;\n'


def run_node(js_src: Path):
    """JavaScript ファイルを node で実行して stdout を返す。(ok, stdout, detail)"""
    try:
        rp = subprocess.run(["node", str(js_src)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        return (False, "", f"タイムアウト: node 実行が {TIMEOUT_SEC} 秒を超過（無限ループの疑い）")
    if rp.returncode != 0:
        return (False, "", "node 実行エラー: " + rp.stderr.strip().replace("\n", " ")[:160])
    return (True, rp.stdout, "ok")


def compile_and_run(src: Path, workdir: Path):
    """TypeScript をコンパイル＆実行して stdout を返す。(ok, stdout, detail)"""
    tsc = REPO_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
    if not tsc.exists():
        return (False, "", "typescript 未インストール（repo 直下で npm install -D typescript）")
    try:
        cp = subprocess.run(
            ["node", str(tsc), str(src), "--outDir", str(workdir), *TSC_FLAGS],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return (False, "", f"タイムアウト: tsc コンパイルが {TIMEOUT_SEC} 秒を超過")
    if cp.returncode != 0:
        msg = (cp.stdout + cp.stderr).strip().replace("\n", " ")
        return (False, "", "tsc: " + msg[:160])
    js = workdir / (src.stem + ".js")
    if not js.exists():
        found = list(workdir.rglob(src.stem + ".js"))
        if not found:
            return (False, "", "コンパイル後の .js が見つからない")
        js = found[0]
    try:
        rp = subprocess.run(["node", str(js)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        return (False, "", f"タイムアウト: node 実行が {TIMEOUT_SEC} 秒を超過（無限ループの疑い）")
    if rp.returncode != 0:
        return (False, "", "node 実行時エラー: " + rp.stderr.strip().replace("\n", " ")[:160])
    return (True, rp.stdout, "ok")


def case_golden(case_dir: Path):
    """評価基準＝元の input.js を実行した出力（差分テスト）。(ok, golden, detail)"""
    inp = case_dir / "input.js"
    if not inp.exists():
        return (False, "", "input.js が無い")
    return run_node(inp)


def grade_against(src: Path, golden: str):
    """候補 src(.ts) を採点し、golden（元の出力）と比較する。"""
    if not src.exists():
        return ("FAIL", f"{src.name} が無い")
    with tempfile.TemporaryDirectory() as td:
        ok, out, detail = compile_and_run(src, Path(td))
    if not ok:
        return ("FAIL", detail)
    if out.strip() == golden.strip():
        return ("PASS", "ok")
    return ("FAIL", f"出力不一致: got={out.strip()!r} want(元の出力)={golden.strip()!r}"[:160])


def grade(case_dir: Path, candidate: str):
    ok, golden, dg = case_golden(case_dir)
    if not ok:
        return ("FAIL", "元(input.js)の実行に失敗: " + dg)
    return grade_against(case_dir / f"{candidate}{EXT}", golden)


def cases():
    return sorted(p for p in CORPUS.iterdir() if p.is_dir())


def grade_all(candidate: str):
    rows, allpass = [], True
    for c in cases():
        verdict, detail = grade(c, candidate)
        rows.append((c.name, verdict, detail))
        allpass = allpass and verdict == "PASS"
    return rows, allpass


def print_table(rows, title):
    print(f"\n### {title}")
    print("| ケース | 判定 | 詳細 |")
    print("|---|---|---|")
    for name, verdict, detail in rows:
        print(f"| {name} | {verdict} | {detail} |")
    npass = sum(1 for _, v, _ in rows if v == "PASS")
    print(f"\n小計: {npass}/{len(rows)} PASS")
    return npass == len(rows)


def check_golden_snapshot():
    """控え golden.txt が、元 input.js の実行出力と一致するか検証する。"""
    rows, allok = [], True
    for c in cases():
        g = c / "golden.txt"
        ok, live, dg = case_golden(c)
        if not ok:
            rows.append((c.name, "FAIL", dg)); allok = False; continue
        if not g.exists():
            rows.append((c.name, "—", "golden.txt 無し")); continue
        match = g.read_text(encoding="utf-8").strip() == live.strip()
        allok = allok and match
        rows.append((c.name, "PASS" if match else "FAIL",
                     "ok" if match else "控えが元の出力とズレている"))
    return rows, allok


def selftest():
    print(f"# オラクル自己検証 — {LANG}・差分テスト")
    rows, good_ok = grade_all("reference")
    print_table(rows, "① 正しい移行 reference（元の出力と一致＝PASS であるべき）")

    # 負例ミューテーションは全ケースに適用する（先頭ケースだけでは検証が偏るため）。
    brk_rows, breaks_ok = [], True
    for c in cases():
        ok_g, golden_c, dg = case_golden(c)
        if not ok_g:
            brk_rows.append((c.name, "FAIL", "元(input.js)の実行に失敗: " + dg))
            breaks_ok = False
            continue
        ref = (c / f"reference{EXT}").read_text(encoding="utf-8")
        for label, mut in [("出力破壊", OUTPUT_BREAK), ("構文破壊", COMPILE_BREAK)]:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / f"broken{EXT}"
                p.write_text(ref + mut, encoding="utf-8")
                verdict, _ = grade_against(p, golden_c)
            ok = verdict == "FAIL"
            breaks_ok = breaks_ok and ok
            brk_rows.append((f"{label}({c.name})", verdict, "期待=FAIL " + ("OK" if ok else "NG オラクル不良")))
    print_table(brk_rows, "② 壊れた移行（全ケース・FAIL であるべき）")

    snap_rows, snap_ok = check_golden_snapshot()
    print_table(snap_rows, "③ 控え golden.txt が元の出力と一致するか（基準の点検）")

    valid = good_ok and breaks_ok and snap_ok
    print(f"\n## オラクル判定: {'PASS（信頼できる外部オラクル）' if valid else 'FAIL（オラクル自体に欠陥）'}")
    return valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="reference",
                    help="採点する候補ファイル名（拡張子なし）。既定=reference")
    ap.add_argument("--selftest", action="store_true", help="オラクル自身を検証")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    rows, allpass = grade_all(a.candidate)
    ok = print_table(rows, f"採点: {a.candidate}{EXT}（{LANG}・差分テスト）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
