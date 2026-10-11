# -*- coding: utf-8 -*-
r"""이름·무기 반각 가타카나 → 한글 8×8 훅(2026-10-11, docs/00 «가타카나» 절).
  · 문자열 한글 = 2바이트 [0x80, 음절 번호+1] (번호 = 번역표 kana_ko.tsv 음절 정렬 순서) — tools/kana_tr.py 표를 0.BIN 에 씀.
  · 가나 그리기 함수 다섯 입구(F1 0x0603FD80 · F2 0x0604000C · F3 0x06040304 · F4 0x06040E76 · F5 0x060410A0)를 덮어
      «MOV.L 리터럴,R0 · JMP @R0 · NOP · 리터럴» → 감싸개 Wk: 문자열에 0x80 이 있으면 버퍼로 옮기며 한글 음절마다 캐시 칸 바이트로 바꿈
      → 덮인 원래 명령(PC 상대 상수는 우리 리터럴로) 실행 → 입구+N 으로 점프. BSR 로 부르는 곳(0x06040984 등)도 다 잡힘.
  · 캐시 칸 55개 = 가나 바이트 0xA6‥0xAF·0xB1‥0xDD(모든 함수에서 서로 다른 글리프, 0xB0 ー 는 '-' 와 같아 뺌) · LRU(문자열 단위 틱).
      칸 배정 때 폭 표(F1 0x06083042 · F2 0x060830B9)에 8/9(ㅔ) · 그릴 때마다 그 벌 텍스처 칸(표 @0x060AAA44, 10 B 칸)이 8×8(0x0108)이면
      1비트 글꼴 → 4비트 화소 32 B 를 VDP1 VRAM 에 씀(장면이 글꼴을 다시 올려도 바로 덮음).
  · ⏳F3(메뉴 16×16)은 16×16 글꼴이 아직 없음 → 그 벌 칸 크기(0x0210)면 안 씀(가나 그대로 보임). 하스피: 8×8 확대 ⛔.
  · 자리: 실행 = RUN 0x060FD000‥(부팅 init 이 0.BIN 보관 자리에서 풀기, mhook.blob 의 extra) · 글꼴·이름 = 이름 구역 0x06079560‥0x06079C28.
"""
import os, struct, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hook as H, han8, kana_tr
A = H.A
L = 0x06004000
KBASE = 0x060FD000; KEND = 0x060FE000
TEXTBL = 0x060AAA44                                   # 텍스처 표 포인터
VRAM = 0x25C00000
NAMEPTR = 0x060815CC; NREG = (0x06079560, 0x06079C28)
SLOTB = bytes(list(range(0xA6, 0xB0)) + list(range(0xB1, 0xDE)))   # 55
NS = len(SLOTB)
# 벌: (텍스처 기준, 폭 표(0 = 고정 폭), 캐시 바이트 → 글리프 번호 55개) — 흉내기로 뽑음(work/kana/fmap.py, verify())
_G1 = bytes.fromhex('51535455565758595a7625262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f5052')
_G2 = bytes.fromhex('757778797a7b7d7e7f7c494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737476')
_G3 = bytes.fromhex('84868788898a8c8d8e8b58595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f8081828385')
SETS = [(0x1C8, 0x06083042, _G1), (0x384, 0x060830B9, _G2), (0x44C, 0, _G3), (0x4B4, 0, _G1)]
MODE16 = 2                                            # 벌 2(F3, 메뉴 16×16) = 캐시 대신 «문자열 안 n번째 한글 → 임시 바이트 n» + 스프라이트 호출 가로채기(remap)
F3 = 0x06040304; F3_BSR = 0x06040646; SPR = 0x0603F7B4; W3TBL = 0x06083154
# 함수: (입구, 벌 번호)
FUNCS = [(0x0603FD80, 0), (0x0604000C, 1), (0x06040304, 2), (0x06040E76, 3), (0x060410A0, 3)]
BUFSZ = 40

