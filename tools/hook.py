# -*- coding: utf-8 -*-
r"""미션 음성 자막 훅 PoC(2026-10-11) — 대사 1개(WDE00/VE001.B 조각 0, 미션대사2 스테이트) 에만 미리 구운 자막 그림.
  · 훅: VBlank-IN 처리기(0x06009736) 끝 `JMP @R1` 의 상수 0x06009814(0.BIN 0x5814, 원래 0x06043294) → 우리 코드 → 끝에 0x06043294 로.
  · 자리: ★0.BIN 의 BSS(0x06089830‥0x060AA568, 시작 코드가 0 으로 지움 — PoC 1차 «부팅불가» 원인) 바깥 파일 자료 영역.
          그림(2비트) 0x060AD080‥0x060AD840 · LUT·우리 칸·코드 0x060ADDC0‥0x060AE180 (파일·스테이트 24장 모두 0, 안을 가리키는 상수 없음).
  · 판정: PCM 핸들 0번 0x0608B348 — +0x34 STAT 4 = 재생 중 · +4 지금 조각 주소 · +8 길이. 열쇠 = (길이, 조각 가운데 4 B).
  · 그림: 4비트 LUT 모드(0 투명 · 1 검정 테두리 · 2 흰 글자, LUT 값은 RGB — SPCTL 0x1131 팔레트·RGB 섞어 씀, 스프라이트 우선순위 2 > NBG0 1)
          → VDP1 명령표 B 벌 꼬리 0xA000‥(전투 106칸 ≪ 559칸). 켜진 동안 매 프레임 그림·LUT·우리 칸(스프라이트+END)을 다시 써 넣음.
  · 명령: 두 벌(A 0x000A0 · B 0x05A20) 모두 VDP1 이 읽는 순서대로 따라가 END 칸 → «건너뛰고 점프(0x5000) → 우리 칸». 꺼지면 END 로.
"""
import importlib.util, struct
_sp = importlib.util.spec_from_file_location('sh2asm', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2asm.py')
_m = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_m); A = _m.A

LOAD = 0x06004000                       # 0.BIN 적재
VBI_LIT = 0x06009814; ORIG = 0x06043294
TEX_AREA = (0x060AD080, 0x060AD840)    # 2비트 그림 원본
CODE_AREA = (0x060ADDC0, 0x060AE180)   # LUT·우리 칸·코드
BSS = (0x06089830, 0x060AA568)
H0 = 0x2608B348                         # PCM 핸들 0번(캐시 거치지 않는 주소)
LIST = 0x25C00000; LA = 0x25C000A0; LB = 0x25C05A20
TEX = 0x25C0A000; LUT = 0x25C0B4E0; OWN = 0x25C0B560
TEXA = (TEX & 0x7FFFF) // 8; LUTA = (LUT & 0x7FFFF) // 8; OWNL = (OWN & 0x7FFFF) // 8
assert OWN + 64 <= 0x25C0B5C0
W8, HT = 20, 41                         # 그림 160×41 (4비트)
X, Y = 100, 176                         # 화면 좌표(지역 좌표 0,0) — 아래 왼쪽 얼굴(x<98)·오른쪽 레이더(x>261) 사이
TEXN = W8 * 4 * HT                     # VRAM 4비트 크기
TEX2 = TEXN // 2                       # 2비트 원본 크기
def keyoff(ln): return (ln >> 3) << 2      # 열쇠 4 B 위치 = 조각 가운데(앞쪽은 AIFF 머리·무음이라 0)
D_TEX = TEX_AREA[0]; D_LUT = CODE_AREA[0]; D_CMD = D_LUT + 32; VAR = D_CMD + 64; CODE = VAR + 4   # VAR = 붙였음 깃발(꺼질 때만 목록 훑기 — 부팅·메뉴에서 매 VBlank 2×1024칸 훑지 않게)


def data():
    lut = struct.pack('>16H', 0, 0x8000, 0xFFFF, *([0] * 13))
    cmd = struct.pack('>16H', 0x0000, 0, 0x0088, LUTA, TEXA, W8 << 8 | HT, X, Y, 0, 0, 0, 0, 0, 0, 0, 0) + struct.pack('>16H', 0x8000, *([0] * 15))
    return lut, cmd


