from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import APP_NAME, APP_SUBTITLE, VERSION, DATA_DIR, ASSETS_DIR
from core.model import load_determinants, compute_results
from core.text_analysis import analyze_alignment, executive_summary
from database.db import Database
from reports.pdf_report import build_pdf_report

st.set_page_config(page_title=APP_NAME, page_icon='📘', layout='wide')
css = ASSETS_DIR / 'style.css'
if css.exists():
    st.markdown(f'<style>{css.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

db = Database()
determinants = load_determinants(DATA_DIR / 'determinants.json')

for k, v in {'page': 'Start', 'assessment_id': None, 'version_id': None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def navigate(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def active_assessment():
    return db.get_assessment(st.session_state.assessment_id) if st.session_state.assessment_id else None


def active_version():
    aid = st.session_state.assessment_id
    if not aid:
        return None
    versions = db.list_versions(aid)
    if not versions:
        return None
    if not st.session_state.version_id:
        st.session_state.version_id = versions[0]['id']
    return next((v for v in versions if v['id'] == st.session_state.version_id), versions[0])


def score_label(score: float) -> str:
    if score >= 85: return 'Excellent'
    if score >= 70: return 'Strong'
    if score >= 55: return 'Moderate'
    if score >= 40: return 'Weak'
    return 'Critical'


def sidebar() -> None:
    with st.sidebar:
        st.markdown(f'## {APP_NAME}')
        st.caption(f'Wersja {VERSION}')
        pages = ['Start', 'Projekty', 'Nowy projekt', 'Analiza CALL–OBJECTIVE', 'Ocena MDSM', 'Wyniki', 'Raport']
        chosen = st.radio('Nawigacja', pages, index=pages.index(st.session_state.page))
        if chosen != st.session_state.page:
            st.session_state.page = chosen
            st.rerun()
        st.divider()
        a = active_assessment()
        if a:
            st.caption('Aktywny projekt')
            st.write(f"**{a['acronym'] or a['project_name']}**")
            versions = db.list_versions(a['id'])
            labels = {v['id']: f"v{v['version_no']} — {v['label']}" for v in versions}
            ids = list(labels)
            idx = ids.index(st.session_state.version_id) if st.session_state.version_id in ids else 0
            selected = st.selectbox('Wersja oceny', ids, format_func=lambda x: labels[x], index=idx)
            st.session_state.version_id = selected
            if st.button('Utwórz nową wersję', use_container_width=True):
                st.session_state.version_id = db.create_version(a['id'])
                st.rerun()
        else:
            st.caption('Brak aktywnego projektu')


def page_start() -> None:
    st.markdown(f'<div class="hero"><h1>{APP_NAME}</h1><p>{APP_SUBTITLE}</p></div>', unsafe_allow_html=True)
    st.write(f"Prototyp realizuje dwa niezależne mechanizmy diagnostyczne: analizę CALL–OBJECTIVE zgodną z procedurą CATA opisaną w rozprawie oraz ocenę {len(determinants)} determinant operacyjnych modelu MDSM za pomocą {sum(len(d['indicators']) for d in determinants)} wskaźników.")
    c1, c2, c3 = st.columns(3)
    c1.metric('Determinanty MDSM', len(determinants))
    c2.metric('Wskaźniki operacyjne', sum(len(d['indicators']) for d in determinants))
    c3.metric('Analiza tekstu', 'CALL ↔ OBJECTIVE')
    st.info('System ma charakter diagnostyczny. Nie prognozuje wyniku konkursu i nie zastępuje oceny eksperckiej.')
    if st.button('Rozpocznij nową analizę', type='primary'):
        navigate('Nowy projekt')


def page_projects() -> None:
    st.title('Projekty')
    rows = db.list_assessments()
    if not rows:
        st.info('Brak projektów.')
        return
    for r in rows:
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.subheader(r['acronym'] or r['project_name'])
            c1.caption(r['project_name'])
            c2.write(r['action_type'] or '—')
            c2.write(r['call_id'] or '—')
            if c3.button('Otwórz', key=f"open{r['id']}", use_container_width=True):
                st.session_state.assessment_id = r['id']
                st.session_state.version_id = db.list_versions(r['id'])[0]['id']
                navigate('Analiza CALL–OBJECTIVE')
            if c3.button('Usuń', key=f"del{r['id']}", use_container_width=True):
                db.delete_assessment(r['id'])
                st.rerun()


def page_new() -> None:
    st.title('Nowy projekt')
    with st.form('new'):
        c1, c2 = st.columns(2)
        name = c1.text_input('Nazwa projektu *')
        acr = c2.text_input('Akronim')
        programme = c1.text_input('Program', value='Horyzont Europa')
        action = c2.selectbox('Typ działania', ['RIA', 'IA', 'CSA', 'MSCA', 'ERC', 'Inny'])
        call = c1.text_input('Call ID')
        topic = c2.text_input('Topic')
        org = c1.text_input('Organizacja')
        evaluator = c2.text_input('Osoba oceniająca')
        ok = st.form_submit_button('Utwórz projekt', type='primary')
    if ok:
        if not name.strip():
            st.error('Podaj nazwę projektu.')
            return
        aid = db.create_assessment({'project_name': name, 'acronym': acr, 'programme': programme, 'call_id': call, 'topic': topic, 'action_type': action, 'organisation': org, 'evaluator': evaluator})
        st.session_state.assessment_id = aid
        st.session_state.version_id = db.list_versions(aid)[0]['id']
        navigate('Analiza CALL–OBJECTIVE')


def page_analysis() -> None:
    a, v = active_assessment(), active_version()
    if not a or not v:
        st.warning('Najpierw utwórz lub otwórz projekt.')
        return
    saved = db.get_analysis(v['id'])
    st.title('Analiza CALL–OBJECTIVE')
    st.caption(f"{a['acronym'] or a['project_name']} · wersja {v['version_no']}")
    st.write('Wklej tekst calla oraz dostępny opis projektu, objective, abstract albo concept note. Tekst projektu może być jednym ciągłym polem i nie musi zawierać nagłówków.')

    with st.form('analysis_form'):
        call_text = st.text_area('CALL TEXT', value=saved.get('call_text', ''), height=290, placeholder='Wklej Expected Outcomes, Scope lub cały tekst topicu...')
        objective_text = st.text_area('PROJECT OBJECTIVE / CONCEPT NOTE', value=saved.get('objective_text', ''), height=290, placeholder='Wklej opis projektu w jednym polu — z nagłówkami albo bez nagłówków...')
        submitted = st.form_submit_button('ANALYZE', type='primary', use_container_width=True)

    if submitted:
        if not call_text.strip() or not objective_text.strip():
            st.error('Wklej oba teksty: CALL oraz PROJECT OBJECTIVE.')
            return
        alignment = analyze_alignment(call_text, objective_text)
        result = compute_results(determinants, {})
        summary = executive_summary(alignment, result)
        db.save_analysis(v['id'], call_text, objective_text, alignment, summary)
        st.success(f"Analiza CALL–OBJECTIVE zakończona. Ocena MDSM pozostaje odrębnym etapem i wymaga oceny {sum(len(d['indicators']) for d in determinants)} wskaźników.")
        st.rerun()

    current = db.get_analysis(v['id'])
    alignment = current.get('alignment') or {}
    if alignment:
        st.subheader('CALL–OBJECTIVE: wyniki analizy leksykalnej i narracyjnej')
        c1, c2, c3 = st.columns(3)
        c1.metric('Cosine similarity', f"{alignment.get('cosine_similarity', 0)*100:.1f}%")
        c2.metric('Pokrycie TOP50', f"{alignment.get('top50_coverage', 0)*100:.1f}%")
        c3.metric('Structural Alignment Score', f"{alignment.get('structural_alignment_score', 0)*100:.1f}%")
        st.caption('SAS = 0,6 × Narrative Coverage + 0,2 × Order Agreement + 0,2 × Narrative Completeness.')
        narr = pd.DataFrame([
            {'Wskaźnik':'Narrative Coverage', 'Wartość':alignment.get('narrative_coverage',0)*100},
            {'Wskaźnik':'Order Agreement', 'Wartość':alignment.get('order_agreement',0)*100},
            {'Wskaźnik':'Narrative Completeness', 'Wartość':alignment.get('narrative_completeness',0)*100},
            {'Wskaźnik':'Structural Alignment Score', 'Wartość':alignment.get('structural_alignment_score',0)*100},
        ])
        fig = px.bar(narr, x='Wartość', y='Wskaźnik', orientation='h', range_x=[0,100], labels={'Wartość':'Wartość [%]'})
        st.plotly_chart(fig, use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**Terminy TOP50 CALL obecne w Objective**')
            st.write(', '.join(alignment.get('covered_top50', [])) or '—')
        with c2:
            st.markdown('**Terminy TOP50 CALL niewykryte w Objective**')
            st.write(', '.join(alignment.get('missing_top50', [])) or '—')
        with st.expander('Osiem funkcji narracyjnych'):
            rows=[]
            cp={x['function']:x for x in alignment.get('call_profile',[])}
            op={x['function']:x for x in alignment.get('objective_profile',[])}
            for fn in cp:
                rows.append({'Funkcja':fn,'CALL':'tak' if cp[fn]['present'] else 'nie','Objective':'tak' if op.get(fn,{}).get('present') else 'nie','Fraza CALL':cp[fn].get('matched_phrase') or '—','Fraza Objective':op.get(fn,{}).get('matched_phrase') or '—'})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.info('Analiza CALL–OBJECTIVE jest niezależna od MDSM. Wyników nie należy sumować ani interpretować jako prawdopodobieństwa finansowania.')
        if st.button(f"Przejdź do weryfikacji {len(determinants)} determinant", type='primary'):
            navigate('Ocena MDSM')


def page_assessment() -> None:
    a, v = active_assessment(), active_version()
    if not a or not v:
        st.warning('Otwórz projekt.')
        return
    analysis = db.get_analysis(v['id'])
    if not analysis.get('objective_text'):
        st.warning('Najpierw wykonaj analizę CALL–OBJECTIVE.')
        return
    st.title(f"Ocena {len(determinants)} determinant MDSM")
    st.caption(f"Warstwę operacyjną MDSM tworzy {len(determinants)} determinant ocenianych za pomocą {sum(len(d['indicators']) for d in determinants)} wskaźników. Struktura wskaźników wynika z operacjonalizacji determinant wyodrębnionych w badaniu jakościowym opisanym w rozdziale 4. Oceny wprowadza użytkownik na podstawie dostępnej dokumentacji projektu.")
    saved = db.get_scores(v['id'])
    with st.form('assessment'):
        tabs = st.tabs([f"{d['id']} {d['name']}" for d in determinants])
        form_values = []
        for tab, det in zip(tabs, determinants):
            with tab:
                st.markdown(f"<span class='badge'>Waga: {float(det['weight']):.1f}%</span>", unsafe_allow_html=True)
                st.write(det['definition'])
                # One evidence/comment block per determinant; indicator scores remain separate.
                first_saved = saved.get(det['indicators'][0]['id'], {}) if det['indicators'] else {}
                evidence = st.text_area(
                    'Evidence / uzasadnienie dla determinanty',
                    value=first_saved.get('evidence', '') or '',
                    key=f"e_det_{det['id']}",
                    height=100,
                    help='Jedno wspólne pole dowodowe dla całej determinanty. Oceny poszczególnych wskaźników pozostają niezależne.'
                )
                notes = st.text_area(
                    'Komentarz ekspercki dla determinanty',
                    value=first_saved.get('notes', '') or '',
                    key=f"n_det_{det['id']}",
                    height=80
                )
                st.markdown('#### Kryteria / wskaźniki')
                for ind in det['indicators']:
                    old = saved.get(ind['id'], {})
                    st.markdown(f"**{ind['name']} · udział wewnętrzny {float(ind['display_share']):.1f}%**")
                    st.caption(ind['question'])
                    score = st.slider('Ocena 0–5', 0.0, 5.0, float(old.get('score', 0.0)), 0.5, key=f"s_{ind['id']}")
                    # Store the determinant-level evidence/comment with each indicator for backward compatibility.
                    form_values.append((ind['id'], score, evidence, notes))
                    st.divider()
        submitted = st.form_submit_button('Zapisz zweryfikowaną ocenę', type='primary')
    if submitted:
        for iid, score, evidence, notes in form_values:
            db.save_score(v['id'], iid, score, evidence, notes)
        result = compute_results(determinants, {iid: score for iid, score, _, _ in form_values})
        db.save_overall(v['id'], result['overall'])
        alignment = db.get_analysis(v['id']).get('alignment', {})
        summary = executive_summary(alignment, result)
        x = db.get_analysis(v['id'])
        db.save_analysis(v['id'], x.get('call_text',''), x.get('objective_text',''), alignment, summary)
        st.success('Ocena zapisana.')
        navigate('Wyniki')


def current_result():
    v = active_version()
    if not v:
        return None, None
    saved = db.get_scores(v['id'])
    scores = {k: float(x['score']) for k, x in saved.items()}
    return compute_results(determinants, scores), saved


def page_results() -> None:
    a, v = active_assessment(), active_version()
    if not a or not v:
        st.warning('Otwórz projekt.')
        return
    result, saved = current_result()
    analysis = db.get_analysis(v['id'])
    if not saved:
        st.info('Najpierw wykonaj analizę.')
        return
    alignment = analysis.get('alignment') or {}
    st.title('Wyniki HE-DSS')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('CALL–OBJECTIVE (SAS)', f"{alignment.get('structural_alignment_score', 0)*100:.1f}%")
    c2.metric('Wynik MDSM', f"{result['overall']:.1f}/100")
    c3.metric('Poziom przygotowania', result['band'])
    c4.metric('Alerty', len(result['alerts']))
    st.info(analysis.get('executive_summary') or result['interpretation'])

    if result['alerts']:
        for x in result['alerts']:
            st.warning(x)

    df = pd.DataFrame(result['rows'])
    left, right = st.columns(2)
    with left:
        fig = px.bar(df.sort_values('score_100'), x='score_100', y='name', orientation='h', labels={'score_100':'Ocena /100','name':''}, range_x=[0,100])
        st.plotly_chart(fig, use_container_width=True)
    with right:
        radar = df.sort_values('id')
        fig = go.Figure(go.Scatterpolar(r=radar['score_100'], theta=radar['id'], fill='toself'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"{len(determinants)} determinant MDSM")
    for _, r in df.sort_values('id').iterrows():
        with st.expander(f"{r['id']} · {r['name']} — {r['score_100']:.1f}/100 ({score_label(r['score_100'])})"):
            det = next(d for d in determinants if d['id'] == r['id'])
            st.write(det['definition'])
            first_item = saved.get(det['indicators'][0]['id'], {}) if det['indicators'] else {}
            if first_item.get('evidence'):
                st.markdown('**Evidence / uzasadnienie dla determinanty:**')
                st.write(first_item.get('evidence',''))
            if first_item.get('notes'):
                st.markdown('**Komentarz ekspercki dla determinanty:**')
                st.write(first_item.get('notes',''))
            indicator_rows = []
            for ind in det['indicators']:
                item = saved.get(ind['id'], {})
                indicator_rows.append({'Wskaźnik': ind['name'], 'Ocena': item.get('score', 0)})
            st.dataframe(pd.DataFrame(indicator_rows), hide_index=True, use_container_width=True)

    st.subheader('Top 5 recommendations')
    for i, rec in enumerate(result['recommendations'][:5], 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {rec['determinant']} → {rec['indicator']} ({rec['score']:.1f}/5)**")
            st.write(rec['text'])


def report_html(a, v, analysis, result, saved) -> str:
    alignment = analysis.get('alignment') or {}
    area_rows = ''.join([
        f"<tr><td>Cosine similarity</td><td>{alignment.get('cosine_similarity',0)*100:.1f}%</td></tr>",
        f"<tr><td>Pokrycie TOP50</td><td>{alignment.get('top50_coverage',0)*100:.1f}%</td></tr>",
        f"<tr><td>Narrative Coverage</td><td>{alignment.get('narrative_coverage',0)*100:.1f}%</td></tr>",
        f"<tr><td>Order Agreement</td><td>{alignment.get('order_agreement',0)*100:.1f}%</td></tr>",
        f"<tr><td>Narrative Completeness</td><td>{alignment.get('narrative_completeness',0)*100:.1f}%</td></tr>",
        f"<tr><td>Structural Alignment Score</td><td>{alignment.get('structural_alignment_score',0)*100:.1f}%</td></tr>",
    ])
    det_rows = ''.join(
        f"<tr><td>{html.escape(r['id'])}</td><td>{html.escape(r['name'])}</td><td>{r['weight_pct']:.1f}%</td><td>{r['score_100']:.1f}</td><td>{html.escape(score_label(r['score_100']))}</td></tr>"
        for r in sorted(result['rows'], key=lambda x: x['id'])
    )
    recs = ''.join(
        f"<li><b>{html.escape(r['determinant'])} — {html.escape(r['indicator'])}</b>: {html.escape(r['text'])}</li>"
        for r in result['recommendations'][:10]
    )
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
    body{{font-family:Arial,sans-serif;max-width:1050px;margin:40px auto;line-height:1.5;color:#1d2a3a}}
    table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}th,td{{border:1px solid #ccd5e0;padding:8px;text-align:left;vertical-align:top}}
    h1,h2{{color:#16345f}}.box{{padding:14px 18px;background:#eef4fb;border-left:5px solid #2559a7;margin:14px 0}}
    </style></head><body>
    <h1>HE-DSS — raport diagnostyczny</h1>
    <p><b>Projekt:</b> {html.escape(a['project_name'])} ({html.escape(a['acronym'] or '')})<br>
    <b>Call:</b> {html.escape(a['call_id'] or '—')}<br><b>Wersja:</b> {v['version_no']}</p>
    <div class="box"><b>Executive Summary</b><br>{html.escape(analysis.get('executive_summary',''))}</div>
    <h2>CALL–OBJECTIVE</h2><p>Analiza leksykalna i narracyjna zgodna z procedurą CATA opisaną w rozprawie.</p><table><tr><th>Wskaźnik</th><th>Wartość</th></tr>{area_rows}</table><p><b>SAS:</b> 0,6 × NC + 0,2 × OA + 0,2 × NComp.</p>
    <h2>{len(determinants)} determinant MDSM</h2><p><b>Wynik syntetyczny:</b> {result['overall']:.1f}/100 · <b>Poziom:</b> {html.escape(result['band'])}</p>
    <table><tr><th>ID</th><th>Determinanta</th><th>Waga</th><th>Ocena</th><th>Interpretacja</th></tr>{det_rows}</table>
    <h2>Top recommendations</h2><ol>{recs}</ol>
    <h2>Ograniczenie</h2><p>Raport jest oparty na wprowadzonym tekście calla, krótkim opisie projektu oraz ocenach MDSM. Nie stanowi oficjalnej oceny Komisji Europejskiej ani prognozy finansowania.</p>
    </body></html>'''


def page_report() -> None:
    a, v = active_assessment(), active_version()
    if not a or not v:
        st.warning('Otwórz projekt.')
        return
    result, saved = current_result()
    analysis = db.get_analysis(v['id'])
    if not saved:
        st.info('Najpierw wykonaj analizę.')
        return
    st.title('Raport')
    html_report = report_html(a, v, analysis, result, saved)
    c1, c2 = st.columns(2)
    c1.download_button('Pobierz raport HTML', html_report.encode('utf-8'), file_name=f"HE_DSS_{a['acronym'] or a['id']}_v{v['version_no']}.html", mime='text/html', use_container_width=True)
    try:
        pdf_bytes = build_pdf_report(a, v, analysis, result, saved, determinants, score_label)
        c2.download_button('Pobierz raport PDF', pdf_bytes, file_name=f"HE_DSS_{a['acronym'] or a['id']}_v{v['version_no']}.pdf", mime='application/pdf', type='primary', use_container_width=True)
    except Exception as exc:
        c2.error(f'Nie udało się utworzyć PDF: {exc}')
    st.components.v1.html(html_report, height=900, scrolling=True)


sidebar()
page = st.session_state.page
if page == 'Start': page_start()
elif page == 'Projekty': page_projects()
elif page == 'Nowy projekt': page_new()
elif page == 'Analiza CALL–OBJECTIVE': page_analysis()
elif page == 'Ocena MDSM': page_assessment()
elif page == 'Wyniki': page_results()
elif page == 'Raport': page_report()
