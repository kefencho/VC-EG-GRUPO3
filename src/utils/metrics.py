"""
Métricas de evaluación del sistema (según la propuesta):
    - Detección de regiones: mAP, precision, recall  (delegado a Ultralytics val)
    - Reconocimiento: CER (Character Error Rate), WER (Word Error Rate)
    - Desempeño general: exactitud por campo y por documento
"""
from __future__ import annotations


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1,
                                     prev + (a[i - 1] != b[j - 1]))
    return dp[n]


def cer(ref: str, hyp: str) -> float:
    """Character Error Rate."""
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def wer(ref: str, hyp: str) -> float:
    """Word Error Rate."""
    r, h = ref.split(), hyp.split()
    if not r:
        return 0.0 if not h else 1.0
    return _levenshtein(" ".join(r), " ".join(h)) / max(1, len(r))


def exactitud_campo(refs: list, hyps: list) -> float:
    """% de campos numéricos reconocidos exactamente."""
    if not refs:
        return 0.0
    ok = sum(1 for r, h in zip(refs, hyps) if str(r) == str(h))
    return ok / len(refs)


if __name__ == "__main__":
    assert cer("208", "208") == 0.0
    assert cer("208", "200") > 0.0
    print("CER('208','200') =", round(cer("208", "200"), 3))
    print("WER('a b c','a x c') =", round(wer("a b c", "a x c"), 3))
    print("Exactitud =", exactitud_campo([208, 22, 11], [208, 22, 10]))
