# -*- coding: utf-8 -*-
"""
R2_05: 改訂に付随する書類（補足資料、タイトルページ、STROBE、回答書、カバーレター）を生成する。
数値は results/R2_results.json（R2_03_content 経由）から取り込む。既存ファイルがあれば上書きせず停止する（本スクリプトの再実行時は出力フォルダを変更）。
"""
import sys, json, re, copy, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import docx
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import docx_track as T
import R2_03_content as C

sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P
R1 = C.R1
PKG = P.SUB_V4
OUT = R1 / "package"; OUT.mkdir(exist_ok=True)
REFMAP = json.load(open(R1 / "results" / "R2_reference_order.json", encoding="utf-8"))
NEW = {k: i + 1 for i, k in enumerate(REFMAP["order"])}
OLDNEW = {int(o): NEW[k] for o, k in REFMAP["old2key"].items()}
f, pnum, pv_ = C.f, C.pnum, C.pv
def plain(s): return re.sub(r"</?[ib]>", "", s)
def pvt(p): return plain(pv_(p))
def guard(path):
    return path   # 本スクリプトの生成物なので再生成時は上書きする

# ------------------------------------------------------------------ 補足資料（S2-S6）
def add_table(doc, header, rows, widths=None, size=8):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = ""; r = cells[j].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
    doc.add_paragraph()
    return t

