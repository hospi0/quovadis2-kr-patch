# -*- coding: utf-8 -*-
r"""미션 음성 자막 훅(2026-10-11 PoC 4차 — 대사 여러 개·화자 쪽 따라 위/아래).
  · 훅: VBlank-IN 처리기(0x06009736) 끝 `JMP @R1` 의 상수 0x06009814(0.BIN 0x5814, 원래 0x06043294) → 우리 코드 → 끝에 0x06043294 로.
  · ★실행 자리 RUN = 상위 RAM 0x060FC000‥0x060FD800(스택 0x060FF000 아래, 스테이트 최저 스택 0x060FEB70, 0.BIN 상수가 가리키는 마지막 0x060FBFE0).
    0.BIN 안은 BSS(0x06089830‥0x060AA568, 부팅 때 지움 — PoC 1차 부팅불가)·뒤쪽은 실행 중 오버레이가 덮어씀(2차 부팅불가) → 상주 불가.
    → 디스크엔 RUN 내용을 «0 반복 줄이기(RLE)»로 0.BIN 뒤쪽 두 자리(부팅 직후엔 온전)에 보관, 시작 코드의 main 점프 상수 0x0600404C(원래 0x0600406C)
      → 우리 init 이 풀어서 RUN 에 놓고 PR 되살려 main 으로(3차 실기 성공).
  · 판정: PCM 핸들 0번 0x0608B348 — +0x34 STAT 4 = 재생 중 · +4 지금 조각 주소 · +8 길이. 열쇠 = (길이, 조각 가운데 4 B) → 대사 표.
  · 화자 쪽: 창별 «말하는 중 = 00» — 아래 창 0x060A56D7 · 위 창 0x060A575B(하스피 스테이트 위 3·아래 5 일치). 위 00 && 아래 FF → 위쪽 자리.
  · 그림: 2비트 원본(0 투명·1 검정 테두리·2 흰 글자) → VDP1 VRAM 0xA000(명령표 B 벌 꼬리, 전투 106칸 ≪ 559칸) 4비트 LUT 모드(LUT 값 RGB).
          켜진 동안 매 프레임 그림·LUT·우리 칸(스프라이트+END) 다시 써 넣음. 두 벌(A 0x000A0 · B 0x05A20) END → «건너뛰고 점프 → 우리 칸».
"""
import importlib.util, struct
_sp = importlib.util.spec_from_file_location('sh2asm', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2asm.py')
_m = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_m); A = _m.A

LOAD = 0x06004000
VBI_LIT = 0x06009814; ORIG = 0x06043294
MAIN_LIT = 0x0600404C; MAIN = 0x0600406C
BSS = (0x06089830, 0x060AA568)
RUN = 0x060FC000; RUN_END = 0x060FE000   # PoC 4차 대사 5개(2비트 그림 3.3 KB + 코드) — 스테이트 최저 스택 0x060FEB70 과 2.9 KB
STORE = [(0x060AD080, 0x060AD840), (0x060ADDC0, 0x060AE180)]   # 디스크 보관(부팅 직후 온전) — 둘째 자리 앞에 init
H0 = 0x2608B348
WIN_BOT = 0x260A56D7; WIN_TOP = 0x260A575B
LIST = 0x25C00000; LA = 0x25C000A0; LB = 0x25C05A20
TEX = 0x25C0A000; LUT = 0x25C0B4E0; OWN = 0x25C0B560
TEXA = (TEX & 0x7FFFF) // 8; LUTA = (LUT & 0x7FFFF) // 8; OWNL = (OWN & 0x7FFFF) // 8
assert OWN + 64 <= 0x25C0B5C0
W8 = 20                                 # 그림 폭 160
X, Y = 100, 176                         # 아래쪽 — 아래 왼쪽 얼굴(x<98)·오른쪽 레이더(x>261) 사이
XT, YT = 82, 4                          # 위쪽 — 위 얼굴(x<82)·오른쪽 위 HUD «待機»(x≥240) 사이


def keyoff(ln): return (ln >> 3) << 2   # 열쇠 4 B 위치 = 조각 가운데


def layout(n):
    """RUN 앞쪽 고정 자리: 표(16 B × (n+1)) · LUT · 우리 칸 · 깃발 · 코드"""
    tab = RUN; lut = tab + 16 * (n + 1); cmd = lut + 32; var = cmd + 64; code = var + 4
    return tab, lut, cmd, var, code


