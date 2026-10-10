# -*- coding: utf-8 -*-
r"""동영상 받아쓰기(2026-10-11) — work/movie/list.tsv 의 고유 영상(mp4 이름 기준) 전부, 위스퍼 large-v3, ★VAD 끔·힌트 없음.
  → work/movie/asr/<d1_M201>.tsv (시작·끝·문장·무음확률)  (이미 있으면 건너뜀)
  C:\claude\utils\whisper-venv\Scripts\python.exe tools/asr_movie.py
"""
import csv, os, subprocess, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
OUT = os.path.join(ROOT, 'work', 'movie', 'asr'); os.makedirs(OUT, exist_ok=True)
rows = list(csv.reader(open(os.path.join(ROOT, 'work', 'movie', 'list.tsv'), encoding='utf-8'), delimiter='\t'))[1:]
uniq = []
for disk, name, size, md5, mp4, sec in rows:
    if mp4.startswith('d%s_' % disk) and mp4 not in [u[0] for u in uniq]:
        uniq.append((mp4, os.path.join(ROOT, 'work', 'movie', 'd' + disk, name)))
from faster_whisper import WhisperModel
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
for mp4, src in uniq:
    o = os.path.join(OUT, mp4.replace('.mp4', '.tsv'))
    if os.path.exists(o): continue
    raw = subprocess.run([FF, '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(a) < 1600:
        open(o, 'w', encoding='utf-8').write(''); continue
    seg, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, word_timestamps=True, vad_filter=False)
    with open(o, 'w', encoding='utf-8') as fo:
        for s in seg:
            fo.write('%.2f\t%.2f\t%s\t%.2f\n' % (s.start, s.end, s.text.strip(), s.no_speech_prob))
    print(mp4, open(o, encoding='utf-8').read().count('\n'), '구간', flush=True)
print('끝', flush=True)
