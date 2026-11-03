# -*- coding: utf-8 -*-
"""
docx_track: python-docx で Word の変更履歴（w:ins / w:del）を生成する補助モジュール。
mode='marked' なら変更履歴つき、mode='clean' なら変更を直接反映。
本文の書式は簡易マークアップ <i>..</i>, <b>..</b> で指定する。
"""
import re, copy, datetime, difflib
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.shared import Cm

TOKEN_RE = re.compile(r"\s+|[^\s]+")
MARK_RE = re.compile(r"(<i>|</i>|<b>|</b>)")


def parse_markup(text):
    """'a <i>p</i> b' -> [(token, (bold, italic)), ...]"""
    bold = ital = False
    out = []
    for part in MARK_RE.split(text):
        if part == "<i>": ital = True
        elif part == "</i>": ital = False
        elif part == "<b>": bold = True
        elif part == "</b>": bold = False
        elif part:
            for tok in TOKEN_RE.findall(part):
                out.append((tok, (bold, ital)))
    return out


def tokens_from_paragraph(p):
    out = []
    for r in p.runs:
        fmt = (bool(r.bold), bool(r.italic))
        for tok in TOKEN_RE.findall(r.text):
            out.append((tok, fmt))
    return out


def markup_from_paragraph(p):
    """段落を簡易マークアップ文字列へ（比較・自動引用変換用）。"""
    s = ""
    for r in p.runs:
        t = r.text
        if r.italic: t = f"<i>{t}</i>"
        if r.bold: t = f"<b>{t}</b>"
        s += t
    return s