def build_supplement():
    d = Document()
    for s in d.sections: s.left_margin = s.right_margin = Cm(1.8)
    d.add_heading("Supplementary Material", 1)
    d.add_paragraph(f"{C.TITLE}. Prefecture-level data are in Supplementary Table S1 (Excel file Supplementary_Table_S1.xlsx). "
                    "Estimates are tablets per resident per year; “per month” means per additional cold month per year (ratio coefficient divided by 12). "
                    "HC3 = heteroscedasticity-consistent standard errors; SLM = spatial lag model; SEM = spatial error model; BH = Benjamini–Hochberg.")
    d.add_heading("Supplementary Table S2. Separate multivariable models for the five temperature indicators", 2)
    rows = []
    for i in C.IND:
        rows.append([i["indicator"], f"{f(i['beta'],2,True)} ({f(i['ci_lo'],2)} to {f(i['ci_hi'],2)})", f(i["std_beta"], 2, True), pnum(i["p_hc3"]), pnum(i["p_bh"]), f(i["adj_r2"], 3)])
    add_table(d, ["Indicator (adjusted for aging, physicians, unemployment, income)", "β per unit (95% CI)", "Standardized β", "p (HC3)", "p (BH-adjusted)", "Adjusted R²"], rows)
    d.add_heading("Supplementary Table S3. Influential observations and spatial models", 2)
    rows = []
    for e in C.EXC:
        rows.append([e["label"], e["n"], f(e["per_month"], 2, True), pnum(e["p_hc3"]), C.sel_names[e["selected"]], f"{f(e['slm_beta'],2,True)} (p = {pnum(e['slm_p'])})", f"{f(e['sem_beta'],2,True)} (p = {pnum(e['sem_p'])})"])
    add_table(d, ["Analysis", "n", "OLS β per month", "OLS p (HC3)", "Model preferred by LM rule", "SLM β per month (p)", "SEM β per month (p)"], rows)
    L = C.SENS["loo"]
    d.add_paragraph(f"Leave-one-prefecture-out (OLS, HC3): p values {pnum(L['p_min'])} to {pnum(L['p_max'])}; β per ratio unit {f(L['beta_min'],1)} to {f(L['beta_max'],1)}; association significant at p < 0.05 in all 47 analyses: {'yes' if L['all_sig'] else 'no'}. "
                    f"Prefectures with Cook’s distance > 4/n (4/47 = {f(C.CK['threshold'],3)}) in the primary model: {', '.join(f'{n} ({f(v,2)})' for n, v in C.CK['over_vals'].items())}.")
    rows = []
    for k, v in sorted(C.ks.items()):
        s = v["sb"]
        rows.append([k, f"{f(s['moran_res'][0],3)} ({pnum(s['moran_res'][2])})", pnum(s["lm_lag"][1]), pnum(s["lm_err"][1]), pnum(s["rlm_lag"][1]), pnum(s["rlm_err"][1]), C.sel_names[v["sel"]],
                     f"{f(s['slm_beta']/12,2,True)} (p = {pnum(s['slm_p'])})", f"{f(s['sem_beta']/12,2,True)} (p = {pnum(s['sem_p'])})"])
    d.add_paragraph("Spatial diagnostics and models by number of nearest neighbors (k):")
    add_table(d, ["k", "Residual Moran’s I (p)", "LM-lag p", "LM-error p", "Robust LM-lag p", "Robust LM-error p", "Model preferred", "SLM β per month (p)", "SEM β per month (p)"], rows)
    d.add_paragraph("Spatial lag model (k = 4 and sensitivity to k): regression coefficient and average direct, indirect, and total effects of one additional cold month per year (tablets per resident per year; 95% intervals from 10,000 simulations of the estimated coefficient and spatial lag parameter, seed 20261102; the total effect equals the coefficient divided by 1 − ρ for a row-standardized weights matrix). The coefficient excludes feedback through neighboring prefectures; the effects include it.")
    erows = []
    for k, e in [(4, C.E4)] + [(int(k), v) for k, v in sorted(C.EK.items())]:
        erows.append([k, f(e["coef_per_month"], 2, True), f(e["rho"], 2)] + [f"{f(e[n]['est'], 2, True)} ({f(e[n]['lo'], 2)} to {f(e[n]['hi'], 2)})" for n in ("direct", "indirect", "total")])
    erows.sort(key=lambda r: r[0])
    add_table(d, ["k", "SLM coefficient per month", "ρ", "Average direct effect", "Average indirect effect", "Average total effect"], erows)
    d.add_heading("Supplementary Table S4. Alternative specifications, drug categories, and age- and sex-standardized outcome", 2)
    rows = [[g["outcome"], g["exposure"], g["covariates"], f(g["std_beta"], 2, True), pnum(g["ols_hc3_p"]), C.sel_names[g["selected"]], pnum(g["selected_p"])] for g in C.GRID]
    add_table(d, ["Outcome", "Exposure", "Covariates", "Standardized β (OLS)", "OLS p (HC3)", "Model preferred by LM rule", "p in selected model"], rows, size=7)
    rows = [[c["category"], f(c["mean"], 1), f(c["per_month"], 2, True), f(c["std_beta"], 2, True), pnum(c["ols_hc3_p"]), pnum(c["ols_p_bh"]), C.sel_names[c["selected"]], pnum(C.cat_sel_p(c)), pnum(c["slm_p"]), pnum(c["sem_p"])] for c in C.CAT]
    d.add_paragraph("Category-specific analyses (tablets only; primary exposure and covariates):")
    add_table(d, ["Drug category", "Mean tablets per resident per year", "OLS β per month", "Standardized β", "OLS p (HC3)", "BH-adjusted p", "Model preferred", "p in selected model", "SLM p", "SEM p"], rows, size=7)
    d.add_paragraph("Indirectly age- and sex-standardized outcome (national tablet quantities per resident by sex and 5-year age group applied to prefecture populations; the standardized ratio is multiplied by the national mean):")
    rows = []
    for key in ("C_crude_reference", "A_primary_covariates", "B_without_aging"):
        r = C.R3[key]; s = r["sb"]
        rows.append([r["label"], f"{f(r['per_month'],2,True)} ({f(r['ci_lo'],2)} to {f(r['ci_hi'],2)})", pnum(r["p_hc3"]), f(s["moran_res"][0], 3), C.sel_names[r["selected"]],
                     f"{f(r['slm_pm'],2,True)} (p = {pnum(s['slm_p'])})", f"{f(r['sem_pm'],2,True)} (p = {pnum(s['sem_p'])})"])
    add_table(d, ["Model", "OLS β per month (95% CI)", "OLS p (HC3)", "Residual Moran’s I", "Model preferred", "SLM β per month (p)", "SEM β per month (p)"], rows)
    d.add_heading("Supplementary Table S5. Additional covariates", 2)
    rows = [[a["model"], a["n"], f(a["per_month"], 2, True), f(a["std_beta"], 2, True), pnum(a["ols_hc3_p"]), C.sel_names[a["selected"]], pnum(a["slm_p"]), pnum(a["sem_p"]), f(a["vif_max"], 1)] for a in C.ADD]
    add_table(d, ["Model (primary covariates plus)", "n", "OLS β per month", "Standardized β", "OLS p (HC3)", "Model preferred", "SLM p", "SEM p", "Max VIF"], rows)
    d.add_paragraph("Body mass index, smoking, and systolic blood pressure are age- and sex-standardized values for specific health checkup attendees aged 40–74 years (fiscal year 2022; NDB Open Data); sodium intake is the mean of the male and female age-adjusted values of the National Health and Nutrition Survey 2016 (unavailable for one prefecture). "
                    "These variables were first compiled with Codex and were then re-extracted from the official tables by separate code written for the revision (column headers, the standardization arithmetic, and the transcription of the National Health and Nutrition Survey table were checked); the values agreed. Standardization is direct, with the pooled respondents of all prefectures in 14 sex-by-age strata (40–74 years) as weights.")
    d.add_heading("Supplementary Table S6. Corrections to the initial submission", 2)
    o = C.ORIG
    rows = [
        ["Cold month ratio", "Described as the proportion of months <10°C; mean 0.09, maximum 0.38", "Computed as months <5°C divided by 60 (2016–2020): multiples of 1/60; mean 0.09, maximum 23/60 = 0.38. The threshold was misreported."],
        ["Global Moran’s I of the outcome (initial outcome definition)", "0.091 (p = 0.114); LISA clusters in Toyama, Ishikawa, Mie, Nara", "0.555 (p = 0.001) after aligning the outcome with the spatial weights matrix; clusters in Hokkaido/Tohoku (High-High) and Kinki (Low-Low)"],
        ["LM tests (initial specification)", "Lag p = 0.40; error p = 0.61; OLS retained", f"Lag p = 0.001; error p = 0.003 (initial specification with aligned data); residual Moran’s I = {f(o['moran_res'],3)}"],
        ["Table 2 (correlation matrix)", "19 of 21 coefficients did not match the data", "Recalculated from the data (Table 2)"],
        ["Covariates", "Physicians per 100,000 (mean 199.6) was hospital full-time-equivalent physicians (Survey of Medical Institutions 2020) and the unemployment rate (mean 3.81%) was the 2020 Census rate, but they were attributed to the Survey of Physicians, Dentists and Pharmacists and the Labour Force Survey; aging rate from the 2020 Census", "Year-aligned covariates re-extracted from official tables (physicians in medical facilities 2022, mean 268.1; unemployment 2023, mean 2.23%; aging 2023)"],
        ["Initial specification (all-unit outcome, initial covariates) with correct alignment", f"OLS standardized β +0.42 (p < 0.001); adjusted R² = {f(o['adj_r2'],3)}", f"Spatial lag p = {pnum(o['slm_p'])}; spatial error p = {pnum(o['sem_p'])}"],
        ["Exposure selection", "Selected by adjusted R² among five indicators and described as pre-specified in the STROBE checklist", "Designated as primary with disclosure that the choice is not independent of the data; other indicators in Supplementary Table S2"],
    ]
    add_table(d, ["Item", "Initial submission", "Revision"], rows)
    d.core_properties.author = "Authors"; d.core_properties.title = "Supplementary Material"
    d.save(guard(OUT / "Supplementary_Material_R1.docx"))

