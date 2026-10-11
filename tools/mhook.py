# -*- coding: utf-8 -*-
r"""미션 음성 자막 훅 본판(2026-10-11, PoC 4차 hook.py 에서 — 자막 자료를 0.BIN 대신 디스크 «짝 자막 파일»로).
  · 짝 자막 파일: 음성 V 파일마다 KD???/V????.B (WD 폴더 이름 첫 글자 W→K, 파일 이름 같음) — tools/ksub.py 가 만들고 tools/isoadd.py 가 트랙 1 끝에 덧붙임.
      머리 'QVK1' · 항목 수(u32) · 항목 16 B × n: 조각 길이(u32) · 열쇠(u32, 조각 가운데 4 B) · 자료 위치(u16, 파일 안) · 쪽 시작(u16, 진행 바이트>>8) · 높이(u16) · 합(u16, RLE 바이트 합)
      자료 = 1비트 글자판(위아래 0 줄·좌우 0 바이트 덧댐, 폭 22 B) RLE(0 아닌 바이트 그대로 · (0, 개수) · 끝 (0, 0)).
  · 음성 읽기 감싸개: 0.BIN 상수 0x0603AAF4(원래 LoadFile 0x0600B6D6 — 음성 V 파일 칸 A 0x20250000 · 칸 B 0x20270000 에서만 씀) → vload:
      원래 LoadFile(경로, 칸) → 경로가 «WD???/V…» 면 첫 글자 K 로 바꿔 LoadFile(짝 경로, 짝 버퍼 A 0x20220000 / B 0x20228000) · 반환값은 원래 것.
      ★하위 RAM 0x20208700‥0x20230000 은 스테이트 26장(타이틀·메뉴·브리핑·미션·통신 동영상 뒤·결과·세이브) 모두 0 · 0.BIN 에 그 안을 가리키는 상수는 0x20218000(0x200 B 표)뿐.
        혹시 덮여도 VBI 가 머리·합을 검사해 깨진 자료는 안 그림.
  · VBI(0x06009814 상수, PoC 와 같음): PCM 핸들 0 STAT 4 → (길이, 열쇠, 진행 = 핸들+0x70) 로 버퍼 A·B 의 항목 중 «쪽 시작 ≤ 진행» 마지막 것
      → 쪽이 바뀌면 RLE 풀고(합 검사) 테두리 계산해 2비트 그림(실행 자리) → 매 프레임 VDP1 VRAM 4비트로(PoC 와 같음). 화자 쪽 위/아래도 PoC 그대로.
  · 실행 자리 RUN 0x060FC000‥0x060FE000(부팅 init 이 0.BIN 보관 자리에서 풀어 놓음 — PoC 3차 방식).
"""
import importlib.util, struct
import hook as H                                                       # PoC 의 상수·expand/walk 등 재사용
A = H.A

LOADFILE = 0x0600B6D6; VLOAD_LIT = 0x0603AAF4
SERVER = 0x060629CC                                                    # GFS_NwExecServer(r4 = int*) — 메인 루프 0x0600527E 에서 매 프레임
POLL = 0x0600B858                                                      # 읽기 완료 확인(r4 = 요청 비트) → 0 완료(닫음) · FFFF 없음 · 그대로면 진행 중
SLOT_A = 0x20250000
NHANDLE = 4; HSTEP = 0x1D0                                             # SBL PCM 핸들 4개 0x0608B348‥
SRV_LIT = 0x060053C4                                                   # 메인 루프 0x0600527E 의 SERVER 리터럴 → 우리 srv(서버 + 짝 파일 완료 확인)
BUF_A = 0x20220000; BUF_B = 0x20228000; BUFSZ = 0x8000
MAGIC = 0x51564B31                                                      # 'QVK1'
HMAX = 13 * 3 + 2                                                       # 한 쪽 최대 3줄
GW = H.GW
RUN = H.RUN
D_LUT = RUN; D_CMD = D_LUT + 32; VAR = D_CMD + 64; KPATH = VAR + 16; CODE = KPATH + 32
SRVARG = KPATH + 24; PEND = KPATH + 28                                  # 서버 인수(int) · 아직 안 끝난 짝 요청 비트(u16, 0 = 없음)
# VAR: +0 붙였음 깃발 · +4 지금 항목 주소 · +8 높이