VAR = KBASE; SLOTS = VAR + 4; TICK = SLOTS + 56; SLOTBA = TICK + 56; TMP = SLOTBA + 56; DESC = TMP + 56
BUF = DESC + 64 * len(SETS); CODE = BUF + BUFSZ * len(FUNCS)


def nstub(e): return 24 if e == F3 else 12 if e % 4 == 0 else 10


def stub(e):
    """입구 덮개: MOV.L @(1,PC),R0 · JMP @R0 · NOP · (E%4==2 면 리터럴 E+6) / (E%4==0 면 E+4 NOP 하나 더, 리터럴 E+8)"""
    if e == F3:                                                                       # + E+12 징검다리(F3 안 BSR 0x0603F7B4 → remap), 리터럴 E+20
        return struct.pack('>HHHHIHHHH', 0xD001, 0x402B, 0x0009, 0x0009, 0, 0xD001, 0x402B, 0x0009, 0x0009)
    if e % 4 == 0: return struct.pack('>HHHH', 0xD001, 0x402B, 0x0009, 0x0009)     # 리터럴 = (E)+4+4 = E+8
    return struct.pack('>HHH', 0xD001, 0x402B, 0x0009)                               # 리터럴 = (E−2)+4+4 = E+6


def displaced(a, d0, e):
    """덮이는 원래 명령을 감싸개 끝에 다시 씀 — PC 상대 상수 읽기는 우리 리터럴로"""
    for k in range(0, nstub(e), 2):
        pc = e + k; op = struct.unpack_from('>H', d0, pc - L)[0]; h = op >> 12; n = op >> 8 & 15
        if h == 0xD: a.ld(n, struct.unpack_from('>I', d0, ((pc + 4) & ~3) + (op & 0xFF) * 4 - L)[0])
        elif h == 0x9: a.ld(n, struct.unpack_from('>h', d0, pc + 4 + (op & 0xFF) * 2 - L)[0] & 0xFFFFFFFF)
        else:
            assert h not in (0xA, 0xB) and op >> 8 not in (0x89, 0x8B, 0x8D, 0x8F, 0xC7) and op & 0xF0FF not in (0x400B, 0x402B, 0x000B, 0x0023, 0x0003), hex(op)
            a.w(op)


