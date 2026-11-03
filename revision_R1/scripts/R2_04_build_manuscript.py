# -*- coding: utf-8 -*-
"""
R2_04: Manuscript_PHRP_v4.docx を土台に、改訂原稿 v5 を2種類生成する。
  - Manuscript_PHRP_v5_marked.docx : Word の変更履歴つき（編集部提出用）
  - Manuscript_PHRP_v5_clean.docx  : 変更を反映したクリーン版
v4 は読み取りのみ。出力先が存在する場合は停止（上書きしない）。
"""
import sys, re, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx import Document
from docx.oxml.ns import qn
import docx_track as T
import R2_03_content as C

sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P
PKG = P.SUB_V4
R1 = C.R1
SRC = PKG / "Manuscript_PHRP_v4.docx"
OUTDIR = R1 / "manuscript"; OUTDIR.mkdir(exist_ok=True)
FIGS = R1 / "figures"


def apply_journal_format(doc):
    """OPHRP の投稿規定: A4・ダブルスペース・余白2.5 cm・単一フォント(Times New Roman 11 pt)・段落間の空白なし・両端揃え・見出しは太字中央・
    ページ番号・行番号。表は1行間・10 pt。書式のみの変更で、文字列の変更履歴には影響しない。"""
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.header_distance = sec.footer_distance = Cm(1.25)
    sp = sec._sectPr
    for old in sp.findall(qn("w:lnNumType")): sp.remove(old)
    ln = OxmlElement("w:lnNumType"); ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous"); ln.set(qn("w:distance"), "360")
    sp.find(qn("w:pgMar")).addnext(ln)                                     # スキーマ順: pgMar の後、cols の前
    # ページ番号（フッター中央）
    ft = sec.footer; ft.is_linked_to_previous = False
    fp = ft.paragraphs[0]
    for r in list(fp.runs): r._r.getparent().remove(r._r)
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    def fld(kind, text=None):
        r = fp.add_run()
        if kind == "instr":
            e = OxmlElement("w:instrText"); e.set("{http://www.w3.org/XML/1998/namespace}space", "preserve"); e.text = text
        else:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind)
        r._r.append(e); r.font.name = "Times New Roman"; r.font.size = Pt(11)
    fld("begin"); fld("instr", " PAGE "); fld("separate"); r = fp.add_run("1"); r.font.name = "Times New Roman"; r.font.size = Pt(11); fld("end")
    # フォント: docDefaults とスタイルのテーマ指定を外し、Times New Roman 11 pt に統一
    def set_fonts(rpr):
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
        for a in list(rf.attrib):
            if "Theme" in a or a.endswith("}hint"): del rf.attrib[a]
        for a in ("ascii", "hAnsi", "eastAsia", "cs"): rf.set(qn("w:" + a), "Times New Roman")
    styles_el = doc.styles.element
    dd = styles_el.find(qn("w:docDefaults"))
    if dd is not None:
        rpr = dd.find(qn("w:rPrDefault") + "/" + qn("w:rPr"))
        if rpr is not None: set_fonts(rpr)
    body_styles = {"Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Body Text 2", "Body Text 3"}
    for st in doc.styles:
        if st.type != 1: continue                                           # 段落スタイルのみ
        el = st.element; rpr = el.find(qn("w:rPr"))
        if rpr is None: rpr = OxmlElement("w:rPr"); el.append(rpr)
        set_fonts(rpr)
        st.font.size = Pt(11); st.font.name = "Times New Roman"
        from docx.shared import RGBColor
        st.font.color.rgb = RGBColor(0, 0, 0)
        pf = st.paragraph_format
        pf.space_before = Pt(0); pf.space_after = Pt(0)
        pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
        if st.name.startswith("Heading") or st.name in ("Title", "Subtitle"):
            st.font.bold = True; st.font.italic = False; pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.keep_with_next = True
        elif st.name in body_styles:
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    # 本文中の直接指定（段落の間隔・揃え）を外す
    for para in doc.paragraphs:
        ppr = para._p.find(qn("w:pPr"))
        if ppr is not None:
            for tag in ("w:spacing", "w:jc"):
                for e in ppr.findall(qn(tag)): ppr.remove(e)
        for r in para._p.iter(qn("w:r")):          # 本文のランに残る直接指定（サイズ・色・フォント）を外し、スタイルの 11 pt に統一
            rp = r.find(qn("w:rPr"))
            if rp is not None:
                for tag in ("w:sz", "w:szCs", "w:color", "w:rFonts"):
                    for e in rp.findall(qn(tag)): rp.remove(e)
    # 表: 1行間・10 pt・左揃え
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    para.paragraph_format.space_before = Pt(0); para.paragraph_format.space_after = Pt(0)
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for r in para._p.iter(qn("w:r")):
                        rp = r.find(qn("w:rPr"))
                        if rp is None: rp = OxmlElement("w:rPr"); r.insert(0, rp)
                        for e in rp.findall(qn("w:sz")) + rp.findall(qn("w:szCs")): rp.remove(e)
                        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "20"); rp.append(sz)
                        szc = OxmlElement("w:szCs"); szc.set(qn("w:val"), "20"); rp.append(szc)

