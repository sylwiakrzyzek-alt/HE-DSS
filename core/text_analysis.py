from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOPWORDS = {
    'the','and','or','of','to','in','for','a','an','on','with','by','from','that','this','will','be','are','is','as','at','into','their','our','its','it','we','they','these','those','such','through','among','using','use','including','also','more','most','not','than','have','has','had','can','could','should','would','may','might',
    'i','oraz','w','z','na','do','dla','że','to','jest','są','będzie','będą','przez','przy','jako','który','która','które','ich','jego','jej','tego','tej','tym','ten','ta','te','się','nie','lub','a','o','od','po','pod','nad','między','także','może','mogą','ma','mają','być','projekt','projekcie'
}

# Osiem funkcji treści z procedury CATA opisanej w rozprawie.
# Reguły są jawne i deterministyczne; lista fraz jest częścią implementacji prototypowej.
NARRATIVE_FUNCTIONS: dict[str, list[str]] = {
    'Problem / potrzeba': [
        'problem','challenge','need','unmet need','burden','issue','barrier','shortage','lack of','demand',
        'problem','wyzwanie','potrzeba','obciążenie','bariera','niedobór','brak'
    ],
    'Luka / ograniczenie': [
        'gap','limitation','limited','insufficient','poorly understood','unknown','missing','bottleneck','fragmented',
        'luka','ograniczenie','niewystarcz','nieznan','brakuje','fragmentac'
    ],
    'Cel': [
        'objective','aim','goal','purpose','seeks to','will address','will investigate','will develop',
        'cel','celem','zamierza','dąży do','będzie badać','będzie rozwijać'
    ],
    'Metoda / rozwiązanie': [
        'method','methodology','approach','solution','framework','model','tool','platform','pilot','trial','experiment','analysis','co-create','validate',
        'metoda','metodologia','podejście','rozwiązanie','model','narzędzie','platforma','pilotaż','badanie','analiza','walidac'
    ],
    'Innowacyjność': [
        'novel','innovative','innovation','new approach','breakthrough','state-of-the-art','beyond the state of the art','unprecedented',
        'nowators','innowacyj','nowe podejście','przełom','stan wiedzy'
    ],
    'Wpływ / korzyści': [
        'impact','benefit','improve','increase','reduce','strengthen','enhance','contribute to','outcome','expected outcome','societal','economic',
        'wpływ','korzyść','popraw','zwiększ','ogranicz','wzmocn','rezultat','oddziaływanie'
    ],
    'Implementacja / wykorzystanie': [
        'implement','implementation','uptake','use of results','exploitation','deployment','adoption','scale-up','dissemination','communication','policy recommendation','market',
        'wdroż','wykorzyst','upowszechn','komunikac','eksploatac','adopc','skalow','rekomendac'
    ],
    'Pacjent / użytkownik': [
        'patient','patients','user','users','end-user','end user','citizen','citizens','beneficiary','beneficiaries','caregiver','caregivers','stakeholder','stakeholders',
        'pacjent','użytkownik','obywatel','beneficjent','opiekun','interesariusz'
    ],
}


def _normalise(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()


def tokens(text: str) -> list[str]:
    out = re.findall(r"[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9\-']{1,}", _normalise(text))
    return [t for t in out if t not in STOPWORDS and not t.isdigit()]


def key_terms(text: str, n: int = 30) -> list[str]:
    return [w for w, _ in Counter(tokens(text)).most_common(n)]


def _tfidf_pair(call_text: str, objective_text: str):
    vectorizer = TfidfVectorizer(lowercase=True, stop_words=list(STOPWORDS), ngram_range=(1, 3), token_pattern=r"(?u)\b[A-Za-zÀ-ž][A-Za-zÀ-ž\-']+\b")
    matrix = vectorizer.fit_transform([call_text, objective_text])
    return vectorizer, matrix


def lexical_similarity(call_text: str, objective_text: str) -> float:
    try:
        _, matrix = _tfidf_pair(call_text, objective_text)
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])
    except ValueError:
        return 0.0


def top50_call_terms(call_text: str, objective_text: str) -> list[str]:
    try:
        vectorizer, matrix = _tfidf_pair(call_text, objective_text)
        terms = vectorizer.get_feature_names_out()
        row = matrix[0].toarray().ravel()
        ranked = sorted(zip(terms, row), key=lambda x: x[1], reverse=True)
        return [term for term, value in ranked if value > 0][:50]
    except ValueError:
        return []


