# -*- coding: utf-8 -*-
r"""그림 글(브리핑 S1/F???.Z · 막간 S1/L???.Z) → 번역용 TSV(2026-10-11).
  판독 = work/text/pages_ja.tsv(tools/lineocr.py 다수결) 위에 work/text/pages_fix.tsv(눈 검토로 바로잡은 줄, 285쪽 전수) 덮어씀.
  .Z 파일마다 쪽(항목 순서)을 이어 한 글로: 줄이 오른쪽 끝까지 안 차면 강제 줄바꿈(\n) · 빈 줄 = 문단(\n\n 하나로).
  같은 글(쪽 그림 md5 같은 것 포함)은 한 줄로 묶고 «파일» 열에 전부.
  → work/text/pages_ja_full.tsv(저장소용 한 파일) + my files/QV2_브리핑막간_NN.tsv(20 KB 단위, 하스피 번역용)
  python tools/pages_tsv.py [--nomy]
"""
import collections, csv, hashlib, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, zspr

HEAD = 'id\t종류\t파일\t쪽수\t원문\t번역\n'
LIMIT = 20 * 1024


def texts():
    t = collections.defaultdict(dict)
    for r in list(csv.reader(open(os.path.join(ROOT, 'work', 'text', 'pages_ja.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        t[r[0]][int(r[1])] = r[2]
    for r in list(csv.reader(open(os.path.join(ROOT, 'work', 'text', 'pages_fix.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        t[r[0]][int(r[1])] = r[2]
    return t


FIX = [('工リア', 'エリア'), ('搨', '揚'), ('侍ち', '待ち'), ('决', '決'), ('髙', '高'), ('その問に', 'その間に'), ('の問、', 'の間、'), ('峽', '峡'),
       ('護せよ', '護衛せよ'), ('護衛衛', '護衛')]


def fix(s):
    import re
    for a, b in FIX: s = s.replace(a, b)
    return re.sub(r'(?<=[゠-ヿ])-|-(?=[゠-ヿ])', 'ー', s)


def page_lines(p, rows):
    """→ [(글, 끝까지 찼나)] (빈 줄은 ('', False))"""
    h, w = p.shape; out = []
    for r in range(16):
        y = 4 + 18 * r
        if y >= h: break
        s = fix(rows.get(r, '').strip())
        strip = p[max(0, y - 2):y + 14]
        if not strip.any(): out.append(('', False)); continue
        last = np.where(strip.any(0))[0][-1]
        end = s[-1:] in '。！？」）'
        out.append((s, last >= w - (16 if end else 30)))
    while out and not out[-1][0]: out.pop()
    return out


def join(lines):
    s = ''
    for k, (t, full) in enumerate(lines):
        if not t:
            while s.endswith('\\n'): s = s[:-2]
            if s: s += '\\n\\n'
            continue
        s += t
        if not full and k + 1 < len(lines): s += '\\n'
    while s.endswith('\\n'): s = s[:-2]
    import re
    for a, b in (('時問', '時間'), ('この問に', 'この間に'), ('護せよ', '護衛せよ'), ('護衛衛', '護衛')): s = s.replace(a, b)
    return re.sub(r'(?<!\\n)敗北条件', lambda m: '\\n敗北条件', s)


def collect():
    tx = texts(); names = {}                                           # md5 → 고유 이름(work/zimg 이름)
    import glob
    from PIL import Image
    for f in glob.glob(os.path.join(ROOT, 'work', 'zimg', '*.png')):
        n = os.path.basename(f)[:-4]
        if n[0] not in 'FL': continue
    groups = collections.OrderedDict()                                # 글 → [파일]
    for k in (1, 2):
        for n, l, s in disc.files(k):
            fn = n.split('/')[-1]
            if not (n.startswith('/S1/') and fn[0] in 'FL' and fn.endswith('.Z')): continue
            d = disc.read(n, k); pages = []; seen = set()
            for e in zspr.entries(d):
                if 0x1000 + e['off'] + e['size'] > len(d): continue
                p = zspr.pixels(d, e)
                if len(np.unique(p)) > 3 or p.max() == 0: continue
                if (e['w'], e['h']) not in ((168, 168), (120, 168), (288, 56)): continue
                key = '%s_%02d' % (fn[:-2], e['i'])
                h = hashlib.md5(p.tobytes()).hexdigest()
                if h in seen: continue
                seen.add(h); names.setdefault(h, key)
                rows = tx.get(names[h], {})
                pl = page_lines(p > 0, rows)
                if not any(t for t, _ in pl): continue
                pages.append(pl)
            if not pages: continue
            allines = []
            for pl in pages: allines += pl
            text = join(allines)
            kind = '브리핑' if fn[0] == 'F' else '막간'
            g = groups.setdefault(text, {'kind': kind, 'files': [], 'pages': len(pages)})
            if fn[:-2] not in g['files']: g['files'].append(fn[:-2])
    return groups


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    groups = collect()
    rows = []
    for text, g in sorted(groups.items(), key=lambda kv: kv[1]['files'][0]):
        rows.append('%s\t%s\t%s\t%d\t%s\t' % (g['files'][0], g['kind'], ','.join(g['files']), g['pages'], text))
    open(os.path.join(ROOT, 'work', 'text', 'pages_ja_full.tsv'), 'w', encoding='utf-8', newline='\n').write(HEAD + ''.join(r + '\n' for r in rows))
    print('글 %d개(브리핑 %d · 막간 %d) · 파일 %d' % (len(rows), sum(1 for g in groups.values() if g['kind'] == '브리핑'), sum(1 for g in groups.values() if g['kind'] == '막간'), sum(len(g['files']) for g in groups.values())))
    if '--nomy' in sys.argv: return
    parts, cur = [], HEAD
    for r in rows:
        line = r + '\n'
        if len((cur + line).encode('utf-8')) > LIMIT and cur != HEAD: parts.append(cur); cur = HEAD
        cur += line
    parts.append(cur)
    for i, p in enumerate(parts, 1):
        open(os.path.join(ROOT, 'my files', 'QV2_브리핑막간_%02d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(p)
    print('my files/QV2_브리핑막간_01‥%02d.tsv' % len(parts), [len(p.encode('utf-8')) for p in parts])


if __name__ == '__main__':
    main()
