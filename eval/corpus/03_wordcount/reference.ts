function wordCount(text: string): [string, number][] {
  const counts: Record<string, number> = {};
  for (const w of text.toLowerCase().split(/\s+/).filter(Boolean)) {
    counts[w] = (counts[w] || 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

console.log(wordCount('the cat the dog the bird cat').map(([w, c]) => `${w}:${c}`).join(' '));