def mn():
    """짧은 니모닉 → 16비트"""
    class O: pass
    o = O()
    o.mov = lambda m, n: 0x6003 | n << 8 | m << 4
    o.movi = lambda i, n: 0xE000 | n << 8 | (i & 0xFF)
    o.ldl = lambda m, n: 0x6002 | n << 8 | m << 4
    o.stl = lambda m, n: 0x2002 | n << 8 | m << 4
    o.stb = lambda m, n: 0x2000 | n << 8 | m << 4
    o.ldbp = lambda m, n: 0x6004 | n << 8 | m << 4
    o.ldld = lambda d, m, n: 0x5000 | n << 8 | m << 4 | d // 4
    o.stld = lambda m, d, n: 0x1000 | n << 8 | m << 4 | d // 4
    o.ldwd0 = lambda d, m: 0x8500 | m << 4 | d // 2
    o.ldbd0 = lambda d, m: 0x8400 | m << 4 | d
    o.add = lambda m, n: 0x300C | n << 8 | m << 4
    o.addi = lambda i, n: 0x7000 | n << 8 | (i & 0xFF)
    o.cmpeq = lambda m, n: 0x3000 | n << 8 | m << 4
    o.cmphs = lambda m, n: 0x3002 | n << 8 | m << 4                     # Rn >= Rm (부호 없음)
    o.cmphi = lambda m, n: 0x3006 | n << 8 | m << 4                     # Rn > Rm
    o.cmpeqi = lambda i: 0x8800 | (i & 0xFF)
    o.tst = lambda m, n: 0x2008 | n << 8 | m << 4
    o.or_ = lambda m, n: 0x200B | n << 8 | m << 4
    o.extub = lambda m, n: 0x600C | n << 8 | m << 4
    o.extuw = lambda m, n: 0x600D | n << 8 | m << 4
    o.shll = lambda n: 0x4000 | n << 8
    o.shlr = lambda n: 0x4001 | n << 8
    o.shll2 = lambda n: 0x4008 | n << 8
    o.shlr2 = lambda n: 0x4009 | n << 8
    o.shll8 = lambda n: 0x4018 | n << 8
    o.dt = lambda n: 0x4010 | n << 8
    o.jsr = lambda n: 0x400B | n << 8
    o.jmp = lambda n: 0x402B | n << 8
    o.push = lambda n: 0x2F06 | n << 4
    o.pop = lambda n: 0x60F6 | n << 8
    o.RTS = 0x000B; o.NOP = 0x0009; o.SPR = 0x4F22; o.LPR = 0x4F26
    return o