def assemble(keylen, key4):
    a = A(CODE); W = a.w
    # ---- 진입(VBI-IN 끝에서 JMP 로 옴: PR = 분배기 복귀) ----
    a.L('vbi'); W(0x4F22, 0x2F46, 0x2F56, 0x2F66, 0x2F76)             # PR·r4‥r7 보존
    a.ld(4, H0)
    W(0x504D)                                                           # mov.l @(0x34,r4),r0
    W(0x8804); a.br('bf', 'off')                                        # STAT == 4
    W(0x5242)                                                           # mov.l @(8,r4),r2  길이
    a.ld(3, keylen); W(0x3320); a.br('bf', 'off')
    W(0x6323, 0x4309, 0x4301, 0x4308)                                  # r3 = (길이>>3)<<2 = 가운데(4 B 정렬)
    W(0x5241, 0x323C, 0x6222)                                           # r2 = @(조각 + r3)
    a.ld(3, key4); W(0x3320); a.br('bf', 'off')
    # ---- 켜짐 ----
    a.ld(1, D_TEX); a.ld(2, TEX); a.ld(3, TEX2); a.br('bsr', 'expand'); W(0x0009)
    a.ld(1, D_LUT); a.ld(2, LUT); W(0xE308); a.br('bsr', 'copy'); W(0x0009)
    a.ld(1, D_CMD); a.ld(2, OWN); W(0xE310); a.br('bsr', 'copy'); W(0x0009)
    a.ld(1, LA); a.br('bsr', 'ins'); W(0x0009)
    a.ld(1, LB); a.br('bsr', 'ins'); W(0x0009)
    a.ld(1, VAR); W(0xE001, 0x2102)                                     # 깃발 = 1
    a.br('bra', 'done'); W(0x0009)
    a.L('off')
    a.ld(1, VAR); W(0x6012, 0x2008); a.br('bt', 'done')                 # 깃발 0 이면 할 일 없음
    W(0xE000, 0x2102)
    a.ld(1, LA); a.br('bsr', 'unins'); W(0x0009)
    a.ld(1, LB); a.br('bsr', 'unins'); W(0x0009)
    a.L('done'); W(0x67F6, 0x66F6, 0x65F6, 0x64F6, 0x4F26)
    a.ld(1, ORIG); W(0x412B, 0x0009)                                    # jmp @r1
    # ---- copy(r1 원본, r2 대상, r3 롱 수) ----
    a.L('copy'); a.L('cl'); W(0x6016, 0x2202, 0x7204, 0x4310); a.br('bf', 'cl'); W(0x000B, 0x0009)
    # ---- expand(r1 2비트 원본, r2 VRAM, r3 바이트 수): 바이트 b → 16비트 (b>>6)<<12 | ((b>>4)&3)<<8 | ((b>>2)&3)<<4 | b&3. r0·r4‥r6 씀 ----
    a.L('expand'); a.L('el')
    W(0x6514, 0x655C)                                                   # r5 = b
    W(0x6053, 0x4009, 0x4009, 0x6603, 0xC903, 0x4609, 0x4608, 0x4608, 0x206B)   # r0 = (b>>6)<<4 | (b>>4)&3
    W(0x4018, 0x6403)                                                   # r4 = 위 바이트
    W(0x6053, 0x4009, 0xC903, 0x4008, 0x4008, 0x6603)                   # r6 = ((b>>2)&3)<<4
    W(0x6053, 0xC903, 0x206B, 0x204B)                                   # r0 = b&3 | r6 | r4
    W(0x2201, 0x7202, 0x4310); a.br('bf', 'el'); W(0x000B, 0x0009)
    # ---- walk(r1 = 시작) → r1 = END 또는 우리 점프 칸(못 찾으면 0). r0·r2·r3 씀 ----
    a.L('walk'); a.ld(3, 1024)
    a.L('wl'); W(0x6011, 0x600D)                                        # r0 = ctrl
    a.ld(2, 0x8000); W(0x2208); a.br('bf', 'wret')                      # tst r0,r2 → END(T=0) 면 돌아감
    a.ld(2, 0x5000); W(0x3020); a.br('bf', 'wjp')
    W(0x8511, 0x600D); a.ld(2, OWNL); W(0x3020); a.br('bt', 'wret')     # 우리 점프
    W(0x6011, 0x600D)
    a.L('wjp'); W(0x4019, 0x4009, 0x4009, 0xC903, 0x8801); a.br('bf', 'wnx')   # (ctrl>>12)&3 == 1 → 점프
    W(0x8511, 0x600D, 0x4008, 0x4000); a.ld(2, LIST); W(0x302C, 0x6103); a.br('bra', 'wdt'); W(0x0009)
    a.L('wnx'); W(0x7120)
    a.L('wdt'); W(0x4310); a.br('bf', 'wl')
    W(0xE100)
    a.L('wret'); W(0x000B, 0x0009)
    # ---- ins(r1 = 시작): END 칸이면 «건너뛰고 점프 → 우리 칸» ----
    a.L('ins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'iret')
    W(0x6011, 0x600D); a.ld(2, 0x8000); W(0x2208); a.br('bt', 'iret')  # 우리 점프 칸이면 그대로
    a.ld(0, 0x5000); W(0x2101); a.ld(0, OWNL); W(0x8111)
    a.L('iret'); W(0x4F26, 0x000B, 0x0009)
    # ---- unins(r1 = 시작): 우리 점프 칸이면 END ----
    a.L('unins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'uret')
    W(0x6011, 0x600D); a.ld(2, 0x5000); W(0x3020); a.br('bf', 'uret')
    a.ld(0, 0x8000); W(0x2101)
    a.L('uret'); W(0x4F26, 0x000B, 0x0009)
    return a.build(), a.lab


def pack2(px):
    """4비트 값(0‥2) 그림 → 2비트(바이트마다 4화소, 앞 화소가 위 비트)"""
    f = px.ravel()
    return bytes(((f[0::4] << 6) | (f[1::4] << 4) | (f[2::4] << 2) | f[3::4]).tolist())


def blob(px, keylen, key4):
    """→ ({주소: 바이트}, 라벨)"""
    tex2 = pack2(px); assert len(tex2) == TEX2
    lut, cmd = data(); code, lab = assemble(keylen, key4)
    parts = {D_TEX: tex2, D_LUT: lut + cmd + bytes(4) + code}
    assert D_TEX + len(tex2) <= TEX_AREA[1], hex(D_TEX + len(tex2))
    assert D_LUT + len(parts[D_LUT]) <= CODE_AREA[1], hex(D_LUT + len(parts[D_LUT]))
    for a, b in parts.items(): assert not (BSS[0] <= a < BSS[1]) and not (BSS[0] < a + len(b) <= BSS[1])
    return parts, lab


def patch_0bin(d0, parts, lab):
    d = bytearray(d0)
    o = VBI_LIT - LOAD
    assert struct.unpack_from('>I', d, o)[0] == ORIG
    for a, b in parts.items():
        c = a - LOAD
        assert d[c:c + len(b)] == bytes(len(b)), ('자리가 0 이 아님', hex(a))
        d[c:c + len(b)] = b
    struct.pack_into('>I', d, o, lab['vbi'])
    assert len(d) == len(d0)
    return bytes(d)
