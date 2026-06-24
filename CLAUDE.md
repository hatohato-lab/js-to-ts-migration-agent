# CLAUDE.md — js-to-ts-migration-agent

このリポジトリは「JavaScript を等価な TypeScript へ移行する」エージェントと、その採点係（差分テスト）です。
正しさは、元の JavaScript を実行した出力を基準に、移行後の TypeScript の出力が一致するかで判定します。

## 確認のしかた

- `python eval/oracle.py --selftest` … 採点係が正しいか（正しい移行=PASS／壊した移行=FAIL）
- `python eval/oracle.py --candidate candidate` … 各ケースの candidate.ts を採点
- `python eval/oracle.py` … お手本(reference.ts)を採点

## いじるときの約束（評価駆動 / EDD）

- 先に eval（合否の基準）を満たすことを確認してから「完成」とする。雰囲気で done にしない。
- `eval/corpus/<ケース>/` の `reference.ts`・`input.js`・`golden.txt` は採点の基準。むやみに変えない。
- 実行には Node.js と TypeScript(tsc) が必要（`node_modules/typescript`）。秘密情報・個人情報・客先コードを入れない。

## ファイルの役割

- `.claude/agents/js-to-ts-migration-agent.md` … エージェント定義
- `eval/oracle.py` … 採点係（差分テスト）／`design/design.md` … 設計／`README.md` … 説明