def assemble():
    o = mn(); a = A(CODE); W = a.w
    # ── VBI ──
    a.L('vbi'); W(o.SPR, *[o.push(r) for r in range(4, 15)])
    # ★PCM 핸들 4개(간격 0x1D0)를 차례로 — 효과음이 0번을 쓰면 대사는 다른 핸들로 감(2026-10-11 실기 «효과음 겹칠 때 자막 없음»)
    a.ld(4, H.H0); W(o.movi(0, 11), o.movi(NHANDLE, 9))
    a.L('hl'); W(o.ldld(0x34, 4, 0), o.cmpeqi(4)); a.br('bf', 'hn')
    W(o.ldld(8, 4, 12))                                                 # r12 = 길이
    W(o.mov(12, 3), o.shlr2(3), o.shlr(3), o.shll2(3))                  # r3 = 가운데
    W(o.ldld(4, 4, 5), o.add(3, 5), o.ldl(5, 13))                       # r13 = 열쇠
    W(o.mov(4, 1), o.addi(0x70, 1), o.ldl(1, 14))                       # r14 = 진행
    a.ld(6, BUF_A); a.br('bsr', 'scan'); W(o.NOP)
    a.ld(6, BUF_B); a.br('bsr', 'scan'); W(o.NOP)
    W(o.tst(11, 11)); a.br('bf', 'hit')
    a.L('hn'); a.ld(1, HSTEP); W(o.add(1, 4), o.dt(9)); a.br('bf', 'hl')
    a.br('bra', 'off'); W(o.NOP)
    a.L('hit'); a.ld(9, VAR); W(o.ldld(4, 9, 0), o.cmpeq(11, 0)); a.br('bt', 'draw')
    W(o.movi(0, 0), o.stld(0, 4, 9))                                    # 지금 항목 = 없음(실패하면 그대로)
    W(o.ldwd0(12, 11), o.extuw(0, 8))                                   # r8 = 높이
    W(o.tst(8, 8)); a.br('bt', 'off')
    W(o.movi(HMAX, 1), o.cmphi(1, 8)); a.br('bt', 'off')
    W(o.ldwd0(8, 11), o.extuw(0, 0))                                    # 자료 위치
    a.ld(1, BUFSZ); W(o.cmphs(1, 0)); a.br('bt', 'off')
    W(o.mov(10, 1), o.add(0, 1))
    a.ld(2, 'mask'); a.ld(3, 'maskend'); W(o.movi(0, 5))
    a.br('bsr', 'unrle'); W(o.NOP)
    W(o.tst(0, 0)); a.br('bt', 'off')
    W(o.ldwd0(14, 11), o.extuw(0, 0), o.extuw(5, 5), o.cmpeq(5, 0)); a.br('bf', 'off')
    a.ld(9, VAR); W(o.stld(11, 4, 9), o.stld(8, 8, 9))
    W(o.mov(8, 10)); a.ld(8, 'mask'); a.ld(9, 'pix2')
    a.br('bsr', 'dilate'); W(o.NOP)
    a.L('draw')
    a.ld(9, VAR); W(o.ldld(8, 9, 7))                                    # r7 = 높이
    a.ld(1, 'pix2'); a.ld(2, H.TEX)
    W(o.mov(7, 3), o.shll2(3), o.shll(3), o.mov(3, 0), o.shll2(3), o.add(0, 3))   # r3 = 높이 × 40
    a.br('bsr', 'expand'); W(o.NOP)
    a.ld(1, D_LUT); a.ld(2, H.LUT); W(o.movi(8, 3)); a.br('bsr', 'copy'); W(o.NOP)
    a.ld(1, D_CMD); a.ld(2, H.OWN); W(o.movi(16, 3)); a.br('bsr', 'copy'); W(o.NOP)
    a.ld(1, H.OWN); a.ld(0, H.W8 << 8); W(o.or_(7, 0), 0x8115)            # 우리 칸 SIZE
    a.ld(1, H.WIN_TOP); W(0x6010, 0x600C, 0x8800); a.br('bf', 'side')   # 위 창 00 ?
    a.ld(1, H.WIN_BOT); W(0x6010, 0x600C, 0x8800); a.br('bt', 'side')   # 아래 창도 00 이면 아래쪽(미션 밖)
    a.ld(1, H.OWN); W(0xE000 | H.XT, 0x8116, 0xE000 | H.YT, 0x8117)
    a.L('side')
    a.ld(1, H.LA); a.br('bsr', 'ins'); W(o.NOP)
    a.ld(1, H.LB); a.br('bsr', 'ins'); W(o.NOP)
    a.ld(1, VAR); W(0xE001, 0x2102)
    a.br('bra', 'done'); W(o.NOP)
    a.L('off')
    a.ld(1, VAR); W(0x6012, 0x2008); a.br('bt', 'done')
    W(0xE000, 0x2102)
    a.ld(1, H.LA); a.br('bsr', 'unins'); W(o.NOP)
    a.ld(1, H.LB); a.br('bsr', 'unins'); W(o.NOP)
    a.L('done'); W(*[o.pop(r) for r in range(14, 3, -1)], o.LPR)
    a.ld(1, H.ORIG); W(o.jmp(1), o.NOP)
    # scan(r6 버퍼) — r12 길이 · r13 열쇠 · r14 진행 → 찾으면 r11 항목 · r10 버퍼. r0·r1·r7 씀
    a.L('scan'); W(o.ldl(6, 0)); a.ld(1, MAGIC); W(o.cmpeq(1, 0)); a.br('bf', 'sret')
    W(o.ldld(4, 6, 7), o.mov(6, 1), o.addi(8, 1))
    a.ld(0, 0x400); W(o.cmphs(0, 7)); a.br('bt', 'sret')                 # 항목 수 1024 넘으면 깨진 것
    a.L('sl'); W(o.tst(7, 7)); a.br('bt', 'sret')
    W(o.ldl(1, 0), o.cmpeq(12, 0)); a.br('bf', 'sn')
    W(o.ldld(4, 1, 0), o.cmpeq(13, 0)); a.br('bf', 'sn')
    W(o.ldwd0(10, 1), o.extuw(0, 0), o.shll8(0), o.cmphs(0, 14)); a.br('bf', 'sn')
    W(o.mov(1, 11), o.mov(6, 10))
    a.L('sn'); W(o.addi(16, 1)); a.br('bra', 'sl'); W(o.dt(7))
    a.L('sret'); W(o.RTS, o.NOP)
    # unrle(r1 원본, r2 출력, r3 출력 끝, r5 합 0) → r0 1 성공 / 0 실패(출력 넘침). r6 씀
    a.L('unrle')
    a.L('ul'); W(o.ldbp(1, 0), o.extub(0, 0), o.add(0, 5), o.tst(0, 0)); a.br('bf', 'ulit')
    W(o.ldbp(1, 0), o.extub(0, 0), o.add(0, 5), o.tst(0, 0)); a.br('bt', 'uok')
    W(o.mov(0, 6), o.movi(0, 0))
    a.L('uz'); W(o.cmphs(3, 2)); a.br('bt', 'ubad')
    W(o.stb(0, 2), o.addi(1, 2), o.dt(6)); a.br('bf', 'uz')
    a.br('bra', 'ul'); W(o.NOP)
    a.L('ulit'); W(o.cmphs(3, 2)); a.br('bt', 'ubad')
    W(o.stb(0, 2)); a.br('bra', 'ul'); W(o.addi(1, 2))
    a.L('uok'); W(o.RTS, o.movi(1, 0))
    a.L('ubad'); W(o.RTS, o.movi(0, 0))
    # dilate(r8 글자판, r9 2비트 출력, r10 높이) — init_code 의 테두리 계산 그대로(부팅 init 대신 VBI 에서)
    a.L('dilate'); W(o.SPR, 0x7816)
    a.L('row'); W(0x7801, 0xEB14)
    a.L('byte')
    a.br('bsr', 'vsum'); W(0xE500); W(0x6C03)
    a.br('bsr', 'vsum'); W(0xE5FF); W(0x6D03)
    a.br('bsr', 'vsum'); W(0xE501); W(0x6403)
    W(0x60C3, 0x4000, 0x20CB)
    W(0x6343, 0x4309, 0x4309, 0x4309, 0x4301, 0x203B)
    W(0x63C3, 0x4301, 0x203B)
    W(0x63D3, 0x4318, 0x4301, 0x203B)
    W(0xC9FF, 0x6603)
    W(0x6080, 0x600C, 0x6503)
    W(0x6757, 0x2679)
    W(0xE300, 0xE708)
    a.L('bit'); W(0x4308, 0x6053, 0xC880); a.br('bt', 'b1'); W(0x7302)
    a.L('b1'); W(0x6063, 0xC880); a.br('bt', 'b2'); W(0x7301)
    a.L('b2'); W(0x4500, 0x4600, 0x4710); a.br('bf', 'bit')
    W(0x2931, 0x7902)
    W(0x7801, 0x4B10); a.br('bf', 'byte')
    W(0x7801)
    W(0x4A10); a.br('bf', 'row')
    W(o.LPR, o.RTS, o.NOP)
    a.L('vsum'); W(0x6183, 0x315C, 0x6010, 0x600C)
    W(0x6213, 0x72EA, 0x6220, 0x622C, 0x202B)
    W(0x6213, 0x7216, 0x6220, 0x622C, 0x202B)
    W(o.RTS, o.NOP)
    # copy · expand · walk · ins · unins — PoC 그대로
    a.L('copy'); a.L('cl'); W(0x6016, 0x2202, 0x7204, 0x4310); a.br('bf', 'cl'); W(0x000B, 0x0009)
    a.L('expand'); a.L('el')
    W(0x6514, 0x655C)
    W(0x6053, 0x4009, 0x4009, 0x6603, 0xC903, 0x4609, 0x4608, 0x4608, 0x206B)
    W(0x4018, 0x6403)
    W(0x6053, 0x4009, 0xC903, 0x4008, 0x4008, 0x6603)
    W(0x6053, 0xC903, 0x206B, 0x204B)
    W(0x2201, 0x7202, 0x4310); a.br('bf', 'el'); W(0x000B, 0x0009)
    a.L('walk'); a.ld(3, 1024)
    a.L('wl'); W(0x6011, 0x600D)
    a.ld(2, 0x8000); W(0x2208); a.br('bf', 'wret')
    a.ld(2, 0x5000); W(0x3020); a.br('bf', 'wjp')
    W(0x8511, 0x600D); a.ld(2, H.OWNL); W(0x3020); a.br('bt', 'wret')
    W(0x6011, 0x600D)
    a.L('wjp'); W(0x4019, 0x4009, 0x4009, 0xC903, 0x8801); a.br('bf', 'wnx')
    W(0x8511, 0x600D, 0x4008, 0x4000); a.ld(2, H.LIST); W(0x302C, 0x6103); a.br('bra', 'wdt'); W(0x0009)
    a.L('wnx'); W(0x7120)
    a.L('wdt'); W(0x4310); a.br('bf', 'wl')
    W(0xE100)
    a.L('wret'); W(0x000B, 0x0009)
    a.L('ins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'iret')
    W(0x6011, 0x600D); a.ld(2, 0x8000); W(0x2208); a.br('bt', 'iret')
    a.ld(0, 0x5000); W(0x2101); a.ld(0, H.OWNL); W(0x8111)
    a.L('iret'); W(0x4F26, 0x000B, 0x0009)
    a.L('unins'); W(0x4F22); a.br('bsr', 'walk'); W(0x0009)
    W(0x2118); a.br('bt', 'uret')
    W(0x6011, 0x600D); a.ld(2, 0x5000); W(0x3020); a.br('bf', 'uret')
    a.ld(0, 0x8000); W(0x2101)
    a.L('uret'); W(0x4F26, 0x000B, 0x0009)
    # ── vload(r4 경로, r5 칸) — 원래 LoadFile 뒤 짝 파일 ── (리터럴 풀 1 KB 거리 때문에 따로 어셈블해 뒤에 붙임)
    code1 = a.build(); lab1 = dict(a.lab)
    base2 = CODE + len(code1); base2 += -base2 % 4
    a = A(base2); W = a.w
    a.L('vload'); W(o.SPR, o.push(8), o.push(9), o.push(10), o.push(11), o.push(12))
    W(o.mov(4, 8), o.mov(5, 9))
    a.ld(0, LOADFILE); W(o.jsr(0), o.NOP, o.mov(0, 10))
    W(o.mov(8, 1), 0x6010, o.cmpeqi(0x57)); a.br('bf', 'vout')           # 'W'
    W(o.ldbd0(1, 1), o.cmpeqi(0x44)); a.br('bf', 'vout')                 # 'D'
    W(o.ldbd0(6, 1), o.cmpeqi(0x56)); a.br('bf', 'vout')                 # 'V'
    a.ld(2, KPATH); W(o.movi(22, 3))
    a.L('vc'); W(o.ldbp(1, 0), o.stb(0, 2), o.addi(1, 2), o.tst(0, 0)); a.br('bt', 'vce')
    W(o.dt(3)); a.br('bf', 'vc')
    a.br('bra', 'vout'); W(o.NOP)                                      # 너무 긴 경로 — 건너뜀
    a.L('vce'); a.ld(2, KPATH)                                         # «WDE00/VE001.B» → «WDE00/KE00.B»(같은 폴더, 16개 묶음)
    W(o.ldbd0(11, 2), o.cmpeqi(0x2E)); a.br('bf', 'vout')               # [11] == '.' (V????.B 꼴만)
    W(o.movi(0x4B, 0), 0x8026)                                         # mov.b r0,@(6,r2) — 'K'
    W(o.movi(0x2E, 0), 0x802A, o.movi(0x42, 0), 0x802B, o.movi(0, 0), 0x802C)   # [10]='.' [11]='B' [12]=0
    a.ld(5, BUF_B); a.ld(1, SLOT_A); W(o.cmpeq(9, 1)); a.br('bf', 'vb')
    a.ld(5, BUF_A)
    a.L('vb'); W(o.mov(5, 9))                                          # r9 = 짝 버퍼
    # 앞 짝 요청이 아직 안 끝났으면(드묾) 그것만 끝날 때까지 기다림 — 요청 비트를 잃으면 파일이 안 닫혀 다음 폴더 읽기가 막힘
    a.ld(12, 3000000)
    a.L('vw'); a.ld(1, PEND); W(0x6011, o.extuw(0, 11), o.tst(11, 11)); a.br('bt', 'vgo')
    a.ld(4, SRVARG); a.ld(0, SERVER); W(o.jsr(0), o.NOP)
    a.br('bsr', 'kpoll'); W(o.NOP)
    W(o.dt(12)); a.br('bf', 'vw')
    a.L('vgo'); W(o.movi(0, 0), o.stl(0, 9))                            # 머리 지움(읽다 실패해도 안 씀)
    a.ld(1, VAR); W(o.stld(0, 4, 1))                                    # 지금 항목 = 없음
    a.ld(4, KPATH); a.ld(0, LOADFILE); W(o.jsr(0), o.mov(9, 5))
    # ★LoadFile 은 비동기 — 기다리지 않고 요청 비트만 적어 둠. 완료 확인은 메인 루프 서버 호출 자리(srv)에서 매 프레임(2026-10-11 실기 «자막 나올 때 끊김»)
    a.ld(1, VAR); W(0x8116)                                            # mov.w r0,@(12,r1) — 진단: LoadFile 반환
    W(o.extuw(0, 11)); a.ld(1, 0xFFFF); W(o.cmpeq(1, 11)); a.br('bt', 'vout')
    a.ld(1, PEND); W(0x21B1)                                           # mov.w r11,@r1 — 짝 요청 비트 적어 둠
    a.L('vout'); W(o.mov(10, 0), o.pop(12), o.pop(11), o.pop(10), o.pop(9), o.pop(8), o.LPR, o.RTS, o.NOP)
    # kpoll — PEND 비트 한 번 확인: 0(완료)·FFFF(없음)이면 PEND 지움. r0‥r7 씀
    a.L('kpoll'); W(o.SPR)
    a.ld(1, PEND); W(0x6011, o.extuw(0, 4), o.tst(4, 4)); a.br('bt', 'kpr')
    a.ld(0, POLL); W(o.jsr(0), o.NOP)
    W(o.extuw(0, 0), o.tst(0, 0)); a.br('bt', 'kpd')
    a.ld(1, 0xFFFF); W(o.cmpeq(1, 0)); a.br('bf', 'kpr')
    a.L('kpd'); a.ld(1, VAR); W(0x8117)                                # mov.w r0,@(14,r1) — 진단: 끝 상태(0 = 완료)
    a.ld(1, PEND); W(o.movi(0, 0), 0x2101)                             # PEND = 0
    a.L('kpr'); W(o.LPR, o.RTS, o.NOP)
    # srv(r4) — 메인 루프의 GFS_NwExecServer 호출을 갈음: 원래 서버 + 짝 요청 확인(r8‥r15 안 건드림)
    a.L('srv'); W(o.SPR)
    a.ld(0, SERVER); W(o.jsr(0), o.NOP)
    a.br('bsr', 'kpoll'); W(o.NOP)
    W(o.LPR, o.RTS, o.NOP)
    a.L('end')
    code = code1 + bytes(base2 - CODE - len(code1)) + a.build()
    lab = dict(lab1); lab.update(a.lab)
    pend = CODE + len(code); pend += -pend % 4
    lab['mask'] = pend; lab['maskend'] = pend + (HMAX + 2) * GW
    lab['pix2'] = lab['maskend'] + (-lab['maskend'] % 4)
    lab['runend'] = lab['pix2'] + H.W8 * 2 * HMAX
    return code, lab


def assemble_fix():
    # mask/pix2 는 a.ld 에 라벨 이름으로 넘김 — A 는 같은 어셈블 안 라벨만 앎 → 코드 길이로 주소 정한 뒤 숫자로 다시
    code, lab = _asm(None)
    for _ in range(3):
        c2, l2 = _asm(lab)
        if len(c2) == len(code): return c2, l2
        code, lab = c2, l2
    raise RuntimeError('어셈블 수렴 안 함')


def _asm(prev):
    """prev 라벨(mask·maskend·pix2) 숫자로 넣고 어셈블"""
    import types
    orig = A.ld
    pv = prev or {'mask': 0x060FD000, 'maskend': 0x060FD400, 'pix2': 0x060FD400}
    def ld(s, rn, val):
        if isinstance(val, str) and val in pv: val = pv[val]
        return orig(s, rn, val)
    A.ld = ld
    try:
        return assemble()
    finally:
        A.ld = orig


def run_image():
    code, lab = assemble_fix()
    img = bytearray(CODE - RUN) + code
    img += bytes(-len(img) % 4)
    lut = struct.pack('>16H', 0, 0x8000, 0xFFFF, *([0] * 13))
    cmd = struct.pack('>16H', 0x0000, 0, 0x0088, H.LUTA, H.TEXA, 0, H.X, H.Y, 0, 0, 0, 0, 0, 0, 0, 0) + struct.pack('>16H', 0x8000, *([0] * 15))
    img[D_LUT - RUN:D_LUT - RUN + 32] = lut; img[D_CMD - RUN:D_CMD - RUN + 64] = cmd
    assert lab['runend'] <= H.RUN_END, hex(lab['runend'])
    return bytes(img), lab


def blob(extra=None):
    """→ ({0.BIN 주소: 바이트}, 라벨, RUN 내용) — 부팅 init 은 PoC init_code(작업 목록 = 빈 것)
       extra = (주소, 바이트) — RUN 뒤 같은 RLE 줄기로 함께 풀 것(가타카나 훅 khook, 0x060FD000‥)"""
    img, lab = run_image()
    jobs = RUN + len(img)
    full = img + bytes(12)
    if extra:
        ea, eb = extra; assert ea >= max(RUN + len(full), lab['runend']), hex(ea)
        full += bytes(ea - RUN - len(full)) + eb
        assert RUN + len(full) <= H.INIT_TOP, hex(RUN + len(full))
    cap1 = H.STORE[0][1] - H.STORE[0][0]
    cut = len(full)
    while len(H.rle(full[:cut])) + 2 > cap1: cut -= 4
    s1 = H.rle(full[:cut]) + b'\0\0'; s2 = H.rle(full[cut:]) + b'\0\0'
    ini, _ = H.init_code(0x06000001, jobs)
    src2 = H.STORE[1][0] + len(ini)
    ini, ilab = H.init_code(src2, jobs); assert H.STORE[1][0] + len(ini) == src2
    p2 = ini + s2
    assert H.STORE[1][0] + len(p2) <= H.STORE[1][1], ('보관 자리 넘침', len(p2))
    lab.update(ilab)
    return {H.STORE[0][0]: s1, H.STORE[1][0]: p2}, lab, img


def patch_0bin(d0, parts, lab):
    d = bytearray(H.patch_0bin(d0, parts, lab))
    o = VLOAD_LIT - H.LOAD; assert struct.unpack_from('>I', d, o)[0] == LOADFILE
    struct.pack_into('>I', d, o, lab['vload'])
    o = SRV_LIT - H.LOAD; assert struct.unpack_from('>I', d, o)[0] == SERVER
    struct.pack_into('>I', d, o, lab['srv'])
    return bytes(d)


# ── 짝 자막 파일 ──
def kfile(pages):
    """pages = [(조각 길이, 열쇠, 쪽 시작 진행 바이트, px(높이×160 값 0‥2))] → 파일 바이트(쪽 시작 오름차순으로 정렬해 넣음)"""
    pages = sorted(pages, key=lambda p: (p[0], p[1], p[2]))
    n = len(pages); head = struct.pack('>II', MAGIC, n)
    tab = b''; dat = b''; base = 8 + 16 * n
    for ln, k4, frm, px in pages:
        h = px.shape[0]; assert 0 < h <= HMAX and px.shape[1] == H.W8 * 8
        r = H.rle(H.gpad(px)) + b'\0\0'
        off = base + len(dat); assert off < BUFSZ
        tab += struct.pack('>IIHHHH', ln, k4, off, min(frm >> 8, 0xFFFF), h, sum(r) & 0xFFFF)
        dat += r
    out = head + tab + dat
    assert len(out) <= BUFSZ, ('짝 파일 버퍼 넘침', len(out))
    return out
