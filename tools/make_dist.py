# -*- coding: utf-8 -*-
r"""쿼바디스 2 배포 묶음 — dist/QuoVadis2_KR_<VER>/ : 장마다 트랙 1 xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat(CP949)
  바뀌는 트랙: 1장·2장 트랙 1(데이터, 짝 자막 파일 덧붙여 길어짐) — 트랙 2(오디오)·cue 는 원본 그대로.
  검증: 원본 트랙 → xdelta 적용 → md5 = 빌드 결과 md5.
  python tools/make_dist.py [--readme]   (먼저 QV_OUT=work/out_now python tools/build.py · --readme = xdelta 그대로 두고 readme·bat·zip 만 다시)
"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.8'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROMS = r'C:\claude\roms\ss'
OUT = os.environ.get('QV_OUT') or os.path.join(ROOT, 'work', 'out_now')
NAME = 'QuoVadis2_KR_' + VER
TITLE = '쿼바디스2 - 혹성강습 오반 레이 (QuoVadis 2 - Wakusei Kyoushuu Ovan Rei, 세가 새턴 일본판) 한글 패치 ' + VER   # 공식 한글 제목(하스피 2026-10-11)
DISCS = [(1, 2, (1,)), (2, 2, (1,))]             # (장, 트랙 수, 패치할 트랙)


def rom(n):
    return 'QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc %d)' % n


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


HEAD = """{tracks}개의 트랙으로 이루어진 {rom} 의
트랙 {t}번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.
"""

BODY = """

[ 적용 방법 ]

  1) 원본 트랙 파일을 이 폴더에 복사
{bins}
     (두 장 중 한 장만 있어도 그 장만 패치합니다)
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 1 이름으로 바꿔 넣고, 트랙 2 와 cue 는 그대로 쓰세요
     (패치한 트랙 1 은 원본보다 조금 커집니다. 정상입니다)

  직접 적용:
    xdelta.exe -d -s "원본 트랙" "패치 파일" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 미션 중 음성 대사 자막(고정 대사·랜덤 공격/피격 대사, 말하는 사람 쪽 화면 위/아래)
  - 이야기 동영상 12개 자막
  - 브리핑·막간 글, 메뉴·시스템·전투 HUD 그림 글자, 배경 그림 글자(작전 목적·경고·결과 등), 옵션
  - 병사 소개 51명
  - 병사·적 이름, 무기·장비 이름
  - 타이틀 화면


[ 알려진 점 ]

  - 아직 끝까지 실기로 통독하지 못했습니다. 이상한 곳이 있으면 알려 주세요.
  - 미션 중 작은 통신 동영상(96×72)에는 자막이 없습니다.
  - 일부 메뉴 배경에 흐리게 비치는 일본어(다른 메뉴 잔상)는 원래 그림에 구워져 있어 그대로 두었습니다.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
set DONE=0
{blocks}
if "%DONE%"=="0" (
  echo   [오류] 원본 트랙 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
echo   완료
pause
"""

BLOCK = r"""if exist "%~dp0{bin}" (
  "%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
  if errorlevel 1 (
    echo   [오류] {n}장 트랙 {t} 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
    pause & exit /b 1
  )
  echo   {n}장 트랙 {t}: "{kbin}"
  set DONE=1
)
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    only = '--readme' in sys.argv
    if not only:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    heads, blocks, bins = [], [], []
    for n, tracks, pts in DISCS:
        for t in pts:
            b = '%s (Track %d).bin' % (rom(n), t)
            src = os.path.join(ROMS, rom(n), b); out = os.path.join(OUT, b)
            patch = '%s_Disc%d_Track%d.xdelta' % (NAME, n, t); pp = os.path.join(d, patch)
            if not only: subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, out, pp], check=True)
            chk = os.path.join(d, '_check.bin')
            subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
            o, want, got = md5(src), md5(out), md5(chk)
            os.remove(chk)
            assert got == want, ('패치 적용 결과가 빌드와 다름', n, t, got, want)
            heads.append(HEAD.format(tracks=tracks, rom=rom(n), t=t, o=o, d=want))
            kbin = '%s (Track %d) [KR].bin' % (rom(n), t)
            blocks.append(BLOCK.format(bin=b, patch=patch, kbin=kbin, n=n, t=t))
            bins.append('       "%s"' % b)
            print('%d장 트랙 %d 원본md5 %s → 패치md5 %s · %s %d B' % (n, t, o, want, patch, os.path.getsize(pp)))
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    readme = TITLE + '\n' + '=' * 60 + '\n\n' + '\n\n'.join(heads) + BODY.format(bins='\n'.join(bins))
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(blocks=''.join(blocks)).replace('\n', '\r\n').encode('cp949'))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(d)):
            zf.write(os.path.join(d, f), NAME + '/' + f)
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-56s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('  zip %s %d B · md5 %s' % (os.path.basename(z), os.path.getsize(z), md5(z)))


if __name__ == '__main__':
    main()