def assemble(d0, font8):
    a = A(CODE); W = a.w
    # ── 감싸개(함수마다)
    for fi, (e, si) in enumerate(FUNCS):
        a.L('wrap%d' % fi)
        W(0x4F22, 0x2F46, 0x2F56, 0x2F66, 0x2F76)                    # PR·r4‥r7
        a.ld(5, DESC + 64 * si); a.ld(6, BUF + BUFSZ * fi)
        a.br('bsr', 'conv'); W(0x0009)
        W(0x67F6, 0x66F6, 0x65F6, 0x64F6, 0x6403, 0x4F26)             # r7‥r4 되살림 · r4 = 새 문자열 · PR
        displaced(a, d0, e)
        a.ld(2, e + nstub(e)); W(0x422B, 0x0009)
    # ── conv(r4 원문, r5 벌 묘사, r6 버퍼) → r0 = 쓸 문자열. r8‥r12 보존
    a.L('conv'); W(0x6143)
    a.L('sc'); W(0x6014, 0x2008); a.br('bt', 'none')
    W(0x8880); a.br('bf', 'sc')
    W(0x4F22, 0x2F86, 0x2F96, 0x2FA6, 0x2FB6, 0x2FC6, 0x2FD6)
    W(0x6843, 0x6963, 0x6A53, 0x6C63, 0xEB00 | (BUFSZ - 1), 0xED00)  # r8 원문 · r9 쓰기 · r10 묘사 · r12 버퍼 · r11 남은 칸 · r13 한글 순번(16×16)
    a.ld(1, VAR); W(0x6010, 0x7001, 0x2100)                           # 틱 += 1(문자열마다)
    a.L('lp'); W(0x6084, 0x2008); a.br('bt', 'fin')
    W(0x8880); a.br('bf', 'put')
    W(0x6484, 0x644C, 0x2448); a.br('bt', 'fin')                      # r4 = 음절 번호+1
    W(0x85A1, 0x2008); a.br('bt', 'cache')                            # 묘사 +2 = 방식(0 캐시 / 1 임시)
    a.ld(1, TMP); W(0x60D3, 0x0144)                                   # TMP[n] = 음절 번호+1
    a.ld(1, SLOTBA); W(0x001C, 0x7D01)                                # 바이트 = SLOTB[n] · n += 1
    a.br('bra', 'put'); W(0x0009)
    a.L('cache'); a.br('bsr', 'slot'); W(0x0009)                      # → r0 = 캐시 칸 바이트
    a.L('put'); W(0x2900, 0x7901, 0x4B10); a.br('bf', 'lp')
    a.L('fin'); W(0xE000, 0x2900, 0x60C3)
    W(0x6DF6, 0x6CF6, 0x6BF6, 0x6AF6, 0x69F6, 0x68F6, 0x4F26, 0x000B, 0x0009)
    a.L('none'); W(0x000B, 0x6043)
    # ── slot(r4 열쇠, r10 묘사) → r0 = 칸 바이트. r0‥r7 씀
    a.L('slot'); W(0x4F22)
    a.ld(1, SLOTS); W(0xE200, 0xE300 | NS)
    a.L('s1'); W(0x6023, 0x051C, 0x655C, 0x3540); a.br('bt', 'hit')
    W(0x7201, 0x3230); a.br('bf', 's1')
    W(0x2F46)                                                         # 열쇠 보관 · r4 = 고른 칸
    a.ld(6, TICK); a.ld(7, VAR); W(0x6770, 0x677C)                    # r7 = 지금 틱
    W(0xE200, 0xE3FF, 0xE400)                                         # i · 가장 큰 나이 −1 · 고른 칸
    a.L('l2'); W(0x6023, 0x051C, 0x655C, 0x2558); a.br('bf', 'used')
    W(0xE501, 0x4518); a.br('bra', 'cmp'); W(0x0009)                  # 빈 칸 = 나이 256
    a.L('used'); W(0x056C, 0x655C, 0x6073, 0x3058, 0x650C, 0x6023)    # 나이 = (지금 − 틱) & 0xFF
    a.L('cmp'); W(0x3537); a.br('bf', 'nx')
    W(0x6353, 0x6423)
    a.L('nx'); W(0x7201, 0xE000 | NS, 0x3200); a.br('bf', 'l2')
    W(0x65F6, 0x6043, 0x0154, 0x0674)                                 # SLOTS[칸] = 열쇠 · TICK[칸] = 지금
    W(0x6243, 0x6453)                                                 # r2 = 칸 · r4 = 열쇠
    a.br('bsr', 'setw'); W(0x0009)
    a.br('bra', 'got'); W(0x0009)
    a.L('hit'); a.ld(6, TICK); a.ld(7, VAR); W(0x6770, 0x6023, 0x0674)
    a.L('got'); a.br('bsr', 'putg'); W(0x0009)
    a.ld(1, SLOTBA); W(0x6023, 0x001C)
    W(0x4F26, 0x000B, 0x0009)
    # ── setw(r2 칸, r4 열쇠): 폭 8/9(글꼴 7열에 점 있으면 9) → 폭 표 있는 벌마다 표[글리프] = 폭
    a.L('setw'); a.ld(1, font8 - 8); W(0x6043, 0x4008, 0x4000, 0x310C)
    W(0xE308, 0xE500)
    a.L('swo'); W(0x6014, 0x250B, 0x4310); a.br('bf', 'swo')
    W(0x6053, 0xC901, 0x7008, 0x6503)
    a.ld(6, DESC); W(0xE300 | len(SETS))
    a.L('sw2'); W(0x5761, 0x2778); a.br('bt', 'sw3')
    W(0x6063, 0x7008, 0x302C, 0x6000, 0x600C, 0x0754)
    a.L('sw3'); W(0x7640, 0x4310); a.br('bf', 'sw2')
    W(0x000B, 0x0009)
    # ── putg(r2 칸, r4 열쇠, r10 묘사): 그 벌 텍스처 칸이 8×8 이면 VRAM 에 글자 32 B. r2 보존
    a.L('putg'); W(0x2F26)
    W(0x60A3, 0x7008, 0x302C, 0x6100, 0x611C)                         # r1 = 글리프 번호
    W(0x60A1, 0x600D, 0x310C)                                         # + 기준 = 텍스처 번호
    W(0x6013, 0x4000, 0x4108, 0x4100, 0x310C)                         # ×10
    a.ld(0, TEXTBL); W(0x6002, 0x310C)                                # r1 = 칸
    W(0x8511, 0x600D); a.ld(3, 0x0108); W(0x3030); a.br('bf', 'pret')
    W(0x6111, 0x611D, 0x4108, 0x4100); a.ld(0, VRAM); W(0x310C)       # r1 = VRAM
    a.ld(5, font8 - 8); W(0x6043, 0x4008, 0x4000, 0x350C)             # r5 = 글꼴 줄
    W(0xE608)
    a.L('pr'); W(0x6354, 0x633C, 0xE708, 0xE200)
    a.L('pb'); W(0x4208, 0x4208, 0x4300, 0x6033, 0x4019, 0xC901, 0x220B, 0x4710); a.br('bf', 'pb')
    W(0x6023, 0x4029, 0x2101, 0x7102, 0x2121, 0x7102)                 # 위 16비트 · 아래 16비트
    W(0x4610); a.br('bf', 'pr')
    a.L('pret'); W(0x62F6, 0x000B, 0x0009)
    # ── remap: F3 의 스프라이트 호출(BSR → 입구 징검다리) — r4 텍스처가 임시 바이트 n 의 글리프면 → IFF 한글 칸 tex16(TMP[n]−1)
    #    r0‥r3 만 쓰고 r5 는 스택에 잠깐(호출 직전 쌓은 인자 3개는 그대로) → 원래 0x0603F7B4 로 JMP(PR = F3 복귀)
    a.L('remap'); W(0x2F56)
    a.ld(1, (-0x44C) & 0xFFFFFFFF); W(0x604D, 0x301C)                 # r0 = 글리프 번호(r4 아래 16비트만 — 위는 찌꺼기일 수 있음)
    a.ld(1, DESC + 64 * MODE16 + 8); a.ld(2, TMP); W(0xE300 | NS)
    a.L('rl'); W(0x6514, 0x655C, 0x3500); a.br('bt', 'rf')
    W(0x7201, 0x4310); a.br('bf', 'rl')
    a.br('bra', 'rj'); W(0x0009)
    a.L('rf'); W(0x6020, 0x600C, 0x2008); a.br('bt', 'rj')
    W(0x70FF); a.ld(1, 0x4A4); W(0x310C)                              # t = 0x4A4 + k
    a.ld(3, 0x4D2); W(0x3132); a.br('bf', 'r1'); W(0x7109)            # 작은 가나 칸 9개 건너뜀
    a.L('r1'); a.ld(3, 0x524); W(0x3132); a.br('bf', 'r2'); W(0x7109)
    a.L('r2'); W(0x6413)
    a.L('rj'); W(0x65F6)
    a.ld(0, SPR); W(0x402B, 0x0009)
    a.L('kend')
    return a.build(), a.lab