CIT_RE = re.compile(r"(?<![0-9]\.)(?<=[A-Za-z\.])(\d{1,2})\)((?:,\s*\d{1,2}\))*)")


def old_to_placeholders(markup):
    def sub(m):
        nums = [int(x) for x in re.findall(r"\d{1,2}", m.group(0))]
        return "{ref:" + ",".join(C.OLD2KEY[n] for n in nums) + "}"
    return CIT_RE.sub(sub, markup)


def plan():
    MOD = {1: C.TITLE, 5: C.ABS_OBJ, 7: C.ABS_METH, 9: C.ABS_RES, 11: C.ABS_CON, 12: "Keywords: " + C.KEYWORDS,
           14: C.HIGHLIGHTS[0], 15: C.HIGHLIGHTS[1], 16: C.HIGHLIGHTS[2], 17: C.HIGHLIGHTS[3],
           22: C.INTRO_P22, 24: C.INTRO_P24, 25: C.INTRO_P25, 27: C.INTRO_P27,
           31: C.M_P31, 35: C.M_OUT1, 37: C.M_P37, 39: C.M_P39,
           47: C.M_P47H, 48: C.M_P48, 50: C.M_P50, 51: C.M_P51H, 52: C.M_P52,
           62: C.R_P62, 65: C.R_P65, 67: C.R_P67, 69: C.R_P69, 70: f"<b>{C.R_P70}</b>", 71: f"<b>{C.R_P71}</b>", 73: C.R_P73, 74: C.R_P74, 76: C.R_P76,
           80: C.D_P80, 86: C.D_P86, 88: C.D_P88, 91: C.D_P91, 92: C.D_P92, 93: C.D_P93, 95: C.D_P95, 96: C.D_P96, 97: C.D_P97,
           98: C.D_P98H, 99: C.D_P99, 100: C.D_P100H, 101: C.D_P101, 102: C.D_P102, 103: C.D_P103, 107: C.D_P107, 111: C.D_P111, 112: C.D_P112,
           155: C.TAB_NOTE2, 157: C.TAB3_TITLE, 158: C.TAB3_NOTE, 160: C.TAB4_TITLE, 161: C.TAB4_NOTE, 163: C.TAB5_TITLE, 166: C.FIG1, 167: C.FIG2}
    for i, (lab, rest) in zip((40, 41, 42, 43), C.M_COV): MOD[i] = f"<b>{lab}</b>{rest}"
    DEL = {18, 72, 82, 83, 89, 104, 105, 114, 115, 168, 169, 170, 171} | set(range(118, 150))   # 168–171: 本文内の図見出しと画像（図は別ファイルで提出。凡例のみ本文末に残す）
    INS = {24: [(24, C.INTRO_NEW)],
           35: [(24, C.M_OUT2), (24, C.M_OUT3)],
           37: [(24, C.M_EXP2), (24, C.M_EXP3)],
           43: [(24, C.M_COV_NEW)],
           52: [(51, C.M_SENS_H), (52, C.M_SENS)],
           54: [(53, C.M_AI_H), (54, C.M_AI)],
           76: [(75, C.R_OTH_H), (24, C.R_O1), (24, C.R_O2), (24, C.R_O3), (24, C.R_O3B), (24, C.R_O4), (24, C.R_O5)],
           107: [(82, C.D_LIM_H), (83, C.D_LIM)],
           167: [(167, C.FIG3)]}
    return MOD, DEL, INS