# ------------------------------------------------------------------ タイトルページ
def build_title_page():
    d = Document(str(PKG / "TitlePage_PHRP_v4.docx"))
    tr = T.Tracker("clean")
    P = list(d.paragraphs)
    tr.rewrite(P[0], f"<b>{C.TITLE}</b>")
    tr.rewrite(P[10], f"<b>Running title: {C.RUNNING}</b>")
    tr.rewrite(P[11], "Keywords: " + C.KEYWORDS)
    tr.rewrite(P[20], "<b>Availability of Data and Materials</b>: The 10th NDB Open Data are publicly available from the Ministry of Health, Labour and Welfare of Japan (https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00016.html). "
                      "Japan Meteorological Agency monthly observations are available from https://www.data.jma.go.jp/risk/obsdl/index.php. The processed prefecture-level dataset used in the analyses (exposure, outcome, and covariates for all 47 prefectures) is provided as Supplementary Table S1. "
                      "Analysis code is available on GitHub (https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan; initial release archived on Zenodo, DOI: https://doi.org/10.5281/zenodo.20997811); "
                      "[authors to complete: corrected release and its Zenodo DOI].")
    er = next(r for r in P[8].runs if r.text.startswith("\nEmail"))                      # 責任著者の電話番号（投稿規定: 住所・電話・メール）
    new = copy.deepcopy(er._r); er._r.addnext(new)
    from docx.oxml.ns import qn as _qn
    new.find(_qn("w:t")).text = "Telephone: +81-80-4436-3110"
    d.save(guard(OUT / "TitlePage_PHRP_v5.docx"))

# ------------------------------------------------------------------ STROBE
def clean_pdf_pages():
    import win32com.client as w, fitz
    tmp = R1 / "manuscript" / "_v5_clean_for_pages.pdf"
    word = w.DispatchEx("Word.Application"); word.Visible = False; word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(R1 / "manuscript" / "Manuscript_PHRP_v5_clean.docx"), ReadOnly=True, AddToRecentFiles=False)
        doc.ExportAsFixedFormat(str(tmp), 17); doc.Close(False)
    finally: word.Quit()
    pdf = fitz.open(str(tmp))
    lines = [[l.strip() for l in p.get_text().split("\n")] for p in pdf]
    return lines

def find_pages(lines):
    def occ(head, n=1):
        c = 0
        for i, ls in enumerate(lines):
            if head in ls:
                c += 1
                if c == n: return i + 1
        return None
    pg = dict(abstract=1, intro=occ("Background/rationale"), objectives=occ("Objectives", 2), design=occ("Study Design and Setting"), outcome=occ("Outcome Variables"),
              exposure=occ("Exposure Variables"), covariates=occ("Covariates"), stats=occ("Statistical Methods"), sens=occ("Sensitivity Analyses"), spatial_m=occ("Spatial Analysis"),
              ai=occ("Use of Generative AI"), results=occ("Descriptive Data"), main=occ("Main Results"), spatial_r=occ("Spatial Autocorrelation", 2) or occ("Spatial Autocorrelation"),
              other=occ("Other Analyses"), key=occ("Key Results"), interp=occ("Interpretation"), limit=occ("Limitations"), gener=occ("Generalizability"), refs=occ("References"))
    for i, ls in enumerate(lines):
        for t in range(1, 6):
            if any(l.startswith(f"Table {t}.") for l in ls): pg.setdefault(f"table{t}", i + 1)
    return pg

def build_locator():
    """クリーン版（行番号つき）のWord出力PDFから、見出しごとの頁・行番号を求め、
    回答書の 'Changes:' に埋め込む関数 loc(text) を返す。行番号は本文全体で連続（Word の行番号設定）。"""
    import fitz
    pdf = fitz.open(str(R1 / "manuscript" / "_v5_clean_for_pages.pdf"))
    ents = []                                   # (page, line number, text)
    for pno, page in enumerate(pdf, 1):
        ws = page.get_text("words")
        nums = sorted((w[1], int(w[4])) for w in ws if w[2] < 56 and w[4].isdigit())
        body = [w for w in ws if w[0] >= 56]
        for y, n in nums:
            txt = " ".join(w[4] for w in sorted((w for w in body if abs(w[1] - y) < 4), key=lambda w: w[0]))
            ents.append((pno, n, txt))
    d = Document(str(R1 / "manuscript" / "Manuscript_PHRP_v5_clean.docx"))
    heads = []; on = False
    for p in d.paragraphs:
        if p.style.name.startswith("Heading"):
            lv = int(p.style.name.split()[-1]); t = p.text.strip()
            if lv == 1 and t == "Introduction": on = True
            if on: heads.append((lv, t))
            if lv == 1 and t == "References": break
    pos = []; cur = 0                           # 見出しを順に探す
    for lv, t in heads:
        k = next((i for i in range(cur, len(ents)) if ents[i][2].strip() == t), None)
        pos.append(k)
        if k is not None: cur = k + 1
    ranges = {}
    for i, (lv, t) in enumerate(heads):
        if pos[i] is None or t == "References" or lv < 2: continue
        j = next((pos[m] for m in range(i + 1, len(heads)) if heads[m][0] <= lv and pos[m] is not None), None)
        a = pos[i] + 1; b = (j if j is not None else len(ents)) - 1
        if b < a: continue
        ranges.setdefault(t, []).append((ents[a][0], ents[b][0], ents[a][1], ents[b][1]))
    def fmt(r):
        p1, p2, l1, l2 = r
        pg = f"p. {p1}" if p1 == p2 else f"pp. {p1}–{p2}"
        return f"{pg}, line {l1}" if l1 == l2 else f"{pg}, lines {l1}–{l2}"
    uniq = {t: fmt(r[0]) for t, r in ranges.items() if len(r) == 1}
    ref_k = next((i for i, e in enumerate(ents) if e[2].strip() == "References"), None)
    if ref_k is not None: uniq["References"] = f"p. {ents[ref_k][0]}, line {ents[ref_k][1]}ff."
    tabs = {}
    for e in ents:
        m = re.match(r"Table (\d)\.", e[2].strip())
        if m: tabs.setdefault(m.group(1), e[0])
    def first(txt): return next((i for i, e in enumerate(ents) if e[2].strip() == txt), None)
    def rng(a, b):                                   # 行 a..b（ents のインデックス）の頁・行
        return fmt((ents[a][0], ents[b][0], ents[a][1], ents[b][1]))
    ia, ih, ii = first("Abstract"), first("HIGHLIGHTS"), first("Introduction")
    if None not in (ia, ih, ii):
        uniq["Abstract"] = rng(ia + 1, ih - 1); uniq["Highlights"] = rng(ih + 1, ii - 1)
    fl = first("Figure Legends")
    if fl is not None: uniq["Figure Legends"] = f"p. {ents[fl][0]}"
    def find_line(snip):
        return next((i for i, e in enumerate(ents) if snip in e[2]), None)
    i4, i5 = find_line("Temperature has been examined in relation"), find_line("Japan's archipelago spans")
    if i4 is not None and i5 is not None: uniq["Introduction, fourth paragraph"] = rng(i4, i5 - 1)
    names = sorted(uniq, key=len, reverse=True)
    pat = re.compile("|".join(re.escape(n) for n in names)) if names else None
    def loc(text):
        if pat is not None: text = pat.sub(lambda m: f"{m.group(0)} ({uniq[m.group(0)]})", text)
        text = re.sub(r"Table (\d)(?!\d)", lambda m: f"Table {m.group(1)} (p. {tabs[m.group(1)]})" if m.group(1) in tabs else m.group(0), text)
        return text
    print("locator: 見出し", len(uniq), "件")
    return loc

