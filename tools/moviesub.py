# -*- coding: utf-8 -*-
r"""동영상 자막 굽기(2026-10-11, 건담 외전 moviesub 에서 — 쿠오바디스 2: FILM 1.09 · cinepak 띠 1개 · 30fps · 영상 크기 제각각).
  자막 표: work/movie/movie_subs.tsv — 영상(d1_M201) · 시작 · 끝(초) · 원문 · 번역(«\n» 강제 줄바꿈) · 비고
  시간: 읽을 시간(글자×0.15초 + 0.8초, 최소 1.2초)보다 짧으면 다음 자막 앞까지 늘림.
  글씨: 갈무리11 좁은꼴(한글 8px·12px 비트맵) 흰색 + 검은 1px 테두리, 화면 아래 가운데(줄 간격 13px), 최대 2줄, 부호 뒤 공백 삭제.
  굽기: tools/movenc.py(자막 든 키 구간만) → work/kr/d<장>/<파일>.K (원본 크기, 0 채움 — 디스크 제자리). 두 장 같은 영상(md5)은 한 번 굽고 양쪽에.
  미리보기: work/movie/sub/<영상>_kr.mp4
  python tools/moviesub.py [영상 …] [--nopreview]
"""
import csv, glob, os, re, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import filmcpk, movenc

FFBIN = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin'
FONT = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Condensed.ttf'
PX, LH = 12, 13
TSV = os.path.join(ROOT, 'work', 'movie', 'movie_subs.tsv')
WORK = os.path.join(ROOT, 'work', 'movie')
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')
KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def listing():
    rows = list(csv.reader(open(os.path.join(WORK, 'list.tsv'), encoding='utf-8'), delimiter='\t'))[1:]
    src, copies = {}, {}
    for disk, name, size, md5, mp4, sec in rows:
        key = mp4.replace('.mp4', '')
        if mp4.startswith('d%s_' % disk) and key not in src: src[key] = os.path.join(WORK, 'd' + disk, name)
        copies.setdefault(key, []).append((int(disk), name))
    return src, copies


def rows():
    out = {}
    for ln in open(TSV, encoding='utf-8').read().splitlines():
        if ln.startswith('#') or ln.startswith('movie\t') or not ln.strip(): continue
        c = ln.split('\t'); t = c[4]
        if not t.strip(): continue
        assert not KANA.search(t), ('가나·한자 남음', c)
        lines = [PUNCT_SP.sub(r'\1', p.strip()) for p in t.split('\\n')]
        out.setdefault(c[0], []).append((float(c[1]), float(c[2]), lines))
    for k in out: out[k].sort()
    return out


def need(lines): return max(sum(len(p) for p in lines) * 0.15 + 0.8, 1.2)


def events(rs, dur):
    ev = []
    for k, (s, e, lines) in enumerate(rs):
        nxt = rs[k + 1][0] if k + 1 < len(rs) else dur
        ev.append((s, min(max(e, s + need(lines)), nxt - 0.07, dur - 0.05), lines))
    return ev


def plate(lines, F, W, H):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.fontmode = '1'
    for ln in lines: assert d.textlength(ln, font=F) <= W - 6, ('줄 넘침', W, ln)
    assert len(lines) <= 2, ('세 줄 이상', lines)
    y = H - 6 - (len(lines) - 1) * LH
    for ln in lines:
        x = (W - int(d.textlength(ln, font=F))) // 2
        d.text((x, y), ln, font=F, anchor='ls', fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0)); y += LH
    px = im.load()
    for yy in range(H):
        for xx in range(W):
            r, g, b, a = px[xx, yy]; px[xx, yy] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return im


def frames(key, src):
    fr = os.path.join(WORK, 'frames', key)
    if not glob.glob(os.path.join(fr, 'f*.png')):
        os.makedirs(fr, exist_ok=True)
        subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', src, '-fps_mode', 'passthrough', os.path.join(fr, 'f%05d.png')], check=True)
    return fr


def times(src):
    film = filmcpk.read(open(src, 'rb').read())
    v = [e for e in film['stab'] if e[2] != 0xFFFFFFFF]
    return [((e[2] & 0x7FFFFFFF) / film['base'], ((e[2] & 0x7FFFFFFF) + e[3]) / film['base']) for e in v]


def burn(key, src, ev, copies, log):
    fr = frames(key, src); T = times(src)
    nf = len(glob.glob(os.path.join(fr, 'f*.png'))); assert nf == len(T), ('프레임 수 불일치', nf, len(T))
    W, H = Image.open(os.path.join(fr, 'f00001.png')).size
    kr = os.path.join(fr, 'kr')
    if os.path.isdir(kr): shutil.rmtree(kr)
    os.makedirs(kr)
    F = ImageFont.truetype(FONT, PX); done = 0
    for a, b, lines in ev:
        pl = plate(lines, F, W, H)
        for f, (t0, t1) in enumerate(T):
            if t0 < b and t1 > a and (min(t1, b) - max(t0, a)) >= 0.5 * (t1 - t0):
                p = os.path.join(kr, 'f%05d.png' % (f + 1))
                im = Image.open(p if os.path.exists(p) else os.path.join(fr, 'f%05d.png' % (f + 1))).convert('RGBA')
                im.alpha_composite(pl); im.convert('RGB').save(p); done += 1
    size = os.path.getsize(src)
    first = os.path.join(ROOT, 'work', 'kr', 'd%d' % copies[0][0], copies[0][1])
    movenc.reencode(src, fr, kr, first, size, log=log)
    for disk, name in copies[1:]:
        dst = os.path.join(ROOT, 'work', 'kr', 'd%d' % disk, name); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(first, dst)
    log('%s %dx%d 프레임 %d/%d 에 자막 → %s' % (key, W, H, done, nf, ', '.join('d%d/%s' % c for c in copies)))
    return first


def preview(key, path, W, H):
    os.makedirs(os.path.join(WORK, 'sub'), exist_ok=True)
    subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', path,
                    '-vf', 'scale=%d:%d:flags=neighbor,pad=ceil(iw/2)*2:ceil(ih/2)*2' % (W * 3, H * 3), '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', os.path.join(WORK, 'sub', key + '_kr.mp4')], check=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src, copies = listing(); allr = rows()
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    names = args or sorted(allr)
    log = lambda *a: print(*a, flush=True)
    F = ImageFont.truetype(FONT, PX)
    for k in sorted(allr):                                             # 먼저 전부 폭 검사
        fr = frames(k, src[k]); W, H = Image.open(os.path.join(fr, 'f00001.png')).size
        for _, _, lines in allr[k]: plate(lines, F, W, H)
    for k in names:
        T = times(src[k]); ev = events(allr[k], T[-1][1])
        log('== %s 자막 %d개' % (k, len(ev)))
        first = burn(k, src[k], ev, copies[k], log)
        if '--nopreview' not in sys.argv:
            fr = os.path.join(WORK, 'frames', k); W, H = Image.open(os.path.join(fr, 'f00001.png')).size
            preview(k, first, W, H)
    log('끝')


if __name__ == '__main__':
    main()
