# HE-DSS 4.6 — wersja do rozprawy doktorskiej

Prototyp implementuje dwa **niezależne** mechanizmy diagnostyczne opisane w rozprawie:

1. **CALL–OBJECTIVE (CATA)**: TF–IDF, cosine similarity, pokrycie TOP50, osiem funkcji narracyjnych, Narrative Coverage, Order Agreement, Narrative Completeness oraz Structural Alignment Score: `SAS = 0.6*NC + 0.2*OA + 0.2*NComp`.
2. **MDSM**: 12 determinant warstwy operacyjnej, 57 wskaźników, wagi znormalizowane na podstawie 168 odniesień po wyłączeniu wsparcia instytucjonalnego i czynnika ludzkiego oraz addytywna agregacja do wyniku 0–100. MDSM nie jest modelem predykcyjnym.

## Uruchomienie lokalne

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Publikacja dla recenzenta

Repozytorium można umieścić na GitHubie i wdrożyć w Streamlit Community Cloud, wskazując `app.py` jako plik startowy. Po wdrożeniu otrzymany stały adres aplikacji należy wpisać w rozdziale 6 rozprawy.

## Ważne ograniczenia

- CALL–OBJECTIVE i MDSM nie są łączone w jeden wskaźnik.
- SAS jest wskaźnikiem opisowym i nie mierzy prawdopodobieństwa finansowania.
- MDSM ocenia stopień przygotowania projektu; nie prognozuje decyzji Komisji Europejskiej.
- Prototyp ma charakter demonstracyjny i nie zastępuje oceny eksperckiej.


## Zasada operacjonalizacji w wersji 4.0
Warstwa koncepcyjna MDSM zachowuje 14 determinant wynikających z badań. Warstwa operacyjna HE-DSS obejmuje 12 determinant i 57 wskaźników możliwych do oceny przez niezależnego eksperta na podstawie kompletnego wniosku i dokumentacji konkursowej. Z mechanizmu obliczeniowego wyłączono czynnik ludzki w procesie oceny oraz wsparcie instytucjonalne. W pozostałych determinantach usunięto wskaźniki, których nie można wiarygodnie ocenić z dokumentacji aplikacyjnej. Nie dodawano nowych wskaźników. Udziały pozostałych wskaźników są normalizowane przy zachowaniu ich pierwotnych proporcji; analogicznie normalizowane są wagi 12 determinant operacyjnych.


## Kontrola duplikatów semantycznych (4.2)
Z warstwy operacyjnej wyłączono dodatkowo trzy wskaźniki dublujące ten sam obserwowalny aspekt wniosku: Zwięzłość z D02 (pozostaje w D04), Logiczna narracja z D04 (logika argumentacji pozostaje w D02) oraz Logiczna organizacja z D09 (struktura wniosku pozostaje w D02; D09 zachowuje aspekty wizualnej przejrzystości). Nie dodano nowych wskaźników. Udziały pozostałych wskaźników w tych determinantach znormalizowano przy zachowaniu pierwotnych proporcji.


## Korekta numeracji i wag w wersji 4.6
Determinanty warstwy operacyjnej mają ciągłą numerację D01–D12: D05 = Innowacyjność, D06 = Jakość konsorcjum, D07 = Renoma instytucji, D08 = Wpływ projektu (Impact), D09 = Interdyscyplinarność, D10 = Przejrzystość prezentacji projektu, D11 = Kompetencje lidera projektu, D12 = Realizm budżetu. Identyfikatory wszystkich 57 wskaźników zostały przepisane zgodnie z tą numeracją. Wagi determinant są liczone z 168 odniesień pozostających po wyłączeniu 10 odniesień do wsparcia instytucjonalnego i 2 odniesień do czynnika ludzkiego.
