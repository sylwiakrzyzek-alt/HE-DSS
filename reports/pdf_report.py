from __future__ import annotations
from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether


def _font_names():
    regular_candidates = [
        Path('C:/Windows/Fonts/arial.ttf'), Path('C:/Windows/Fonts/calibri.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    bold_candidates = [
        Path('C:/Windows/Fonts/arialbd.ttf'), Path('C:/Windows/Fonts/calibrib.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]
    regular = next((p for p in regular_candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), None)
    if regular and bold:
        pdfmetrics.registerFont(TTFont('HEDSS', str(regular)))
        pdfmetrics.registerFont(TTFont('HEDSS-Bold', str(bold)))
        return 'HEDSS','HEDSS-Bold'
    return 'Helvetica','Helvetica-Bold'


def build_pdf_report(a, v, analysis, result, saved, determinants, score_label):
    buf=BytesIO(); font,bold=_font_names()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=15*mm,
                          title='HE-DSS 4.5 - raport diagnostyczny')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2',parent=styles['Title'],fontName=bold,fontSize=20,leading=24,textColor=colors.HexColor('#16345f'),spaceAfter=10))
    styles.add(ParagraphStyle(name='H2x',parent=styles['Heading2'],fontName=bold,fontSize=14,leading=18,textColor=colors.HexColor('#16345f'),spaceBefore=10,spaceAfter=7))
    styles.add(ParagraphStyle(name='Bodyx',parent=styles['BodyText'],fontName=font,fontSize=8.5,leading=11))
    styles.add(ParagraphStyle(name='Smallx',parent=styles['BodyText'],fontName=font,fontSize=7.3,leading=9))
    styles.add(ParagraphStyle(name='Centerx',parent=styles['BodyText'],fontName=bold,fontSize=9,alignment=TA_CENTER))
    story=[]
    story.append(Paragraph('HE-DSS 4.5 - raport diagnostyczny',styles['Title2']))
    story.append(Paragraph(f"<b>Projekt:</b> {a['project_name']} ({a['acronym'] or '-'})<br/><b>Call:</b> {a['call_id'] or '-'}<br/><b>Wersja:</b> {v['version_no']}",styles['Bodyx']))
    story.append(Spacer(1,5*mm))
    summary=analysis.get('executive_summary','')
    t=Table([[Paragraph('<b>Executive Summary</b><br/>'+summary,styles['Bodyx'])]],colWidths=[176*mm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eef4fb')),('BOX',(0,0),(-1,-1),0.7,colors.HexColor('#2559a7')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)])); story.append(t)
    alignment=analysis.get('alignment') or {}
    story.append(Paragraph('CALL-OBJECTIVE Alignment',styles['H2x']))
    story.append(Paragraph(f"<b>Overall alignment:</b> {alignment.get('overall',0):.1f}% &nbsp;&nbsp; <b>Confidence:</b> {alignment.get('confidence','-')}",styles['Bodyx']))
    area_data=[[Paragraph('<b>Obszar</b>',styles['Smallx']),Paragraph('<b>Wynik</b>',styles['Smallx']),Paragraph('<b>Potencjalnie brakujące terminy</b>',styles['Smallx'])]]
    for x in alignment.get('areas',[]): area_data.append([Paragraph(str(x['area']),styles['Smallx']),Paragraph(f"{x['score']:.1f}%",styles['Smallx']),Paragraph(', '.join(x.get('missing',[])) or '-',styles['Smallx'])])
    tab=Table(area_data,colWidths=[48*mm,24*mm,104*mm],repeatRows=1)
    tab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#b9c4d0')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)])); story.append(tab)
    story.append(Paragraph(f'{len(determinants)} determinant MDSM',styles['H2x']))
    story.append(Paragraph(f"<b>Wynik syntetyczny:</b> {result['overall']:.1f}/100 &nbsp;&nbsp; <b>Poziom:</b> {result['band']}",styles['Bodyx']))
    det_data=[[Paragraph('<b>ID</b>',styles['Smallx']),Paragraph('<b>Determinanta</b>',styles['Smallx']),Paragraph('<b>Waga</b>',styles['Smallx']),Paragraph('<b>Ocena</b>',styles['Smallx']),Paragraph('<b>Interpretacja</b>',styles['Smallx'])]]
    for r in sorted(result['rows'],key=lambda x:x['id']): det_data.append([r['id'],Paragraph(r['name'],styles['Smallx']),f"{r['weight_pct']:.2f}%",f"{r['score_100']:.1f}",score_label(r['score_100'])])
    tab=Table(det_data,colWidths=[14*mm,84*mm,20*mm,20*mm,38*mm],repeatRows=1)
    tab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#b9c4d0')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef6')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTNAME',(0,1),(0,-1),font),('FONTNAME',(2,1),(-1,-1),font),('FONTSIZE',(0,1),(-1,-1),7.2),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)])); story.append(tab)
    story.append(PageBreak())
    story.append(Paragraph(f"Szczegółowa ocena {sum(len(d['indicators']) for d in determinants)} wskaźników",styles['H2x']))
    story.append(Paragraph('Wskaźniki odpowiadają podtematom wyodrębnionym w analizie tematycznej opisanej w rozdziale 4 rozprawy.',styles['Bodyx']))
    for det in determinants:
        rows=[[Paragraph('<b>Wskaźnik</b>',styles['Smallx']),Paragraph('<b>Udział</b>',styles['Smallx']),Paragraph('<b>Ocena</b>',styles['Smallx']),Paragraph('<b>Evidence / komentarz</b>',styles['Smallx'])]]
        for ind in det['indicators']:
            item=saved.get(ind['id'],{})
            ev=(item.get('evidence','') or '')
            note=(item.get('notes','') or '')
            text=(ev+'\n'+note).strip() or 'Brak danych / wymaga oceny eksperckiej.'
            rows.append([Paragraph(ind['name'],styles['Smallx']),f"{ind['share']:.0f}%",f"{float(item.get('score',0)):.1f}/5",Paragraph(text.replace('\n','<br/>'),styles['Smallx'])])
        title=Paragraph(f"{det['id']} {det['name']}",styles['H2x'])
        tab=Table(rows,colWidths=[45*mm,16*mm,18*mm,97*mm],repeatRows=1)
        tab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#c7d0da')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef2f7')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTNAME',(1,1),(2,-1),font),('FONTSIZE',(1,1),(2,-1),7),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        story.extend([title,tab,Spacer(1,3*mm)])
    story.append(Paragraph('Najważniejsze rekomendacje',styles['H2x']))
    recs=result.get('recommendations',[])[:10]
    if recs:
        for i,r in enumerate(recs,1): story.append(Paragraph(f"<b>{i}. {r['determinant']} - {r['indicator']}</b><br/>{r['text']}",styles['Bodyx']))
    else: story.append(Paragraph('Brak automatycznych rekomendacji. Sprawdź, czy oceny zostały uzupełnione i zweryfikowane.',styles['Bodyx']))
    story.append(Paragraph('Ograniczenie',styles['H2x']))
    story.append(Paragraph('Raport jest oparty na wprowadzonym tekście calla, krótkim opisie projektu oraz ocenach MDSM. Automatyczna sugestia nie stanowi oficjalnej oceny Komisji Europejskiej ani prognozy finansowania. Determinanty wymagające danych o konsorcjum, instytucjach, liderze, zarządzaniu i budżecie powinny zostać ocenione na podstawie pełnej dokumentacji.',styles['Bodyx']))
    doc.build(story); return buf.getvalue()
