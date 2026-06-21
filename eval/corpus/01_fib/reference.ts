// 正例（陽性対照）: input.js を型注釈つき TypeScript へ変換した「正しい」変換。
// オラクルはこれを PASS と判定できなければならない（自己検証）。
function fib(n: number): number {
  if (n < 2) return n;
  return fib(n - 1) + fib(n - 2);
}

console.log([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(fib).join(','));
