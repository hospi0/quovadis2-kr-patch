# -*- coding: utf-8 -*-
r"""미션 음성 짝 자막 파일 만들기(2026-10-11) — tools/mhook.py 형식.
  번역: my files/QV2_음성자막_NN.tsv 의 «번역» 열(하스피) + tools/poc.py LINES(PoC 대사, 번역이 없을 때만).
  같은 조각(md5)은 두 장·여러 V 파일 어디서 나오든 같은 자막. 구간(_k)마다 쪽, 3줄 넘으면 글자 수 비율로 시간 나눠 쪽 더.
  쪽 시작 = 구간 시작 초 × 11,025(8비트 모노 — 핸들 진행 바이트와 같은 단위).
  → files(장) = {'KD000': {'V0A01.B': 바이트, …}, …} — 음성 V 파일 하나도 빠짐없이(없으면 LoadFile 이 오류) 항목 0 개 파일이라도 만듦.
  python tools/ksub.py   → 통계 + work/ksub_preview.png(앞 몇 쪽)
"""
import csv, glob, os, re, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, vbank, hook as H, mhook as M, poc

RATE = 11025
WMAX = H.W8 * 8 - 2
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')
KANA = re.compile(r'[぀-ヿ一-鿿]')
_F = ImageFont.truetype(poc.FONT, 12)
_D = ImageDraw.Draw(Image.new('1', (8, 8)))


def tw(s): return _D.textlength(s, font=_F)


def wrap(text):
    """«\n» 강제 줄바꿈 · 띄어쓰기 단위로 폭 158 px 안에. 낱말 하나가 넘치면 글자 단위."""
    out = []
    for para in text.split('\\n'):
        para = PUNCT_SP.sub(r'\1', para.strip()); cur = ''
        for w in para.split(' '):
            t = (cur + ' ' + w) if cur else w
            if tw(t) <= WMAX: cur = t; continue
            if cur: out.append(cur); cur = ''
            while tw(w) > WMAX:
                k = len(w)
                while tw(w[:k]) > WMAX: k -= 1
                out.append(w[:k]); w = w[k:]
            cur = w
        if cur: out.append(cur)
    return out


def translations():
    """work/text/voice_ko.tsv(tools/merge_tr.py — 하스피 번역 병합·용어 통일·부호 뒤 공백) → {id: 번역}"""
    tr = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'voice_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 2 and c[1].strip():
            assert not KANA.search(c[1]), ('가나·한자 남음', c[0], c[1])
            tr[c[0]] = c[1].strip()
    return tr


def index():
    """→ 조각 목록 [(장, 파일, 조각, md5, 길이)] · md5 → 구간 [(id, 시작, 끝)]"""
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'asr', 'index.tsv'), encoding='utf-8')][1:]
    clips = [(int(d), n, int(c), m, int(ln)) for d, n, c, m, ln, v, s in idx]
    first = {}
    for d, n, c, m, ln in clips: first.setdefault(m, (n, c))
    segs = {}; nc = {(n, c): m for d, n, c, m, ln in clips}
    for r in list(csv.reader(open(os.path.join(ROOT, 'work', 'text', 'voice_ja.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        segs.setdefault(nc[(r[2], int(r[3]))], []).append((r[0], float(r[4]), float(r[5])))
    return clips, segs


def pages_for(md5, segs, tr, poc_lines):
    """→ [(쪽 시작 초, 줄들)]"""
    if md5 in poc_lines and not any(i in tr for i, _, _ in segs.get(md5, [])):
        return [(0.0, poc_lines[md5])]
    out = []
    for i, s, e in segs.get(md5, []):
        if i not in tr: continue
        lines = wrap(tr[i])
        n = (len(lines) + 2) // 3; tot = sum(len(x) for x in lines) or 1; acc = 0
        for k in range(n):
            pg = lines[k * 3:(k + 1) * 3]
            out.append((s + (e - s) * acc / tot, pg)); acc += sum(len(x) for x in pg)
    if out: out[0] = (0.0, out[0][1])
    return out


def build(disks=(1, 2), log=print):
    tr = translations(); clips, segs = index()
    poc_lines = {}
    for name, ci, lines, side in poc.LINES:
        for d, n, c, m, ln in clips:
            if n == name and c == ci: poc_lines[m] = lines
    cache = {}
    res = {}; stat = {'files': 0, 'pages': 0, 'max': 0}
    for k in disks:
        vf = sorted(n for n, l, s in disc.files(k) if n.startswith('/WD') and n.rsplit('/', 1)[1].startswith('V'))
        bycl = {}
        for d, n, c, m, ln in clips:
            if d == k: bycl.setdefault(n, []).append((c, m, ln))
        groups = {}                                                     # (폴더, 묶음 이름) → 쪽들
        for n in vf:
            dd, fn = n.strip('/').split('/')
            gk = (dd, 'K' + fn[1:4] + '.B')                             # ★V 파일 16개 묶음(VE000‥VE00F → KE00.B), 음성과 같은 폴더
            pages = groups.setdefault(gk, [])
            for c, m, ln in sorted(bycl.get(n, [])):
                pp = pages_for(m, segs, tr, poc_lines)
                if not pp: continue
                if n not in cache: cache[n] = disc.read(n, k)
                dat = cache[n]; o, ln2, v = vbank.clips(dat)[c]; assert ln2 == ln
                k4 = struct.unpack_from('>I', dat, o + H.keyoff(ln))[0]
                for t, lines in pp:
                    e = (ln, k4, int(t * RATE))
                    if any(q[:3] == e for q in pages): continue        # 같은 조각이 묶음 안 여러 파일에
                    pages.append((ln, k4, int(t * RATE), poc.render(lines)))
        dirs = {}
        for (dd, gn), pages in groups.items():
            b = M.kfile(pages)
            dirs.setdefault(dd, {})[gn] = b
            stat['files'] += 1; stat['pages'] += len(pages); stat['max'] = max(stat['max'], len(b))
        res[k] = dirs
    log('짝 자막 파일 %d개 · 쪽 %d · 가장 큰 파일 %d B(버퍼 %d) · 번역 %d 구간' % (stat['files'], stat['pages'], stat['max'], M.BUFSZ, len(tr)))
    return res


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    r = build()
    for k, dirs in r.items(): print('장', k, {d: len(f) for d, f in dirs.items()})