def build_strobe(pg):
    d = Document(str(PKG / "STROBE_checklist_PHRP.docx"))
    P = d.paragraphs
    for p in P:
        if p.text.startswith("Manuscript:"):
            for r in p.runs[1:]: r.text = ""
            p.runs[0].text = "Manuscript: " + C.TITLE
    t = d.tables[0]
    def pp(*keys): return ", ".join(f"p. {pg[k]}" for k in keys if pg.get(k))
    upd = {
        "1 (a)": f"Title; Abstract (Methods) (p. 1)",
        "1 (b)": "Abstract (p. 1)",
        "2": f"Introduction ({pp('intro')})", "3": f"Introduction, Objectives ({pp('objectives')})",
        "4": f"Methods, Study Design and Setting ({pp('design')})", "5": f"Methods, Study Design and Setting ({pp('design')})",
        "6 (a)": f"Methods, Study Design; Participants ({pp('design')}); N = 47 prefectures",
        "7": f"Methods, Outcome, Exposure, and Covariates ({pp('outcome','exposure','covariates')})",
        "8": f"Methods, Outcome, Exposure, and Covariates ({pp('outcome','exposure','covariates')}); Supplementary Table S1",
        "9": f"Methods, Outcome and Exposure (limitations of the outcome and exposure measures); Discussion, Limitations ({pp('limit')})",
        "10": f"Methods, Study Design (N = 47, all prefectures) ({pp('design')})",
        "11": f"Methods, Exposure; Multivariable OLS Regression (per additional cold month per year; per SD) ({pp('exposure')})",
        "12 (a)": f"Methods, Statistical Methods ({pp('stats')}); Spatial Analysis ({pp('spatial_m')})",
        "12 (b)": f"Methods, Primary Exposure and Model Specification ({pp('stats')}); no subgroup or interaction analyses",
        "12 (c)": f"Methods, Outcome (masked cells not imputed) and Covariates (no imputation) ({pp('outcome','covariates')})",
        "12 (e)": f"Methods, Sensitivity Analyses ({pp('sens')}); Results, Other Analyses ({pp('other')}); Supplementary Tables S2–S5",
        "13 (a)": f"Methods, Participants; Results, Participants (N = 47) ({pp('results')})",
        "14 (a)": f"Results, Descriptive Data; Table 1 ({pp('results','table1')})",
        "14 (b)": f"Results, Descriptive Data (no missing data for the primary variables; sodium unavailable for one prefecture in a sensitivity analysis) ({pp('results')})",
        "15": f"Results, Descriptive Data; Table 1 ({pp('results','table1')})",
        "16 (a)": f"Results, Main Results; Tables 3–4 ({pp('main','table3','table4')})",
        "16 (b)": f"Methods, Exposure Variables (<5°C threshold; 60 months) ({pp('exposure')})",
        "16 (c)": f"Results, Main Results (per additional cold month per year; per SD) ({pp('main')})",
        "17": f"Results, Spatial Autocorrelation; Other Analyses; Table 5 ({pp('spatial_r','other','table5')}); Supplementary Tables S2–S6",
        "18": f"Discussion, Key Results ({pp('key')})", "19": f"Discussion, Limitations ({pp('limit')})",
        "20": f"Discussion, Interpretation ({pp('interp')})", "21": f"Discussion, Generalizability ({pp('gener')})",
    }
    n = 0
    for row in t.rows[1:]:
        key = row.cells[0].text.strip()
        if key in upd:
            c = row.cells[2]
            for p in c.paragraphs[1:]: p._p.getparent().remove(p._p)
            p0 = c.paragraphs[0]
            for r in p0.runs[1:]: r.text = ""
            if p0.runs: p0.runs[0].text = upd[key]
            else: p0.add_run(upd[key])
            n += 1
    d.core_properties.title = "STROBE checklist (revised)"
    d.save(guard(OUT / "STROBE_checklist_R1.docx"))
    return n

# ------------------------------------------------------------------ 回答書・カバーレター
def para(d, text, bold=False, italic=False, size=None, style=None):
    p = d.add_paragraph(style=style); r = p.add_run(text); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    return p

LOC = [lambda t: t]
def item(d, no, comment, response, change):
    p = para(d, f"{no}  ", bold=True); r = p.add_run(comment); r.italic = True
    p2 = para(d, "Response: ", bold=True); p2.add_run(response)
    p3 = para(d, "Changes: ", bold=True); p3.add_run(LOC[0](change))

