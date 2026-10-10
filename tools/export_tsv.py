# -*- coding: utf-8 -*-
r"""받아쓰기(work/asr) → 번역용 TSV(2026-10-11).
  열: id · 장 · 파일 · 조각 · 시작 · 끝 · 원문 · 번역(빈칸)
  id = <폴더>/<V파일>#<조각>_<구간> (예 WDE00/VE012#0_1). 두 장 같은 조각(md5)은 처음 것 하나만.
  빼는 것: 위스퍼 지어낸 문구(무음 확률 0.6↑ 이고 «ご視聴»·«チャンネル登録» 류) · 빈 받아쓰기.
  → work/text/voice_ja.tsv(저장소용 한 파일) + my files/QV2_음성자막_NN.tsv(20 KB 단위, 하스피 «20kb단위로 뽑아서 마이파일스에»)
  python tools/export_tsv.py
"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
HALLU = re.compile(r'ご視聴|チャンネル登録|ありがとうございました$|字幕')
HEAD = 'id\t장\t파일\t조각\t시작\t끝\t원문\t번역\n'
LIMIT = 20 * 1024


def rows():
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'asr', 'index.tsv'), encoding='utf-8')][1:]
    seen = set(); out = []; dropped = empty = 0
    for disk, name, ci, md5, ln, v, sec in idx:
        if md5 in seen: continue
        seen.add(md5)
        segs = json.load(open(os.path.join(ROOT, 'work', 'asr', md5 + '.json'), encoding='utf-8'))['segs']
        keep = []
        for s in segs:
            t = s['t'].replace('\t', ' ').strip()
            if not t: continue
            if s.get('ns', 0) >= 0.6 and HALLU.search(t): dropped += 1; continue
            keep.append((s['s'], s['e'], t))
        if not keep: empty += 1; continue
        base = '%s#%s' % (name.strip('/').replace('.B', ''), ci)
        for k, (a, b, t) in enumerate(keep):
            out.append('%s_%d\t%s\t%s\t%s\t%.2f\t%.2f\t%s\t' % (base, k, disk, name, ci, a, b, t))
    return out, dropped, empty


def main():
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    rs, dropped, empty = rows()
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'text', 'voice_ja.tsv'), 'w', encoding='utf-8', newline='\n').write(HEAD + ''.join(r + '\n' for r in rs))
    parts, cur = [], HEAD
    for r in rs:
        line = r + '\n'
        if len((cur + line).encode('utf-8')) > LIMIT and cur != HEAD:
            parts.append(cur); cur = HEAD
        cur += line
    parts.append(cur)
    out = os.path.join(ROOT, 'my files')
    for i, p in enumerate(parts, 1):
        open(os.path.join(out, 'QV2_음성자막_%02d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(p)
    print('줄 %d · 지어낸 문구 뺌 %d · 빈 조각 %d · 파일 %d개(20 KB 이하) → my files/QV2_음성자막_NN.tsv' % (len(rs), dropped, empty, len(parts)))
    print('크기', [len(p.encode('utf-8')) for p in parts][:5], '…', len(parts[-1].encode('utf-8')))


if __name__ == '__main__':
    main()
