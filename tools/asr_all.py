# -*- coding: utf-8 -*-
r"""미션 음성 전부 받아쓰기(2026-10-11) — WD*/V????.B 안 AIFF 조각(8비트 부호 있음 모노 22,050 Hz), 두 장 고유 조각만.
  ★VAD 끔(건담 교훈: 짧은 외침을 통째로 버림) · 위스퍼 large-v3 · 낱말 시각까지.
  → work/asr/<md5>.json {"md5","sec","segs":[{s,e,t,ns}]} (이미 있으면 건너뜀)
  → work/asr/index.tsv  장·파일·조각·md5·길이·값·초 (조각 → 받아쓰기 연결, 자막 열쇠 만들 때 씀)
  C:\claude\utils\whisper-venv\Scripts\python.exe tools/asr_all.py
"""
import hashlib, json, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, vbank

OUT = os.path.join(ROOT, 'work', 'asr')
PROMPT = None   # ★힌트 문구가 짧은 조각에 그대로 새어 나옴(«オヴァン、レイ。 進めねえ。») → 힌트 없이, 이름은 나중에 일괄 정리


def aiff_pcm(c):
    """AIFF → (float32 −1‥1, 속도)"""
    assert c[:4] == b'FORM' and c[8:12] == b'AIFF'
    p, rate, data, bits, ch = 12, 22050, None, 8, 1
    while p + 8 <= len(c):
        ck, n = c[p:p + 4], struct.unpack_from('>I', c, p + 4)[0]
        if ck == b'COMM':
            ch, _, bits = struct.unpack_from('>hIh', c, p + 8)
            e = struct.unpack_from('>H', c, p + 16)[0] & 0x7FFF; m = struct.unpack_from('>Q', c, p + 18)[0]
            rate = int(round(m * 2.0 ** (e - 16383 - 63)))
        elif ck == b'SSND':
            off = struct.unpack_from('>I', c, p + 8)[0]; data = c[p + 16 + off:p + 8 + n]
        p += 8 + n + (n & 1)
    if bits == 8: a = np.frombuffer(data, np.int8).astype(np.float32) / 128
    else: a = np.frombuffer(data[:len(data) // 2 * 2], '>i2').astype(np.float32) / 32768
    if ch == 2: a = a.reshape(-1, 2).mean(1)
    return a, rate


def to16k(a, rate):
    idx = np.arange(0, len(a), rate / 16000)
    return np.interp(idx, np.arange(len(a)), a).astype(np.float32)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    idx, uniq = [], {}
    for k in (1, 2):
        for n, l, s in disc.files(k):
            if not (n.startswith('/WD') and '/V' in n): continue
            d = disc.read(n, k)
            for ci, (o, ln, v) in enumerate(vbank.clips(d)):
                c = d[o:o + ln]; h = hashlib.md5(c).hexdigest()
                a, rate = aiff_pcm(c)
                idx.append((k, n, ci, h, ln, v, round(len(a) / rate, 2)))
                uniq.setdefault(h, (a, rate))
    with open(os.path.join(OUT, 'index.tsv'), 'w', encoding='utf-8') as f:
        f.write('장\t파일\t조각\tmd5\t길이\t값\t초\n')
        for r in idx: f.write('\t'.join(map(str, r)) + '\n')
    print('조각 %d · 고유 %d' % (len(idx), len(uniq)), flush=True)
    from faster_whisper import WhisperModel
    m = WhisperModel('large-v3', device='cuda', compute_type='float16')
    done = 0
    for h, (a, rate) in uniq.items():
        p = os.path.join(OUT, h + '.json')
        if os.path.exists(p): done += 1; continue
        seg, _ = m.transcribe(to16k(a, rate), language='ja', beam_size=5, word_timestamps=True, initial_prompt=PROMPT,
                              condition_on_previous_text=False, vad_filter=False)
        segs = [{'s': round(x.start, 2), 'e': round(x.end, 2), 't': x.text.strip(), 'ns': round(x.no_speech_prob, 2)} for x in seg]
        json.dump({'md5': h, 'sec': round(len(a) / rate, 2), 'segs': segs}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        done += 1
        if done % 100 == 0: print('%d/%d' % (done, len(uniq)), flush=True)
    print('끝 %d' % done, flush=True)


if __name__ == '__main__':
    main()