def build_response(loc=lambda t: t):
    LOC[0] = loc
    d = Document()
    for s in d.sections: s.left_margin = s.right_margin = Cm(2.2)
    d.add_heading("Response to Reviewers", 1)
    para(d, f"Manuscript ID OPHRP-2026-0484 — revised title: {C.TITLE}")
    para(d, "Page and line numbers refer to the clean version of the revised manuscript (continuous line numbering; the tables and figure legends follow the references). Changes are tracked in the marked version. Reference numbers in the revised manuscript differ from the initial version because the references were renumbered in order of first citation; the corresponding numbers are given below.", italic=True)
    d.add_heading("Summary of the revision and corrections to the initial submission", 2)
    para(d, "Re-examining the original analysis scripts and data in response to the comments of Reviewer 3 showed that several results of the initial submission were incorrect. We report them openly because they change the conclusions.")
    for t in [
        "The cold month ratio was computed as the proportion of the 60 months from January 2016 to December 2020 with a mean temperature below 5°C, not below 10°C as stated. The 5°C threshold was in the analysis configuration; the manuscript misreported it. This resolves the issues raised in A1 (a maximum of 0.38 equals 23/60; the mean of 0.09 reflects the 5°C threshold).",
        "The spatial autocorrelation analysis contained a data-alignment error: the outcome vector and the spatial weights matrix were ordered differently. Correcting this changes Global Moran’s I from 0.091 (p = 0.114) to 0.555 (p = 0.001) for the initial outcome definition, the LISA clusters, and the LM tests. The statements that there was no spatial autocorrelation and that this supported OLS were therefore wrong, and they have been removed.",
        "Table 2 (correlation matrix) did not match the data for 19 of 21 coefficients. It has been recalculated from the data.",
        "Physician density and unemployment rate were attributed to the wrong sources (A4): the physician variable was hospital full-time-equivalent physicians per 100,000 (Survey of Medical Institutions 2020), not physicians in the Survey of Physicians, Dentists and Pharmacists, and the unemployment rate was the 2020 Census rate, not the Labour Force Survey rate. Year-aligned covariates were re-extracted from the official tables. The unemployment rate is no longer significantly associated with the outcome.",
        f"With the revised analysis, the association between the cold month ratio and dispensed tablets is significant in OLS ({f(C.pm['beta'])} tablets per resident per year for each additional cold month per year; 95% CI {f(C.pm['ci_lo'])} to {f(C.pm['ci_hi'])}), but it is not significant in the spatial lag model that the LM decision rule preferred (the robust LM tests did not clearly distinguish lag from error dependence) (p = {pnum(C.B4['slm_p'])}) and is significant at the 5% level in the spatial error model (p = {pnum(C.B4['sem_p'])}). The conclusions have been revised to describe the findings as exploratory and model-dependent, and the title has been changed accordingly.",
        "The cold month ratio was selected as the primary exposure because it had the best fit among five indicators; this is now disclosed, and the statement in the STROBE checklist that the exposure was pre-specified has been corrected.",
    ]: d.add_paragraph(t, style="List Bullet")
    para(d, "Supplementary Table S6 lists the corrections.")
    d.add_heading("Reviewer 1", 2)
    para(d, "Comment: The article was reviewed according to the STROBE guidelines and found suitable for publication.", italic=True)
    para(d, "Response: We thank Reviewer 1. Because the revision changed the findings and conclusions as described above, we have updated the STROBE checklist.")
    d.add_heading("Reviewer 2", 2)
    para(d, "No comments.", italic=True)
    d.add_heading("Reviewer 3", 2)
    A = "A. Required revisions"
    d.add_heading(A, 3)
    sd = C.D["x"]["sd"]
    items = [
      ("A1-1", "Specify how the cold month ratio was derived: weather station(s), reference period, and exact calculation.",
       "The ratio is the number of months with a mean temperature below 5°C divided by 60 (January 2016–December 2020), from the JMA station of each prefecture (the prefectural capital in 44 prefectures; Kumagaya, Hikone, and Shimonoseki for Saitama, Shiga, and Yamaguchi). The reference period is 2016–2020 and is not matched to FY2023.",
       "Methods, Exposure Variables; Supplementary Table S1."),
      ("A1-2", "With one year of monthly data the ratio takes increments of 1/12; the maximum of 0.38 does not correspond to such a value.",
       "The ratio is based on 60 months and takes multiples of 1/60; the maximum of 0.38 equals 23/60. The initial manuscript did not state the number of months and misreported the threshold.",
       "Methods, Exposure Variables."),
      ("A1-3", "The Discussion states that ratios above 0.20 mean four or more months below 10°C, but four months corresponds to 0.33.",
       "This statement was incorrect (a ratio of 0.20 corresponds to 2.4 months per year below 5°C). The sentence was removed.",
       "Discussion, Climate, Cold-Season Duration, and Pharmaceutical Demand."),
      ("A1-4", "The mean of 0.09 seems low; provide prefecture-level values for all 47 prefectures with the source data.",
       "Prefecture-level values of the exposure (number of months below 5°C, ratio, stations), outcome, and covariates are given in Supplementary Table S1. The mean of 0.09 results from the 5°C threshold (a 10°C threshold would give a mean of about 0.30).",
       "Supplementary Table S1 (Excel)."),
      ("A1-5", "Rescale the coefficient to an interpretable unit (per additional cold month or per SD).",
       f"The coefficient is now given per additional cold month per year ({f(C.pm['beta'])}; 95% CI {f(C.pm['ci_lo'])} to {f(C.pm['ci_hi'])}) and per SD of the ratio ({f(C.psd['beta'])}; SD = {f(sd,3)}).",
       "Results, Main Results; Table 4; Abstract."),
      ("A2-1", "List the therapeutic category codes and the NDB Open Data tables used.",
       "Categories 214, 217, 218, 219, and 333; the oral outpatient (dispensed outside the institution) table by prefecture of the 10th NDB Open Data, excluding claims paid with public expenditure.",
       "Methods, Outcome Variables."),
      ("A2-2", "State the unit of “total quantity”; if dosage units, revise “prescription rate”.",
       "The quantity is in dosage units. The initial outcome summed all units of measurement (93.7% of the quantity was tablets). The primary outcome is now tablets only, expressed per resident per year, and the term “prescription rate” was replaced by “dispensed tablets” throughout.",
       "Title; Abstract; Methods, Outcome Variables; throughout."),
      ("A2-3", "Summing quantities across classes with different dosing units is difficult to interpret; standardization (e.g., DDD per 1,000 inhabitants per day) and class-specific analyses are encouraged.",
       "We restricted the primary outcome to one unit (tablets), analysed all units, category 214 alone, and each category separately (Supplementary Table S4), and added an indirectly age- and sex-standardized outcome (A2-7). We also examined a partial conversion to DDD for single-agent tablets of category 214, but we do not report it: the correspondence between products, active substances, and WHO DDD values could be checked only mechanically against product names and could not be independently verified, and the conversion covered only part of the quantity (combination products and products without a WHO DDD could not be converted). The lack of dose standardization (defined daily doses) is stated as a limitation.",
       "Methods, Outcome Variables; Results, Other Analyses; Discussion, Limitations; Supplementary Table S4."),
      ("A2-4", "State whether prefecture attribution reflects the institution or the patient’s residence and discuss cross-prefecture care-seeking.",
       "Attribution reflects the location of the dispensing pharmacy or medical institution. This is stated and discussed.",
       "Methods, Outcome Variables; Discussion, Limitations."),
      ("A2-5", "State whether the published tables cover all prescriptions or a subset and how this affects totals.",
       "The tables list a limited number of products per category, and cells with small counts are masked (2.9% of tablet cells, not imputed); the outcome is a lower bound.",
       "Methods, Outcome Variables; Discussion, Limitations."),
      ("A2-6", "Specify the source and year of the population denominator.",
       "Total resident population on 1 October 2023 (Population Estimates, Statistics Bureau). The initial analysis used the 2020 Census.",
       "Methods, Outcome Variables."),
      ("A2-7", "Provide age- and sex-standardized estimates or justify crude rates with aging as a covariate.",
       f"Direct standardization is not possible because the published tables do not give quantities cross-classified by prefecture, age, and sex, so the primary analysis used crude per-resident quantities adjusted for the aging rate. We added an indirectly age- and sex-standardized outcome (national tablet quantities per resident by sex and 5-year age group from the NDB sex-age table, applied to prefecture populations by sex and age group; Population Estimates 2023). It reduced the correlation of the outcome with the aging rate from {f(C.R3['r_aging_crude'],2)} to {f(C.R3['r_aging_std'],2)}. The pattern of results was unchanged: OLS {f(C.R3['A_primary_covariates']['per_month'])} tablets per resident per year per cold month ({pvt(C.R3['A_primary_covariates']['p_hc3'])}), spatial lag {pvt(C.R3['A_primary_covariates']['sb']['slm_p'])}, spatial error {pvt(C.R3['A_primary_covariates']['sb']['sem_p'])} (Supplementary Table S4).",
       "Methods, Outcome Variables and Sensitivity Analyses; Results, Other Analyses; Supplementary Table S4; Discussion, Limitations."),
      ("A3-1", "Designate a single primary exposure with an a priori rationale; reconcile “selected by best model fit” with STROBE 12(e); report the other four indicators as sensitivity analyses including multivariable models.",
       "The cold month ratio is designated as primary because it captures cumulative cold-season duration. We state that the choice is not independent of the data because it had the best fit in the initial analysis. The other four indicators are reported in separate multivariable models (Supplementary Table S2). STROBE item 12(e) was corrected.",
       "Methods, Exposure Variables; Primary Exposure and Model Specification; Results, Other Analyses; STROBE checklist."),
      ("A3-2", "Include dietary sodium, hypertension prevalence, BMI, and smoking, or justify their omission.",
       "BMI, smoking, systolic blood pressure, the share of attendees with systolic blood pressure ≥140 mmHg (a proxy; hypertension prevalence is not published), and sodium intake were added in sensitivity analyses (Supplementary Table S5). The association is attenuated and not significant with smoking added. These variables were first compiled with AI assistance and were then re-extracted from the official tables with separate code; the values agreed, and the process is disclosed.",
       "Methods, Covariates; Results, Other Analyses; Supplementary Table S5; Use of Generative AI."),
      ("A3-3", "Assess spatial autocorrelation on the OLS residuals, ideally with LM diagnostics.",
       f"Done. The residuals are spatially autocorrelated (Moran’s I = {f(C.B4['moran_res'][0],3)}, {pvt(C.B4['moran_res'][2])}); LM diagnostics and spatial lag and error models are reported (Table 5); the spatial lag coefficient is now identified as a regression coefficient that excludes feedback through neighboring prefectures, and its average direct, indirect, and total effects with simulation-based intervals are reported (Table 5; Supplementary Table S3); the LISA clusters are labelled exploratory and are not corrected for multiple testing. The assessment also revealed the alignment error described above.",
       "Methods, Spatial Analysis; Results, Spatial Autocorrelation; Table 5."),
      ("A3-4", "Identify the influential prefectures (Cook’s distance ≈ 0.58 and several above 4/n) and report analyses excluding them and excluding Hokkaido and Okinawa.",
       f"In the revised model, {len(C.cook_over)} prefectures exceeded 4/n ({', '.join(C.cook_over)}; maximum {f(C.CK['max_val'],2)}, {C.CK['max_name']}). Excluding them, excluding Hokkaido and Okinawa, and leave-one-out analyses are reported (Supplementary Table S3).",
       "Results, Main Results and Other Analyses; Figure 2; Supplementary Table S3."),
      ("A3-5", "The Durbin–Watson statistic is not informative for cross-sectional data and may be removed.", "Removed.", "Methods, Multivariable OLS Regression; Results, Main Results; Table 4 note."),
      ("A3-6", "The Moran’s I of 0.311 for total volume in the Discussion is not reported in Methods or Results; report it formally or remove it.",
       "The statement was removed.", "Discussion, Spatial Dependence and Model Dependence."),
      ("A4-1", "Specify the survey year and definition of each covariate; the aging rate is from 2020 and the outcome from FY2023.",
       "Covariates were aligned to the outcome year: aging rate (1 October 2023), physicians in medical facilities (31 December 2022), unemployment rate (calendar 2023, model-based), per capita income (FY2022). Sources and years are listed.",
       "Methods, Covariates."),
      ("A4-2", "Verify the unemployment and physician density figures against the stated sources.",
       "The initial values came from different sources than those stated. The physician variable (mean 199.6 per 100,000) was the full-time-equivalent number of physicians in hospitals per 100,000 population from the 2020 Survey of Medical Institutions (e-Stat table 0004002104), not physicians working in medical facilities as counted in the Survey of Physicians, Dentists and Pharmacists (official 2022 figure: mean 268.1). The unemployment rate (mean 3.81%) was calculated from the 2020 Census (e-Stat table 0003450538: unemployed persons divided by the labour force), not from the Labour Force Survey (2023 model-based estimate: mean 2.23%). Both were replaced by values re-extracted from the official tables of the stated sources, with years aligned to the outcome. As a result, the unemployment rate is no longer significantly associated with the outcome, and the corresponding Discussion was rewritten.",
       "Methods, Covariates; Results, Descriptive Data and Main Results; Discussion, Unemployment as a Socioeconomic Determinant."),
      ("A5-1", "Moderate causal language (e.g., “Climate leaves a measurable footprint”).",
       "The sentence was removed and causal wording was moderated throughout, including the title. The findings are described as exploratory.", "Title; Abstract; Discussion; Conclusion."),
      ("A5-2", "The Highlight on housing insulation as a cost-effective strategy is not examined; remove it or present it as a hypothesis.",
       "The Highlight was removed, and insulation is discussed only as a hypothesis.", "Highlights; Discussion, Possible Health-System Implications."),
      ("A6-1", "Move the AI disclosure to a Methods subsection, describe the extent of use, and how AI-assisted drafting and code were verified.",
       "A subsection “Use of Generative AI” in Methods describes the use, which extended beyond language editing, and how the data were checked. Because the journal does not permit AI-assisted tools for creating or altering images, the subsection states exactly how the figures were made: plotting code was run on the numerical results; the code was written with AI assistance; no image was generated, edited, or retouched by AI. The cover letter asks the editorial office to confirm that this procedure is acceptable. The subsection also states that the authors reviewed and edited the AI-assisted code, numerical results, and text, and confirms that the AI-assisted text, code, and figures contain no plagiarism and that no AI-generated material is cited as a primary source (as the journal’s policy requires).",
       "Methods, Use of Generative AI."),
      ("A6-2", "Use the journal’s reference style and renumber in order of first citation (reference 32 was cited before 13).",
       "References are numbered in square brackets in order of first citation, with up to three authors followed by “et al.”. The list was rebuilt (" + str(len(C.REFS)) + " references).", "References."),
      ("A6-3", "Ensure the title page includes ethics approval, conflicts of interest, funding, data availability, CRediT, and ORCID.", "The title page includes all of these items; the data availability statement was updated.", "Title page."),
      ("A6-4", "Share the processed prefecture-level dataset and analysis code.",
       "The processed dataset is provided as Supplementary Table S1. The code is in the GitHub repository; a corrected release is [authors to complete: release and DOI].", "Title page; Supplementary Table S1."),
    ]
    for no, cm, rs, ch in items: item(d, no, cm, rs, ch)
    d.add_heading("B. Recommended revisions", 3)
    items = [
      ("B1", "Cite and discuss studies linking temperature to prescribing (Mihara et al.; England; Spain) and clarify novelty.", "Added to the Introduction with the novelty relative to them.", "Introduction, fourth paragraph."),
      ("B2", "Consider that outdoor and indoor temperatures may not align across prefectures.", "Added.", "Discussion, Climate, Cold-Season Duration, and Pharmaceutical Demand."),
      ("B3", "Consider whether medical assistance (public assistance) claims are captured in the NDB.", "The tables used exclude claims paid with public expenditure, so these prescriptions are probably not captured. Added.", "Discussion, Unemployment as a Socioeconomic Determinant; Limitations."),
      ("B4", "A multi-year panel with prefecture fixed effects would strengthen the design.", "A multi-year panel requires harmonizing the published products, units, and suppression across releases and was not feasible in this revision. It is stated as a limitation and a direction for future research.", "Discussion, Limitations and Conclusion."),
      ("B5", "Place the Limitations after the Interpretation section.", "Done.", "Discussion, Limitations."),
      ("B6", "Submit figures at 500 dpi or higher.", "Figures were regenerated from the data at 500 dpi (JPG, 16.5 cm wide). Figure 3 (spatial clusters) was added.", "Figure Legends; Figures 1–3 (separate JPG files)."),
    ]
    for no, cm, rs, ch in items: item(d, no, cm, rs, ch)
    d.add_heading("C. Corrections to the reference list", 3)
    items = [
      ("C1 (Ref 6)", "The citation (1985;290:75) does not correspond to the original article by Keatinge et al.", f"Corrected to Br Med J (Clin Res Ed) 1984;289(6456):1405–8, doi:10.1136/bmj.289.6456.1405 (now reference {OLDNEW[6]}).", "References."),
      ("C2 (Ref 19)", "Now published in J Hypertens 2026;44(1):109–115; verify the author list.", f"Updated; the author list was corrected to Tabara Y, Kushida O, Ozaki E, et al. (now reference {OLDNEW[19]}).", "References."),
      ("C3 (Ref 10)", "Replace the JMA tourist information page with the specific JMA climate statistics source.", f"Replaced with the JMA past weather data download portal (monthly values; now reference {OLDNEW[10]}); the monthly mean temperatures of the 47 stations were downloaded from this portal on 2 March 2026.", "References."),
      ("C4 (Ref 23)", "Iwabe et al. analyzed health check-up data of the Japan Health Insurance Association rather than claims data.", f"The description was revised (now reference {OLDNEW[23]}).", "Discussion, Aging, Healthcare Context, and Prescription Dynamics."),
      ("C5 (Ref 22)", "Revise the description to reflect that Ogata et al. quantified the contributions of changes in risk factor distributions.", f"Revised (now reference {OLDNEW[22]}).", "Discussion, Aging, Healthcare Context, and Prescription Dynamics."),
      ("C6 (Ref 26)", "“Unemployed” in the JACC Study refers to baseline employment status and may include retirees; temper the interpretation.", f"The caveat was added and the interpretation tempered (now reference {OLDNEW[26]}).", "Discussion, Unemployment as a Socioeconomic Determinant."),
      ("C7 (Ref 1)", "Add the date of access.", "Added (reference 1).", "References."),
      ("C8 (Ref 2)", "Add a URL and the specific table cited.", "Added URL and table (Table 10; reference 2).", "References."),
    ]
    for no, cm, rs, ch in items: item(d, no, cm, rs, ch)
    d.add_heading("Other changes made by the authors", 2)
    para(d, "The following changes were not requested by the reviewers; they are listed so that every change in the marked manuscript is accounted for.")
    for t in [
        "Title, running title, and keywords were changed to avoid causal wording and to match the revised outcome and methods (see A5-1).",
        "Introduction: the statement that cardiovascular diseases are the second leading cause of death was changed to heart disease, in line with the cited source (reference 2).",
        "Abstract, Highlights, Discussion (Key Results, Strengths), and Conclusion were rewritten to reflect the revised findings; Discussion headings were renamed (“Spatial Dependence and Model Dependence”; “Possible Health-System Implications”).",
        "Two Discussion paragraphs on policy implications of the unemployment association and on climate adaptation policy were deleted because the unemployment association was not retained and the claims were not supported by the analysis.",
        "Figures 1 and 2 were redrawn for the revised outcome and diagnostics, and Figure 3 (spatial clusters) was added. The figures are no longer embedded in the manuscript file; only the legends remain at the end of the manuscript, and the figures are supplied as separate JPG files.",
        "The text was condensed to meet the 5,000-word limit: background passages in the Discussion (aging, unemployment, policy), the Methods, and descriptive Results text that duplicates the tables were shortened, and the Abstract was shortened; no analysis or conclusion was changed by this.",
        "Supplementary Table S6 lists the corrections to the initial submission; document properties were anonymized.",
    ]: d.add_paragraph(t, style="List Bullet")
    d.add_heading("Items to be submitted with the revision", 2)
    for t in ["Revised manuscript with changes highlighted (Manuscript_PHRP_v5_marked.docx) and a clean version", "Updated STROBE checklist", "Supplementary Table S1 (prefecture-level data) and Supplementary Material (Tables S2–S6)", "Title page", "Figures 1–3 (JPG, 500 dpi)"]:
        d.add_paragraph(t, style="List Bullet")
    d.core_properties.author = "Authors"; d.core_properties.title = "Response to Reviewers"
    d.save(guard(OUT / "Response_to_Reviewers_R1.docx"))

