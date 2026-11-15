"""Escritor OOXML derivado del registro Kai IMP-008; no contiene datos de G05."""
from __future__ import annotations
import os
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

def valor_xml(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<v>{v}</v>', 'n'
    s = escape(str(v).replace('\x00', ''))
    return f'<is><t xml:space="preserve">{s}</t></is>', 'inlineStr'


def nombre_col(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def hoja_xml(data, widths, freeze=True):
    from xml.sax.saxutils import quoteattr
    cols = ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1))
    rows_xml = []
    for rid, row in enumerate(data, 1):
        cells = []
        for j, val in enumerate(row, 1):
            if val is None:continue
            content, typ = valor_xml(val)
            style = ' s="1"' if rid == 1 else ''
            cells.append(f'<c r="{nombre_col(j)}{rid}" t="{typ}"{style}>{content}</c>')
        rows_xml.append(f'<row r="{rid}">{"".join(cells)}</row>')
    frozen = '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>' if freeze else '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
    ref=f'A1:{nombre_col(max(len(x) for x in data))}{max(1,len(data))}'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="{ref}"/>{frozen}<sheetFormatPr defaultRowHeight="17"/><cols>{cols}</cols><sheetData>{''.join(rows_xml)}</sheetData><autoFilter ref="{ref}"/></worksheet>'''


def escribir_xlsx(path: Path, sheets):
    # Escritura derivada y atómica. No modificar manualmente el XLSX: sus cambios
    # no se fusionan al registro canónico. Celdas textuales nunca son fórmulas.
    estilos='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF143C5B"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs></styleSheet>'''
    types='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'''+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))+'</Types>'
    rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'''+''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_,_) in enumerate(sheets,1))+'</sheets></workbook>'
    wrels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'''+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.kai_xlsx_',suffix='.tmp',dir=path.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml',types)
            z.writestr('_rels/.rels',rels)
            z.writestr('xl/workbook.xml',workbook)
            z.writestr('xl/_rels/workbook.xml.rels',wrels)
            z.writestr('xl/styles.xml',estilos)
            for i,(_,data,widths) in enumerate(sheets,1):
                z.writestr(f'xl/worksheets/sheet{i}.xml',hoja_xml(data,widths))
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None: raise RuntimeError('Exportación Excel corrupta')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
