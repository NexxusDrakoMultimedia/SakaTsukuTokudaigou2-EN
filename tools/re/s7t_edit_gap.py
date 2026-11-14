"""s7t: one-shot patch of tools/textfmt_gap.py: optional 4th GAPS element `slot` (NUL + zero padding the slot owns)."""
import os
import re
p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/tools/textfmt_gap.py'
s = open(p, encoding='utf8').read()
s = s.replace("""    'FLOW_PRG/HOMETOWN.BIN': [(0x47060, 10, False)],    # %s%sです。
}""", """    'FLOW_PRG/HOMETOWN.BIN': [(0x47060, 10, False)],    # %s%sです。
    # match preview stadium line `%sｽﾀｼﾞｱﾑ` (s7t): 8 bytes + NUL + 3 zero pad bytes = a 12-byte slot -> '%s Stadium' (11 bytes) fits
    'FLOW_PRG/SCHE0.BIN': [(0x39574, 8, False, 12)],
    'FLOW_PRG/SCHE1.BIN': [(0x39574, 8, False, 12)],
}""")
s = s.replace("""# source -> [(offset, span, cont)]   span = bytes of the text WITHOUT the NUL (cont: up to the start of the next record)""",
"""# source -> [(offset, span, cont[, slot])]   span = bytes of the text WITHOUT the NUL (cont: up to the start of the next record);
# slot (cont False only, optional) = span + NUL + the all-zero padding behind it that the record may use (max_bytes = slot)""")
s = s.replace("""    for off, span, cont in GAPS.get(source, ()):
        raw = bytes(data[off:off + span])
        if len(raw) != span or b'\0' in raw or (not cont and data[off + span:off + span + 1] != b'\0'):
            continue
        mb = span if cont else span + 1""", """    for ent in GAPS.get(source, ()):
        off, span, cont = ent[:3]
        slot = ent[3] if len(ent) > 3 else span + 1
        raw = bytes(data[off:off + span])
        if len(raw) != span or b'\0' in raw or (not cont and data[off + span:off + span + 1] != b'\0'):
            continue
        if not cont and any(data[off + span:off + slot]):
            continue
        mb = span if cont else slot""")
s = s.replace("""    b = C.encode_text(en)
    if not cont:
        if len(b) > span:
            raise ValueError('%r is %d bytes, the slot holds %d' % (en, len(b), span))
        return b + b'\0' * (span + 1 - len(b))""", """    b = C.encode_text(en)
    if not cont:
        if len(b) > (limit if limit is not None else span):
            raise ValueError('%r is %d bytes, the slot holds %d' % (en, len(b), limit if limit is not None else span))
        return b + b'\0' * (max(span, len(b)) + 1 - len(b))""")
s = s.replace("def render(ja, en, span, cont):", "def render(ja, en, span, cont, limit=None):")
s = s.replace("""        span = e['max_bytes'] if cont else e['max_bytes'] - 1
        jb = C.encode_text(e['ja'])
        if len(jb) != span or""", """        jb = C.encode_text(e['ja'])
        span = e['max_bytes'] if cont else len(jb)
        limit = None if cont else e['max_bytes'] - 1
        if len(jb) != span or""")
s = s.replace("""        buf[off:off + len(render(e['ja'], en, span, cont))] = render(e['ja'], en, span, cont)""", """        out = render(e['ja'], en, span, cont, limit)
        buf[off:off + len(out)] = out""")
open(p, 'w', encoding='utf8').write(s)