def build_cover():
    d = Document()
    for s in d.sections: s.left_margin = s.right_margin = Cm(2.4)
    for t in ["[Date of submission]", "", "Editor-in-Chief", "Osong Public Health and Research Perspectives", "Korea Disease Control and Prevention Agency", "", "Dear Professor Lee,", ""]: para(d, t)
    para(d, f"Please find enclosed the revised version of our manuscript, OPHRP-2026-0484 (now titled “{C.TITLE}”), together with a point-by-point response to the reviewers. We thank you and the reviewers for the careful and constructive comments.")
    para(d, "In responding to Reviewer 3, we re-examined the original analysis scripts and data and found errors in the initial submission that change its conclusions: the exposure threshold was misreported (5°C over 60 months, not 10°C); the spatial autocorrelation analysis contained a data-alignment error, so Global Moran’s I and the LISA clusters were wrong and the claim of no spatial autocorrelation does not hold; the correlation matrix did not match the data; and two covariates were attributed to the wrong sources. We have corrected these and report them in the response letter and Supplementary Table S6.")
    para(d, "The revised analysis shows that a longer cold season is associated with larger quantities of cardiovascular tablets dispensed per resident in conventional regression, but that the association is not significant in the spatial lag model, which the standard decision rule preferred although the robust diagnostics did not clearly distinguish it from the spatial error model (in which the association is significant), and is attenuated after adjustment for smoking. We therefore present the findings as exploratory and hypothesis-generating, and we have revised the title, abstract, and conclusions accordingly.")
    para(d, "The study used only publicly available aggregate data, and ethics review was not required. The authors declare no conflicts of interest. The use of generative AI, which extended beyond language editing, is described in the Methods, where the authors also confirm that the AI-assisted text, code, and figures contain no plagiarism and that no AI-generated material is cited as a primary source. The journal does not permit AI-assisted tools for creating or altering images. Our figures were drawn by running plotting code on the numerical data; the code was written with AI assistance, but no image was generated, edited, or retouched by AI. As this policy could be read to cover AI-assisted plotting code, we would be grateful if the editorial office could confirm that this procedure is acceptable; if it is not, we will redraw the figures with code written without AI assistance. The manuscript has not been published or submitted elsewhere. All authors have read and approved the revised manuscript.")
    for t in ["", "Sincerely,", "", "Haruki Saito", "Department of Epidemiology, Fukushima Medical University School of Medicine", "1 Hikarigaoka, Fukushima-shi, Fukushima 960-1295, Japan", "Email: m211039@fmu.ac.jp", "ORCID: 0009-0009-7890-6068"]: para(d, t)
    d.core_properties.title = "Cover letter (revision)"
    d.save(guard(OUT / "CoverLetter_R1.docx"))

if __name__ == "__main__":
    build_supplement(); print("supplement ok")
    build_title_page(); print("title page ok")
    try:
        lines = clean_pdf_pages(); pg = find_pages(lines); print("pages:", pg)
    except Exception as e:      # Word（COM）が無い環境ではSTROBEのページ番号を省略する
        pg = {}; print("ページ番号の取得をスキップ（Word COM が利用できない）:", type(e).__name__)
    print("strobe rows updated:", build_strobe(pg))
    try: loc = build_locator()
    except Exception as e: loc = (lambda t: t); print("頁・行番号の取得をスキップ:", type(e).__name__, e)
    build_response(loc); print("response ok")
    build_cover(); print("cover ok")