class Tracker:
    def __init__(self, mode, author="Authors", date=None):
        assert mode in ("marked", "clean")
        self.mode = mode
        self.author = author
        self.date = date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._id = 5000

    @property
    def tracked(self): return self.mode == "marked"

    def _mk(self, tag):
        self._id += 1
        el = OxmlElement(tag)
        el.set(qn("w:id"), str(self._id)); el.set(qn("w:author"), self.author); el.set(qn("w:date"), self.date)
        return el

    # ------------------------------------------------------------ run builders
    @staticmethod
    def _base_rpr(p):
        for r in p._p.iter(qn("w:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is not None:
                b = copy.deepcopy(rpr)
                for t in ("w:b", "w:bCs", "w:i", "w:iCs"):
                    for e in b.findall(qn(t)): b.remove(e)
                return b
            break
        return None

    @staticmethod
    def _run(text, fmt, base_rpr, deleted=False):
        r = OxmlElement("w:r")
        rpr = copy.deepcopy(base_rpr) if base_rpr is not None else OxmlElement("w:rPr")
        if fmt[0]: rpr.append(OxmlElement("w:b"))
        if fmt[1]: rpr.append(OxmlElement("w:i"))
        if len(rpr): r.append(rpr)
        t = OxmlElement("w:delText" if deleted else "w:t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text
        r.append(t)
        return r

    @staticmethod
    def _merge(tokens):
        out = []
        for tok, fmt in tokens:
            if out and out[-1][1] == fmt: out[-1] = (out[-1][0] + tok, fmt)
            else: out.append((tok, fmt))
        return out

    def _clear_content(self, p):
        for ch in list(p._p):
            if ch.tag != qn("w:pPr"): p._p.remove(ch)

    # ------------------------------------------------------------ paragraph ops
    def rewrite(self, p, new_markup):
        """段落の本文を new_markup に置き換える（markedでは単語単位の差分を変更履歴化）。"""
        old = tokens_from_paragraph(p)
        new = parse_markup(new_markup)
        if [t for t in old] == [t for t in new]: return False
        base = self._base_rpr(p)
        self._clear_content(p)
        if not self.tracked:
            for txt, fmt in self._merge(new): p._p.append(self._run(txt, fmt, base))
            return True
        sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                for txt, fmt in self._merge(old[i1:i2]): p._p.append(self._run(txt, fmt, base))
            else:
                if i2 > i1:
                    d = self._mk("w:del")
                    for txt, fmt in self._merge(old[i1:i2]): d.append(self._run(txt, fmt, base, deleted=True))
                    p._p.append(d)
                if j2 > j1:
                    ins = self._mk("w:ins")
                    for txt, fmt in self._merge(new[j1:j2]): ins.append(self._run(txt, fmt, base))
                    ins_parent = p._p; ins_parent.append(ins)
        return True

    def delete_paragraph(self, p):
        if not self.tracked:
            p._p.getparent().remove(p._p); return
        for r in list(p._p.findall(qn("w:r"))):
            for t in r.findall(qn("w:t")):
                t.tag = qn("w:delText"); t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            d = self._mk("w:del"); r.addprevious(d); d.append(r)
        ppr = p._p.get_or_add_pPr()
        rpr = ppr.find(qn("w:rPr"))
        if rpr is None: rpr = OxmlElement("w:rPr"); ppr.append(rpr)
        rpr.append(self._mk("w:del"))

    def new_paragraph_after(self, ref_el, template_p, markup):
        """ref_el（lxml要素）の直後に、template_p の書式で新段落を挿入して Paragraph を返す。"""
        el = OxmlElement("w:p")
        tppr = template_p._p.find(qn("w:pPr"))
        if tppr is not None:
            ppr = copy.deepcopy(tppr)
            for e in ppr.findall(qn("w:rPr")): ppr.remove(e)
            for e in ppr.findall(qn("w:sectPr")): ppr.remove(e)
            el.append(ppr)
        ref_el.addnext(el)
        p = Paragraph(el, template_p._parent)
        base = self._base_rpr(template_p)
        toks = self._merge(parse_markup(markup))
        if self.tracked:
            ppr = el.get_or_add_pPr(); rpr = OxmlElement("w:rPr"); rpr.append(self._mk("w:ins")); ppr.append(rpr)
            ins = self._mk("w:ins")
            for txt, fmt in toks: ins.append(self._run(txt, fmt, base))
            el.append(ins)
        else:
            for txt, fmt in toks: el.append(self._run(txt, fmt, base))
        return p

    # ------------------------------------------------------------ table ops
    def set_cell(self, cell, text, bold=None):
        p = cell.paragraphs[0]
        if bold is None:
            first = p.runs[0] if p.runs else None
            bold = bool(first.bold) if first is not None else False
        mk = f"<b>{text}</b>" if bold and text else text
        return self.rewrite(p, mk)

    def _fill_empty_cell(self, cell, text, bold, base):
        p = cell.paragraphs[0]
        for extra in cell.paragraphs[1:]: extra._p.getparent().remove(extra._p)
        self._clear_content(p)
        toks = self._merge(parse_markup(f"<b>{text}</b>" if bold and text else text))
        if self.tracked:
            ins = self._mk("w:ins")
            for txt, fmt in toks: ins.append(self._run(txt, fmt, base))
            p._p.append(ins)
        else:
            for txt, fmt in toks: p._p.append(self._run(txt, fmt, base))

    def add_row(self, table, texts, bolds=None, template_row=None):
        tmpl = (template_row if template_row is not None else table.rows[-1])._tr
        new = copy.deepcopy(tmpl)
        table.rows[-1]._tr.addnext(new)
        from docx.table import _Row
        row = _Row(new, table)
        if self.tracked:
            trpr = new.get_or_add_trPr(); trpr.append(self._mk("w:ins"))
        for i, cell in enumerate(row.cells):
            base = self._base_rpr(cell.paragraphs[0])
            self._fill_empty_cell(cell, texts[i] if i < len(texts) else "", bool(bolds[i]) if bolds else False, base)
        return row

    def delete_row(self, row):
        if not self.tracked:
            row._tr.getparent().remove(row._tr); return
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in list(p._p.findall(qn("w:r"))):
                    for t in r.findall(qn("w:t")):
                        t.tag = qn("w:delText"); t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                    d = self._mk("w:del"); r.addprevious(d); d.append(r)
        trpr = row._tr.get_or_add_trPr(); trpr.append(self._mk("w:del"))

    def sync_table(self, table, rows, bold_fn=None):
        """rows: 2次元の文字列。既存行は差分編集、足りなければ挿入行、余れば削除行。"""
        old_rows = list(table.rows)
        for i, texts in enumerate(rows):
            if i < len(old_rows):
                for j, cell in enumerate(old_rows[i].cells):
                    if j < len(texts):
                        b = bold_fn(i, j, texts[j]) if bold_fn else None
                        self.set_cell(cell, texts[j], bold=b)
            else:
                bolds = [bold_fn(i, j, t) if bold_fn else False for j, t in enumerate(texts)]
                self.add_row(table, texts, bolds, template_row=old_rows[min(len(old_rows) - 1, 1)])
        for r in old_rows[len(rows):]: self.delete_row(r)

    # ------------------------------------------------------------ image
    def replace_image(self, p, img_path, width_cm):
        if self.tracked:
            for r in list(p._p.findall(qn("w:r"))):
                d = self._mk("w:del"); r.addprevious(d); d.append(r)
        else:
            for r in list(p._p.findall(qn("w:r"))): p._p.remove(r)
        run = p.add_run(); run.add_picture(str(img_path), width=Cm(width_cm))
        if self.tracked:
            ins = self._mk("w:ins"); run._r.addprevious(ins); ins.append(run._r)

    def add_image_paragraph_after(self, ref_el, template_p, img_path, width_cm):
        p = self.new_paragraph_after(ref_el, template_p, "")
        # 空のinsを残さないよう、中身を消してから画像を追加
        for ch in list(p._p):
            if ch.tag != qn("w:pPr"): p._p.remove(ch)
        run = p.add_run(); run.add_picture(str(img_path), width=Cm(width_cm))
        if self.tracked:
            ins = self._mk("w:ins"); run._r.addprevious(ins); ins.append(run._r)
        return p


# ---------------------------------------------------------------- 引用番号
class Cites:
    PAT = re.compile(r"\{ref:([a-z0-9_,]+)\}")

    def __init__(self): self.order = []

    def scan(self, text):
        for m in self.PAT.finditer(text):
            for k in m.group(1).split(","):
                if k not in self.order: self.order.append(k)

    def num(self, k): return self.order.index(k) + 1

    def resolve(self, text):
        def fmt(m):
            nums = sorted(self.num(k) for k in m.group(1).split(","))
            parts, i = [], 0
            while i < len(nums):
                j = i
                while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
                if j - i >= 2: parts.append(f"{nums[i]}–{nums[j]}")
                else: parts.extend(str(n) for n in nums[i:j + 1])
                i = j + 1
            return "[" + ",".join(parts) + "]"
        return self.PAT.sub(fmt, text)
