# -*- coding: utf-8 -*-
r"""동영상 꺼내기(2026-10-11) — 두 장 MV/*.K(세가 FILM, Cinepak 320×152, 22,050 Hz 8비트 스테레오).
  ★높이 홀수(320×149 등) 있음 → mp4 는 짝수로 한 줄 덧댐(pad).
  → work/movie/d1/·d2/<이름>.K (원본 그대로) · work/movie/mp4/<이름>.mp4(볼 용도, 같은 md5 는 한 번) · work/movie/list.tsv
  python tools/movies.py
"""
import hashlib, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
FP = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffprobe.exe'


def dur(p):
    r = subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = os.path.join(ROOT, 'work', 'movie'); mp4 = os.path.join(out, 'mp4'); os.makedirs(mp4, exist_ok=True)
    seen = {}; rows = []
    for k in (1, 2):
        dd = os.path.join(out, 'd%d' % k); os.makedirs(dd, exist_ok=True)
        for n, l, s in disc.files(k):
            if not n.startswith('/MV/'): continue
            d = disc.read(n, k); base = os.path.basename(n)
            p = os.path.join(dd, base); open(p, 'wb').write(d)
            h = hashlib.md5(d).hexdigest()
            if h in seen:
                rows.append((k, base, len(d), h[:8], seen[h][0], seen[h][1])); continue
            m = os.path.join(mp4, ('d%d_' % k) + base.replace('.K', '.mp4'))
            r = subprocess.run([FF, '-v', 'error', '-y', '-i', p, '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', m], capture_output=True, text=True)
            t = dur(m) if r.returncode == 0 else -1
            seen[h] = (os.path.basename(m), t)
            rows.append((k, base, len(d), h[:8], os.path.basename(m), t))
            print('장%d %s %d B %.1f초%s' % (k, base, len(d), t, '' if r.returncode == 0 else ' ★변환 실패 ' + r.stderr[:80]), flush=True)
    with open(os.path.join(out, 'list.tsv'), 'w', encoding='utf-8') as f:
        f.write('장\t파일\t크기\tmd5\tmp4\t초\n')
        for r in rows: f.write('%d\t%s\t%d\t%s\t%s\t%.1f\n' % r)
    uniq = {h: v for h, v in seen.items()}
    print('끝: 파일 %d · 고유 %d · 고유 총 %.1f분' % (len(rows), len(uniq), sum(v[1] for v in uniq.values() if v[1] > 0) / 60))


if __name__ == '__main__':
    main()