def data_block():
    """VAR‥CODE 앞: 틱·칸·나이(0) · 칸 바이트 · 벌 묘사(기준 u16, 폭 표 u32, 글리프 55)"""
    b = bytearray(CODE - KBASE)
    b[SLOTBA - KBASE:SLOTBA - KBASE + NS] = SLOTB
    for i, (base, wt, g) in enumerate(SETS):
        o = DESC - KBASE + 64 * i
        struct.pack_into('>HHI', b, o, base, 1 if i == MODE16 else 0, wt); b[o + 8:o + 8 + NS] = g
    return b


# ── 문자열 표(0.BIN)
def table():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'work/text/kana_ko.tsv'), encoding='utf-8'), delimiter='\t'))
    syl = sorted({c for r in rows for c in r['ko'] if '가' <= c <= '힣'})
    return rows, syl


def enc(t, idx):
    out = bytearray()
    for c in t:
        if '가' <= c <= '힣': out += bytes([0x80, idx[c] + 1])
        else:
            assert 0x20 <= ord(c) < 0x7F, repr(c); out.append(ord(c))
    return bytes(out)


def font8(syl):
    f = bytearray()
    for c in syl:
        g, w = han8.glyph(c)
        for row in g: f.append(sum(v << (7 - i) for i, v in enumerate(row)))
    return bytes(f)


