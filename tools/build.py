# -*- coding: utf-8 -*-
r"""빌드(2026-10-11) — 두 장 트랙 1 이미지(work/out/).
  두 장 모두: 0.BIN(미션 자막 훅 본판 tools/mhook.py — 두 장 0.BIN 같음) + MV/*.K(동영상 자막, tools/moviesub.py 가 구운 work/kr/d<장>/)
            + 새 폴더 KD???/V????.B(짝 자막 파일, tools/ksub.py — 트랙 1 끝 포스트갭 앞에 덧붙임, tools/isoadd.py)
  python tools/build.py [--movies]   (--movies = 동영상 자막 먼저 굽기)
  ★검산: tools/mtest.py(흉내기) 를 먼저 통과해야 씀.
"""
import glob, hashlib, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

OUT = os.path.join(os.environ.get('QV_OUT') or os.path.join(ROOT, 'work', 'out'), 'QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc %d) (Track 1).bin')
KR = os.environ.get('QV_KR') or os.path.join(ROOT, 'work', 'kr')          # 동영상 굽는 중에 따로 빌드할 땐 사본 폴더(QV_KR)·다른 출력(QV_OUT)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    log = lambda *a: print(*a, flush=True)
    if '--movies' in sys.argv:
        subprocess.run([sys.executable, os.path.join(HERE, 'moviesub.py'), '--nopreview'], check=True)
    import mhook as M, ksub, isoadd, mtest, pagegfx, uigfx, hudgfx, bggfx, optgfx, biogfx
    ks = ksub.build(log=log)
    assert mtest.main(ks[1]), '흉내기 실패'
    import khook, ktest, iffkr, titlegfx
    assert ktest.main(), '가타카나 훅 흉내기 실패'
    dk, kimg, _ = khook.build(disc.read('/0.BIN', 1))                 # 이름·무기 한글(8×8 캐시 훅) — 문자열·입구 덮개
    parts, lab, _ = M.blob(extra=(khook.KBASE, kimg))                  # 훅 실행 이미지는 자막 RUN 뒤 0x060FD000 에 같이 풂
    bin0 = M.patch_0bin(dk, parts, lab)
    for k in (1, 2):
        files = {'/0.BIN': bin0}
        files['/S1/IFF.Z'] = iffkr.build(disc.read('/S1/IFF.Z', k), khook.table()[1])   # 메뉴 16×16 글꼴 가나 칸 → 한글(F3 이름)
        files.update(pagegfx.build(k, log=log))                         # 브리핑·막간 글 쪽 그림(한글)
        files.update(uigfx.build(k, log=log))                           # 메뉴·시스템 그림 글자(한글)
        files.update(optgfx.build(k, log=log, base=files))              # 옵션 하위판·무비 재생판·무비 제목(uigfx OPT 결과 위에)
        files.update(hudgfx.build(k, log=log))
        files.update(hudgfx.build_nl2(k, log=log))                      # 로딩 계기판 «起動»
        files.update(hudgfx.build_syu(k, log=log))                      # 작전 종료 «作戦終了»
        files.update(biogfx.build(k, log=log))                          # 병사 소개 판(S??.R)                          # 전투 HUD 명령·상태 글자(한글)
        files.update(bggfx.build(k, log=log))                           # VDP2 배경 비트맵 글자(작전 목적·경고·디브리핑 등)
        files.update(titlegfx.build(k, log=log))                         # 타이틀 «혹성강습 / 오반·레이 / 쿼바디스 2»(BG/B0001.BIN)
        files.update(bggfx.build_spr(k, base=files, log=log))           # .Z 안 RGB 그림(배치 화면 머리글) — uigfx 결과 위에
        for p in sorted(glob.glob(os.path.join(KR, 'd%d' % k, '*.K'))):
            files['/MV/' + os.path.basename(p)] = open(p, 'rb').read()
        isoadd.build(OUT % k, k, files, None, log=log, into=ks[k])      # 짝 자막 묶음 = 음성과 같은 WD 폴더에
        log('장 %d: 바뀐 파일 %d · 짝 자막 %d · md5 %s' % (k, len(files), sum(len(v) for v in ks[k].values()), hashlib.md5(open(OUT % k, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