def top50_coverage(call_text: str, objective_text: str) -> tuple[float, list[str], list[str]]:
    top = top50_call_terms(call_text, objective_text)
    target = _normalise(objective_text)
    covered = [t for t in top if re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', target)]
    missing = [t for t in top if t not in covered]
    return (len(covered) / len(top) if top else 0.0), covered, missing


def _phrase_position(text: str, phrases: list[str]) -> tuple[int | None, str | None]:
    low = _normalise(text)
    best: tuple[int, str] | None = None
    for phrase in phrases:
        # Prefix-like Polish rules (e.g. "innowacyj") are intentionally allowed.
        idx = low.find(phrase.lower())
        if idx >= 0 and (best is None or idx < best[0]):
            best = (idx, phrase)
    return best if best is not None else (None, None)


def narrative_profile(text: str) -> list[dict[str, Any]]:
    denom = max(1, len(_normalise(text)))
    out = []
    for name, phrases in NARRATIVE_FUNCTIONS.items():
        pos, phrase = _phrase_position(text, phrases)
        out.append({
            'function': name,
            'present': pos is not None,
            'position': None if pos is None else pos / denom,
            'matched_phrase': phrase,
        })
    return out


def _present_names(profile: list[dict[str, Any]]) -> list[str]:
    return [x['function'] for x in profile if x['present']]


def narrative_coverage(call_profile, obj_profile) -> float:
    c = set(_present_names(call_profile)); o = set(_present_names(obj_profile))
    return len(c & o) / len(c) if c else 0.0


def narrative_completeness(obj_profile) -> float:
    return len(_present_names(obj_profile)) / len(NARRATIVE_FUNCTIONS)


def order_agreement(call_profile, obj_profile) -> float:
    cp = {x['function']: x['position'] for x in call_profile if x['present']}
    op = {x['function']: x['position'] for x in obj_profile if x['present']}
    common = list(set(cp) & set(op))
    if len(common) < 2:
        return 0.0
    agree = total = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            a, b = common[i], common[j]
            total += 1
            if (cp[a] < cp[b]) == (op[a] < op[b]):
                agree += 1
    return agree / total if total else 0.0


def analyze_alignment(call_text: str, objective_text: str) -> dict[str, Any]:
    if not call_text.strip() or not objective_text.strip():
        return {}
    cosine = lexical_similarity(call_text, objective_text)
    coverage50, covered, missing = top50_coverage(call_text, objective_text)
    call_prof = narrative_profile(call_text)
    obj_prof = narrative_profile(objective_text)
    nc = narrative_coverage(call_prof, obj_prof)
    oa = order_agreement(call_prof, obj_prof)
    ncomp = narrative_completeness(obj_prof)
    sas = 0.6 * nc + 0.2 * oa + 0.2 * ncomp
    return {
        'cosine_similarity': round(cosine, 4),
        'top50_coverage': round(coverage50, 4),
        'structural_alignment_score': round(sas, 4),
        'narrative_coverage': round(nc, 4),
        'order_agreement': round(oa, 4),
        'narrative_completeness': round(ncomp, 4),
        'top50_terms': top50_call_terms(call_text, objective_text),
        'covered_top50': covered,
        'missing_top50': missing,
        'call_profile': call_prof,
        'objective_profile': obj_prof,
        'method_note': 'SAS = 0.6×NC + 0.2×OA + 0.2×NComp. Wskaźnik opisowy; nie jest miarą prawdopodobieństwa finansowania.'
    }


def executive_summary(alignment: dict[str, Any], result: dict[str, Any]) -> str:
    return (
        f"CALL–OBJECTIVE: cosine similarity {alignment.get('cosine_similarity',0)*100:.1f}%, "
        f"pokrycie TOP50 {alignment.get('top50_coverage',0)*100:.1f}%, Structural Alignment Score {alignment.get('structural_alignment_score',0)*100:.1f}%. "
        f"MDSM: {result.get('overall',0):.1f}/100 ({result.get('band','')}). "
        "Oba mechanizmy są niezależne i mają charakter diagnostyczny; nie prognozują wyniku konkursu."
    )