def patch_text(d0):
    """→ (0.BIN 바이트열, 글꼴 주소)"""
    d = bytearray(d0); rows, syl = table(); idx = {c: i for i, c in enumerate(syl)}
    assert len(syl) <= 254
    # 이름: 0‥99 번 새로 쌓기(같은 원문 주소 = 같은 새 문자열), 100‥255 = 자리표 하나
    pool = bytearray(); newp = {}
    for r in rows:
        if r['kind'] != 'name': continue
        newp[int(r['addr'], 16)] = NREG[0] + len(pool); pool += enc(r['ko'], idx) + b'\0'
    ph = NREG[0] + len(pool); pool += b'-\0'
    for i in range(256):
        o = NAMEPTR - L + 4 * i; p = struct.unpack_from('>I', d, o)[0]
        struct.pack_into('>I', d, o, newp[p] if i < 100 else ph)
    pool += bytes(-len(pool) % 4)
    fa = NREG[0] + len(pool); f = font8(syl); pool += f
    assert NREG[0] + len(pool) <= NREG[1], ('이름 구역 넘침', hex(NREG[0] + len(pool)))
    d[NREG[0] - L:NREG[1] - L] = bytes(pool) + bytes(NREG[1] - NREG[0] - len(pool))
    # 무기: 이름 칸 24 B
    for r in rows:
        a = int(r['addr'], 16)
        if r['kind'] == 'weapon':
            e = enc(r['ko'], idx); assert len(e) < 24, r; d[a - L:a + 24 - L] = e + bytes(24 - len(e))
        elif r['kind'] == 'other':
            n = d.index(b'\0', a - L) - (a - L); e = enc(r['ko'], idx); assert len(e) <= n, r
            d[a - L:a - L + n] = e + b' ' * (n - len(e))
    return bytes(d), fa


def build(d0):
    """→ (0.BIN(문자열·입구 덮개 반영), RUN 0x060FD000 이미지, 라벨)"""
    d, fa = patch_text(d0)
    code, lab = assemble(d0, fa)
    img = bytes(data_block()) + code
    assert KBASE + len(img) <= KEND, hex(KBASE + len(img))
    d = bytearray(d)
    for fi, (e, si) in enumerate(FUNCS):
        n = nstub(e); s = stub(e)
        d[e - L:e - L + len(s)] = s
        struct.pack_into('>I', d, e + (8 if e == F3 else n - 4) - L, lab['wrap%d' % fi])
        if e == F3: struct.pack_into('>I', d, e + 20 - L, lab['remap'])
    # F3 안 BSR 0x0603F7B4 → 입구 징검다리(F3+12)
    assert struct.unpack_from('>H', d0, F3_BSR - L)[0] >> 12 == 0xB
    dd = (F3 + 12 - (F3_BSR + 4)) // 2; assert -2048 <= dd < 2048
    struct.pack_into('>H', d, F3_BSR - L, 0xB000 | (dd & 0xFFF))
    # F3 폭 표: 임시 바이트 글리프 = 한글 16×16 간격(가나 문자열은 더 없음)
    import iffkr
    for g in _G3: d[W3TBL + g - L] = iffkr.ADV16
    return bytes(d), img, lab


if __name__ == '__main__':
    import disc
    d, img, lab = build(disc.read('/0.BIN', 1))
    print('RUN 이미지 %d B (0x%08X‥0x%08X) · RLE %d B' % (len(img), KBASE, KBASE + len(img), len(H.rle(img))))