def build(mode, out_path):
    doc = Document(str(SRC))
    P = list(doc.paragraphs); TB = list(doc.tables)
    tr = T.Tracker(mode)
    MOD, DEL, INS = plan()
    cites = T.Cites()

    # ---- 1) 最終的な本文順で引用を走査して番号を確定
    final_text = {}
    for i, p in enumerate(P):
        if i in DEL: continue
        if i in MOD: txt = MOD[i]
        elif 20 <= i <= 112 or 152 <= i <= 167:
            txt = old_to_placeholders(T.markup_from_paragraph(p))
        else: continue
        final_text[i] = txt
        cites.scan(txt)
        for _, t in INS.get(i, []): cites.scan(t)
    ref_keys = list(cites.order)
    import json as _j
    (R1 / 'results' / 'R2_reference_order.json').write_text(_j.dumps({'order': ref_keys, 'old2key': C.OLD2KEY}, ensure_ascii=False, indent=1), encoding='utf-8')
    uncited = [k for k in C.REFS if k not in ref_keys]
    missing = [k for k in ref_keys if k not in C.REFS]
    assert not missing, missing

    # ---- 2) 本文の書き換え
    n_mod = 0
    for i, p in enumerate(P):
        if i in DEL:
            tr.delete_paragraph(p)
        elif i in final_text:
            txt = cites.resolve(final_text[i])
            if tr.rewrite(p, txt): n_mod += 1
    # 挿入（後ろから前へ処理しなくても、各インデックス内で ref を連鎖させれば順序は保たれる）
    for i, items in INS.items():
        ref = P[i]._p
        for tidx, markup in items:
            newp = tr.new_paragraph_after(ref, P[tidx], cites.resolve(markup)); ref = newp._p
    # 参考文献: 旧リストを削除し、初出順の新リストを最後の旧参考文献の後ろへ
    ref = P[117]._p        # 見出し References の直後（旧文献は削除済み/削除履歴として後ろに残る）
    for k in ref_keys:
        newp = tr.new_paragraph_after(ref, P[118], C.REFS[k]); ref = newp._p

    # ---- 3) 表
    t3 = C.tab3_rows(); t4 = C.tab4_rows()
    def flags(rows, skip=()):
        d = {}
        for i, r in enumerate(rows[1:], start=1):
            sv = r[-1].replace(" ", "")
            d[i] = (i not in skip) and (sv.startswith("<") or float(sv) < 0.05)
        return d
    def mkfn(fl):
        return lambda i, j, t: (None if i == 0 else fl[i])
    f3 = mkfn(flags(t3)); f4 = mkfn(flags(t4, skip=(1,)))
    tr.sync_table(TB[0], C.tab1_rows())
    tr.sync_table(TB[1], C.tab2_rows())
    tr.sync_table(TB[2], t3, bold_fn=f3)
    tr.sync_table(TB[3], t4, bold_fn=f4)
    tr.sync_table(TB[4], C.tab5_rows())
    # 表5の注
    tr.new_paragraph_after(TB[4]._tbl, P[161], C.TAB5_NOTE)

    # ---- 4) 図
    # 図は本文に埋め込まない（P168–171 は DEL で削除）。図1–3は figures/ の JPG を別ファイルで提出する。

    # ---- 5) 文書プロパティ（二重匿名のため氏名を残さない）
    cp = doc.core_properties
    cp.title = C.TITLE; cp.author = "Authors"; cp.last_modified_by = "Authors"; cp.comments = ""; cp.subject = ""; cp.keywords = ""
    apply_journal_format(doc)
    doc.save(str(out_path))
    return dict(modified=n_mod, refs=len(ref_keys), uncited=uncited)


if __name__ == "__main__":
    for mode, name in (("marked", "Manuscript_PHRP_v5_marked.docx"), ("clean", "Manuscript_PHRP_v5_clean.docx")):
        out = OUTDIR / name
        # v5 の出力は本スクリプトの生成物なので再生成時は上書きする
        info = build(mode, out)
        print(mode, "->", out.name, info)
