# E-01 fixture — `slugify` specification (normative for this fixture)

Implement `slugify(text)` in `fixture/e01/normalize.py`. Python 3 standard library only.

1. If `text` is not a `str`, raise `TypeError`.
2. Normalize with Unicode NFKD, then drop every character that cannot be encoded as ASCII
   (this removes accents: `"Café"` → `"Cafe"`).
3. Lowercase the result.
4. Every maximal run of characters that are not `a`–`z` or `0`–`9` becomes a single hyphen `-`.
5. Remove leading and trailing hyphens.
6. If the result is longer than 40 characters, cut it to its first 40 characters and then remove any
   trailing hyphens again.
7. If the final result is empty, raise `ValueError`.

Examples:

| input | output |
|---|---|
| `"Hello, World!"` | `"hello-world"` |
| `"  Café  crème  "` | `"cafe-creme"` |
| `"a---b___c"` | `"a-b-c"` |
| `"Ünïcödé 2026"` | `"unicode-2026"` |
| `"!!!"` | `ValueError` |
| `123` | `TypeError` |
