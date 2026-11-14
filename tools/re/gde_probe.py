"""gde probe: counts in the translation DB used by the translators' notes (read-only)."""
import glob, json, re, sys, os
pats = {
 "san": r"\b[A-Za-z#]+-san\b|\bsan\b", "kun": r"-kun\b", "sama": r"-sama\b", "senpai": r"senpai|sempai",
 "kyu": r"\d+-kyu", "dan": r"\d+-dan", "gun": r"-gun\b", "cho": r"-cho\b", "mura": r"-mura\b",
 "oku": r"\bOku\b", "man": r"\bMan\b", "yen": r"\bYen\b", "Ymoney": r"\bY\d", "10k": r"10k",
 "ginga": r"Ginga", "Mr": r"\bMr\.", "pref": r"Pref\.",
}
cnt = {k: 0 for k in pats}; ex = {k: [] for k in pats}
total = tr = 0
for f in glob.glob("translation/*.jsonl"):
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        r = json.loads(line); total += 1
        en = r.get("en") or ""
        if en and not r.get("skip"): tr += 1
        for k, p in pats.items():
            if re.search(p, en):
                cnt[k] += 1
                if len(ex[k]) < 4: ex[k].append(en.replace("\n", " / ")[:70])
print("records", total, "translated", tr)
for k in pats: print(k, cnt[k], ex[k])