def assemble(n):
    TAB, D_LUT, D_CMD, VAR, CODE = layout(n)
    a = A(CODE); W = a.w
    a.L('vbi'); W(0x4F22, 0x2F46, 0x2F56, 0x2F66, 0x2F76)
    a.ld(4, H0)
    W(0x504D, 0x8804); a.br('bf', 'off')                                # STAT == 4
    W(0x5242)                                                           # r2 = 길이
    W(0x6323, 0x4309, 0x4301, 0x4308)                                  # r3 = 가운데
    W(0x5541, 0x353C, 0x6552)                                           # r5 = @(조각 + r3) = 열쇠
    a.ld(6, TAB)
    a.L('tl'); W(0x6062, 0x2008); a.br('bt', 'off')                     # 표 끝(길이 0)
    W(0x3020); a.br('bf', 'tn')
    W(0x5061, 0x3050); a.br('bt', 'found')
    a.L('tn'); W(0x7610); a.br('bra', 'tl'); W(0x0009)
    a.L('found')
    W(0x5162, 0x5763)                                                   # r1 = 그림 원본 · r7 = 크기<<16 | 바이트 수
    a.ld(2, TEX); W(0x637D); a.br('bsr', 'expand'); W(0x0009)
    a.ld(1, D_LUT); a.ld(2, LUT); W(0xE308); a.br('bsr', 'copy'); W(0x0009)
    a.ld(1, D_CMD); a.ld(2, OWN); W(0xE310); a.br('bsr', 'copy'); W(0x0009)
    a.ld(1, OWN); W(0x6073, 0x4029, 0x8115)                             # 우리 칸 SIZE = r7>>16
    a.ld(1, WIN_TOP); W(0x6010, 0x600C, 0x8800); a.br('bf', 'side')     # 위 창 00 ?
    a.ld(1, WIN_BOT); W(0x6010, 0x600C, 0x8800); a.br('bt', 'side')     # 아래 창도 00 이면 아래쪽(미션 밖)
    a.ld(1, OWN); W(0xE000 | XT, 0x8116, 0xE000 | YT, 0x8117)
    a.L('side')
    a.ld(1, LA); a.br('bsr', 'ins'); W(0x0009)
    a.ld(1, LB); a.br('bsr', 'ins'); W(0x0009)
    a.ld(1, VAR); W(0xE001, 0x2102)
    a.br('bra', 'done'); W(0x0009)
    a.L('off')
    a.ld(1, VAR); W(0x6012, 0x2008); a.br('bt', 'done')
    W(0xE000, 0x2102)
    a.ld(1, LA); a.br('bsr', 'unins'); W(0x0009)
    a.ld(1, LB); a.br('bsr', 'unins'); W(0x0009)
    a.L('done'); W(0x67F6, 0x66F6, 0x65F6, 0x64F6, 0x4F26)
    a.ld(1, ORIG); W(0x412B, 0x0009)
    # copy(r1, r2, r3 롱 수)
    a.L('copy'); a.L('cl'); W(0x6016, 0x2202, 0x7204, 0x4310); a.br('bf', 'cl'); W(0x000B, 0x0009)
    # expand(r1 2비트, r2 VRAM, r3 바이트 수) — r0·r4‥r6 씀, r7 안 건드림
    a.L('expand'); a.L('el')
    W(0x6514, 0x655C)
    W(0x6053, 0x4009, 0x4009, 0x6603, 0xC903, 0x4609, 0x4608, 0x4608, 0x206B)
    W(0x4018, 0x6403)
    W(0x6053, 0x4009, 0xC903, 0x4008, 0x4008, 0x6603)
    W(0x6053, 0xC903, 0x206B, 0x204B)
    W(0x2201, 0x7202, 0x4310); a.br('bf', 'el'); W(0x000B, 0x0009)
    # walk(r1 시작) → END 또는 우리 점프 칸(없으면 0)
    a.L('walk'); a.ld(3, 1024)
    a.L('wl'); W(0x6011, 0x600D)
    a.ld(2, 0x8000); W(0x2208); a.br('bf', 'wret')
    a.ld(2, 0x5000); W(0x3020); a.br('bf', 'wjp')
    W(0x8511, 0x600D); a.ld(2, OWNL); W(0x3020); a.br('bt', 'wret')
    W(0x6011, 0x600D)
    a.L('wjp'); W(0x4019, 0x4009, 0x4009, 0xC903, 0x8801); a.br('bf', 'wnx')
    W(0x8511, 0x600D, 0x4008, 0x4000); a.ld(2, LIST); W(0x302C, 0x6103); a.br('bra', 'wdt'); W(0x0009)
    a.L('wnx'); W(0x7120)
    a.L('wdt'); W(0x4310); a.br('bf', 'wl')
    W(0xE100)
    a.L('wret'); W(0x000B, 0x0009)
    a.L('ins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'iret')
    W(0x6011, 0x600D); a.ld(2, 0x8000); W(0x2208); a.br('bt', 'iret')
    a.ld(0, 0x5000); W(0x2101); a.ld(0, OWNL); W(0x8111)
    a.L('iret'); W(0x4F26, 0x000B, 0x0009)
    a.L('unins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'uret')
    W(0x6011, 0x600D); a.ld(2, 0x5000); W(0x3020); a.br('bf', 'uret')
    a.ld(0, 0x8000); W(0x2101)
    a.L('uret'); W(0x4F26, 0x000B, 0x0009)
    return a.build(), a.lab


def pack2(px):
    f = px.ravel()
    return bytes(((f[0::4] << 6) | (f[1::4] << 4) | (f[2::4] << 2) | f[3::4]).tolist())


def run_image(entries):
    """entries = [(길이, 열쇠4, px(높이×160 값 0‥2))] → (RUN 내용(그림 칸은 0 — init 이 채움), 라벨, 그림 칸 주소들)"""
    n = len(entries); TAB, D_LUT, D_CMD, VAR, CODE = layout(n)
    code, lab = assemble(n)
    img = bytearray(CODE - RUN) + code
    img += bytes(-len(img) % 4)
    tab = b''; tptrs = []
    for ln, k4, px in entries:
        h = px.shape[0]; nb = W8 * 2 * h; assert px.shape[1] == W8 * 8 and nb * 2 <= 0x25C0B4E0 - TEX
        ptr = RUN + len(img); tptrs.append(ptr); img += bytes(nb + (-nb % 4))
        tab += struct.pack('>IIIHH', ln, k4, ptr, W8 << 8 | h, nb)
    tab += bytes(16)
    img[0:len(tab)] = tab
    lut = struct.pack('>16H', 0, 0x8000, 0xFFFF, *([0] * 13))
    cmd = struct.pack('>16H', 0x0000, 0, 0x0088, LUTA, TEXA, 0, X, Y, 0, 0, 0, 0, 0, 0, 0, 0) + struct.pack('>16H', 0x8000, *([0] * 15))
    o = D_LUT - RUN; img[o:o + 32] = lut; o = D_CMD - RUN; img[o:o + 64] = cmd
    assert RUN + len(img) <= RUN_END, hex(RUN + len(img))
    return bytes(img), lab, tptrs


GW = W8 + 2                            # 1비트 글자판 폭(좌우 0 바이트 덧댐)


def gpad(px):
    """글자(값 2)만 1비트, 위아래 0 줄·좌우 0 바이트 덧댐 → (h+2)×GW 바이트"""
    import numpy as np
    g = np.packbits((px == 2).astype(np.uint8), axis=1)
    p = np.zeros((g.shape[0] + 2, GW), np.uint8); p[1:-1, 1:-1] = g
    return p.tobytes()


def rle(b):
    """0 이 아닌 바이트 = 그대로 · 0 = (0, 개수 1‥255) · 끝 = (0, 0)"""
    out = bytearray(); i = 0
    while i < len(b):
        if b[i]:
            out.append(b[i]); i += 1
        else:
            j = i
            while j < len(b) and not b[j] and j - i < 255: j += 1
            out += bytes([0, j - i]); i = j
    return bytes(out)


def init_code(src2, jobs):
    """부팅 init: 보관 두 자리 RLE → RUN 부터 연속으로 풀기 → 작업(글자판·그림·높이, 높이 0 끝)마다 테두리 계산해 2비트 그림 → PR 되살려 main.
       테두리 D = 위·가운데·아래 줄 OR(Vc) 를 좌우 1비트 번짐(옆 바이트 넘김 포함) · 화소 = 글자 2 / (D 이고 글자 아님) 1 / 0"""
    a = A(STORE[1][0]); W = a.w
    a.L('init'); W(0x4F22, *[0x2F06 | r << 4 for r in range(8, 15)])   # PR·r8‥r14 보존
    a.ld(1, STORE[0][0]); a.ld(2, RUN); a.br('bsr', 'rle'); W(0x0009)
    a.ld(1, src2); a.br('bsr', 'rle'); W(0x0009)                       # r2 이어서
    a.ld(14, jobs)
    a.L('job'); W(0x68E6, 0x69E6, 0x6AE6)                             # r8 글자판 · r9 그림 · r10 높이
    W(0x2AA8); a.br('bt', 'jend')
    W(0x7816)                                                           # r8 += 22 → 첫 진짜 줄의 왼쪽 덧댐
    a.L('row'); W(0x7801, 0xEB14)                                       # r8 += 1 → 첫 바이트 · r11 = 20
    a.L('byte')
    a.br('bsr', 'vsum'); W(0xE500); W(0x6C03)                           # r12 = Vc
    a.br('bsr', 'vsum'); W(0xE5FF); W(0x6D03)                           # r13 = Vl
    a.br('bsr', 'vsum'); W(0xE501); W(0x6403)                           # r4 = Vr
    W(0x60C3, 0x4000, 0x20CB)                                           # r0 = Vc<<1 | Vc
    W(0x6343, 0x4309, 0x4309, 0x4309, 0x4301, 0x203B)                   # | Vr>>7
    W(0x63C3, 0x4301, 0x203B)                                           # | Vc>>1
    W(0x63D3, 0x4318, 0x4301, 0x203B)                                   # | Vl<<7
    W(0xC9FF, 0x6603)                                                   # r6 = D(바이트)
    W(0x6080, 0x600C, 0x6503)                                           # r5 = g = @r8
    W(0x6757, 0x2679)                                                   # r6 = D & ~g
    W(0xE300, 0xE708)                                                   # r3 = 출력 · r7 = 8
    a.L('bit'); W(0x4308, 0x6053, 0xC880); a.br('bt', 'b1'); W(0x7302)
    a.L('b1'); W(0x6063, 0xC880); a.br('bt', 'b2'); W(0x7301)
    a.L('b2'); W(0x4500, 0x4600, 0x4710); a.br('bf', 'bit')
    W(0x2931, 0x7902)                                                   # 그림 16비트 · r9 += 2
    W(0x7801, 0x4B10); a.br('bf', 'byte')
    W(0x7801)                                                           # 오른쪽 덧댐 건너뜀
    W(0x4A10); a.br('bf', 'row')
    a.br('bra', 'job'); W(0x0009)
    a.L('jend'); W(*[0x60F6 | r << 8 for r in range(14, 7, -1)], 0x4F26)
    a.ld(1, MAIN); W(0x412B, 0x0009)
    # vsum(r8, r5 = −1/0/+1) → r0 = @(r1−22)|@r1|@(r1+22), r1 = r8+r5. r1·r2 씀
    a.L('vsum'); W(0x6183, 0x315C, 0x6010, 0x600C)
    W(0x6213, 0x72EA, 0x6220, 0x622C, 0x202B)
    W(0x6213, 0x7216, 0x6220, 0x622C, 0x202B)
    W(0x000B, 0x0009)
    a.L('rle'); a.L('rl'); W(0x6014, 0x600C, 0x2008); a.br('bf', 'lit')
    W(0x6014, 0x600C, 0x2008); a.br('bt', 'rend')
    W(0x6303, 0xE000)
    a.L('rz'); W(0x2200, 0x7201, 0x4310); a.br('bf', 'rz')
    a.br('bra', 'rl'); W(0x0009)
    a.L('lit'); W(0x2200, 0x7201); a.br('bra', 'rl'); W(0x0009)
    a.L('rend'); W(0x000B, 0x0009)
    return a.build(), a.lab


INIT_TOP = 0x060FEE00                   # 부팅 init 때 풀어 쓰는 끝(그때 스택은 0x060FF000 바로 아래만 씀)


def blob(entries):
    """→ ({0.BIN 주소: 바이트}, 라벨, RUN 내용(그림 칸 0))"""
    img, lab, tptrs = run_image(entries)
    jobs = RUN + len(img); gbase = jobs + 12 * (len(entries) + 1)
    jb = b''; gb = b''
    for (ln, k4, px), tp in zip(entries, tptrs):
        g = gpad(px); jb += struct.pack('>III', gbase + len(gb), tp, px.shape[0]); gb += g + bytes(-len(g) % 4)
    jb += bytes(12)
    full = img + jb + gb
    assert RUN + len(full) <= INIT_TOP, hex(RUN + len(full))
    cap1 = STORE[0][1] - STORE[0][0]
    cut = len(full)
    while len(rle(full[:cut])) + 2 > cap1: cut -= 4
    s1 = rle(full[:cut]) + b'\0\0'; s2 = rle(full[cut:]) + b'\0\0'
    ini, _ = init_code(0x06000001, jobs)
    src2 = STORE[1][0] + len(ini)
    ini, ilab = init_code(src2, jobs); assert STORE[1][0] + len(ini) == src2
    p2 = ini + s2
    assert STORE[1][0] + len(p2) <= STORE[1][1], ('보관 자리 넘침', len(p2), STORE[1][1] - STORE[1][0])
    lab.update(ilab)
    return {STORE[0][0]: s1, STORE[1][0]: p2}, lab, img


def patch_0bin(d0, parts, lab):
    d = bytearray(d0)
    for lit, old, new in ((VBI_LIT, ORIG, lab['vbi']), (MAIN_LIT, MAIN, lab['init'])):
        o = lit - LOAD; assert struct.unpack_from('>I', d, o)[0] == old, hex(lit)
        struct.pack_into('>I', d, o, new)
    for a, b in parts.items():
        assert not (BSS[0] <= a < BSS[1])
        c = a - LOAD; assert d[c:c + len(b)] == bytes(len(b)), ('자리가 0 이 아님', hex(a))
        d[c:c + len(b)] = b
    assert len(d) == len(d0)
    return bytes(d)
