# -*- coding: utf-8 -*-
r"""0.BIN 반각 가타카나(이름·무기) → 한글 번역표 만들기(2026-10-11) — work/text/kana_ko.tsv
  이름 = 포인터 표 0x060815CC 0‥99번(번호 = 병사 소개 S 번호 → bio_ko 표기, 없으면 음성 자막 번역 표기·음역)
  무기 = 33 B 기록 0x060819D0‥ 의 이름 칸(+5, 24 B) — 가타카나 낱말만 사전으로 바꾸고 형번·HE/AP 등 영문은 그대로
"""
import struct, re, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
L = 0x06004000; NAMEPTR = 0x060815CC; WREC = 0x060819D0; WEND = 0x06082850; WSZ = 33
NAME_EXTRA = {'ﾀﾞﾐｰ': '더미', 'ｹﾂﾊﾞﾝ': '케츠반', 'ﾘｼﾞｱ': '리디아', 'ﾃﾞｨｵﾝ': '디온', 'ﾎﾞﾊﾞ': '보바', 'ﾆｯﾀ': '닛타',
              'ｱｸﾞﾘ': '아그리', 'ｼﾆﾙ': '시닐', 'ﾃﾞﾄｽ': '데토스', 'ｹﾞﾘﾗ': '게릴라', 'ﾊﾞﾊﾞﾉｱ': '바바노아', 'ｾﾗﾑ': '세람',
              'ｼｷｶﾝ': '지휘관', 'ｸﾛｲｷﾊﾞ': '검은송곳니', 'ﾏﾁｪｯﾃｨ': '마체티', 'ｻﾓｴﾄﾞ': '사모예드', 'ﾌｨﾃﾞﾘｽ': '피델리스',
              'ﾓﾅｰｸ': '모나크', 'ｼﾊﾞ': '시바', 'ﾊｲﾌﾞ': '하이브', 'ｼｬﾄﾞｳ': '섀도', 'ﾋｾﾝﾄｳ': '비전투', 'ﾖﾋﾞ': '예비'}
WORDS = {'ｿｳﾋﾞ ﾅｼ': '장비 없음', 'ｿｳﾋﾞ ﾌｶ': '장비 불가',
         'ｺﾝﾊﾞｯﾄﾅｲﾌ': '컴뱃나이프', 'ﾅｯｸﾙｶﾞｰﾄﾞ': '너클가드', 'ﾌﾚｲﾑｽﾛｳｱｰ': '플레임스로어', 'ﾍﾙﾌﾚｲﾑ': '헬플레임',
         'ﾊﾟｲﾙﾊﾞﾝｶｰ': '파일벙커', 'ﾊﾟｲﾙﾌﾞﾚｲｶｰ': '파일브레이커', 'ｱｻﾙﾄ': '어설트', 'ｻﾌﾞﾏｼﾝｶﾞﾝ': '서브머신건',
         'ｼｮｯﾄｶﾞﾝ': '샷건', 'ﾐｻｲﾙﾌｨｽﾄ': '미사일피스트', 'ｽﾅｲﾌﾟ': '스나이프', 'ﾋﾞｰﾑﾗﾝﾁｬｰ': '빔런처', 'ﾊﾞｽﾞｰｶ': '바주카',
         'ﾋﾞｰﾑﾊﾞｽﾞ': '빔바주카', 'ﾐｻｲﾙﾎﾟｯﾄﾞ': '미사일포드', 'ﾐｻｲﾙﾊﾟｯｸ': '미사일팩', 'ﾐｻｲﾙ': '미사일',
         'ﾚｰﾙｶﾞﾝ': '레일건', 'ﾋﾞｰﾑｷｭｳﾎｳ': '빔구포', 'ﾛｹｯﾄﾗﾝﾁｬｰ': '로켓런처', 'ﾋﾞｰﾑｷｬﾉﾝ': '빔캐논',
         'ﾏｼﾝｶﾞﾝ': '머신건', 'ﾛﾝｸﾞｷｬﾉﾝ': '롱캐논', 'ｷｬﾉﾝ': '캐논', 'ｼｻｸﾚｰｻﾞｰ': '시제레이저', 'ﾚｰｻﾞｰｷｬﾉﾝ': '레이저캐논',
         'ｽﾓｰｸﾃﾞｨｽﾁｬｰｼﾞｬｰ': '스모크디스차저', 'ｼｮｳﾒｲﾀﾞﾝ': '조명탄', 'ｱｰﾏｰﾍﾟｲﾝﾄ': '아머페인트',
         'ﾊﾟﾜｰﾚｰｻﾞｰｻｲﾄ': '파워레이저사이트', 'ﾚｰｻﾞｰｻｲﾄ': '레이저사이트', 'ｾﾝｻｰﾓｼﾞｭｰﾙ': '센서모듈',
         'ｺｯｸﾋﾟｯﾄｱｰﾏｰ': '콕핏아머', 'ﾋﾞｰﾑｽﾍﾟｼｬﾙ': '빔스페셜'}
OTHER = [(0x0607BCDA, 'ｵｰﾄｾｰﾌﾞ', '자동저장'), (0x06079F1C, 'ﾜｸｾｲ ｦ ｾﾝﾀｸ ｼﾃｸﾀﾞｻｲ', '행성을 선택하십시오')]


def cstr(b, a): return b[a - L:b.index(b'\0', a - L)]


def rows(b0):
    bio = {r['id']: r['이름'] for r in csv.DictReader(open(os.path.join(ROOT, 'work/text/bio_ko.tsv'), encoding='utf-8'), delimiter='\t')}
    out = []; seen = set()
    for i in range(100):
        p = struct.unpack_from('>I', b0, NAMEPTR - L + 4 * i)[0]; ja = cstr(b0, p).decode('cp932')
        if p in seen: continue
        seen.add(p)
        ko = ja if re.fullmatch(r'[0-9A-Z]+', ja) else (bio.get('S%02d' % i) or NAME_EXTRA[ja])
        out.append(('name', '%08X' % p, i, ja, ko))
    a = WREC
    while a < WEND:
        ja = b0[a + 5 - L:a + 29 - L].split(b'\0')[0].decode('cp932'); ko = ja
        for k in sorted(WORDS, key=len, reverse=True): ko = ko.replace(k, WORDS[k])
        assert not re.search(r'[｡-ﾟ]', ko), ja
        out.append(('weapon', '%08X' % (a + 5), (a - WREC) // WSZ, ja, ko)); a += WSZ
    for a, ja, ko in OTHER:
        assert cstr(b0, a).decode('cp932').rstrip() == ja
        out.append(('other', '%08X' % a, 0, ja, ko))
    return out


if __name__ == '__main__':
    import disc
    rs = rows(disc.read('/0.BIN', 1))
    with open(os.path.join(ROOT, 'work/text/kana_ko.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('kind\taddr\tidx\tja\tko\n')
        for r in rs: f.write('%s\t%s\t%d\t%s\t%s\n' % r)
    syl = sorted({c for r in rs for c in r[4] if '가' <= c <= '힣'})
    print(len(rs), '행 · 음절', len(syl)); print(''.join(syl))
