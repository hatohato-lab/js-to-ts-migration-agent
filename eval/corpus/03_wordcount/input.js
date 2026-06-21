// クリーンルーム純粋関数: 単語の出現回数を数え、頻度降順 → 名前昇順に並べる。
function wordCount(text) {
  const counts = {};
  for (const w of text.toLowerCase().split(/\s+/).filter(Boolean)) {
    counts[w] = (counts[w] || 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

console.log(wordCount('the cat the dog the bird cat').map(([w, c]) => `${w}:${c}`).join(' '));
