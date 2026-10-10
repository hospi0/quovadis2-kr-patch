# -*- coding: utf-8 -*-
r"""빌드(2026-10-11) — 두 장 트랙 1 이미지(work/out/, 크기 그대로 제자리).
  장 1: 0.BIN(미션 자막 훅 — tools/poc.py 의 PoC 대사표) + MV/*.K(동영상 자막, tools/moviesub.py 가 구운 work/kr/d1/)
  장 2: MV/*.K(work/kr/d2/)
  python tools/build.py [--movies]   (--movies = 동영상 자막 먼저 굽기)
"""
import glob, hashlib, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, iso

OUT = os.path.join(ROOT, 'work', 'out', 'QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc %d) (Track 1).bin')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    log = lambda *a: print(*a, flush=True)
    if '--movies' in sys.argv:
        subprocess.run([sys.executable, os.path.join(HERE, 'moviesub.py')], check=True)
    import poc, hook as H
    ents = []
    for name, ci, lines, side in poc.LINES:
        px = poc.render(lines); ln, k4 = poc.key(name, ci); ents.append((ln, k4, px))
    parts, lab, _ = H.blob(ents)
    files1 = {'/0.BIN': H.patch_0bin(disc.read('/0.BIN', 1), parts, lab)}
    for k in (1, 2):
        files = files1 if k == 1 else {}
        for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'kr', 'd%d' % k, '*.K'))):
            files['/MV/' + os.path.basename(p)] = open(p, 'rb').read()
        iso.patch(OUT % k, k, files, log=log)
        log('장 %d: 바뀐 파일 %s · md5 %s' % (k, ', '.join(sorted(files)), hashlib.md5(open(OUT % k, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
