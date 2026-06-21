// クリーンルーム純粋関数: フィボナッチ数列（再帰）。客先案件の要素は一切含まない。
function fib(n) {
  if (n < 2) return n;
  return fib(n - 1) + fib(n - 2);
}

console.log([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(fib).join(','));
