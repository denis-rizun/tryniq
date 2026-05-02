export type Token =
  | { kind: 'space'; text: string; key: number }
  | { kind: 'word'; text: string; low: boolean; idx: number; key: number };

export const splitWords = (text: string, lowIdx: number[] = []): Token[] => {
  const parts = text.split(/(\s+)/);
  let wIdx = 0;
  return parts.map<Token>((p, i) => {
    if (/^\s+$/.test(p)) return { kind: 'space', text: p, key: i };
    const out: Token = {
      kind: 'word',
      text: p,
      low: lowIdx.includes(wIdx),
      idx: wIdx,
      key: i,
    };
    wIdx++;
    return out;
  });
};
