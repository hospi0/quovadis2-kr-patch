# -*- coding: utf-8 -*-
r"""트랙 1 에 새 폴더·파일 덧붙이기(2026-10-11, 미션 자막 «짝 자막 파일» KD???/V????.B 용).
  · 원래 파일 자리는 그대로(제자리 바꿔 넣기도 같이 — 같은 섹터 수 안), 새 폴더·파일은 «트랙 1 끝 150 섹터(포스트갭) 앞»에 끼우고 포스트갭 150 을 다시 붙임.
  · 고치는 것: 루트 디렉터리 2번째 섹터 끝에 새 폴더 기록(SBL GFS 는 이름 순서 안 따짐 — 줄 세우기 없이 덧붙임) · 경로표 L(18)·M(19) 끝에 덧붙임 + PVD 경로표 크기 ·
    PVD 볼륨 크기(원래 값 = 트랙 1 + 트랙 2 전체 섹터 → 늘린 만큼 더함).
  · cue 는 트랙마다 FILE 따로 → 트랙 1 bin 만 커지고 cue 는 그대로.
  build(dst, 장, files={'/0.BIN': bytes}, dirs={'KDE00': {'VE001.B': bytes, ...}})
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import disc, iso

POSTGAP = 150


def _sec(f, n):
    f.seek(n * 2352 + 16); return bytearray(f.read(2048))


def _rec(name, lba, size, flags, date):
    n = name.encode('ascii'); ln = 33 + len(n); ln += ln & 1
    r = bytearray(ln); r[0] = ln
    struct.pack_into('<I', r, 2, lba); struct.pack_into('>I', r, 6, lba)
    struct.pack_into('<I', r, 10, size); struct.pack_into('>I', r, 14, size)
    r[18:25] = date; r[25] = flags
    struct.pack_into('<H', r, 28, 1); struct.pack_into('>H', r, 30, 1)
    r[32] = len(n); r[33:33 + len(n)] = n
    return bytes(r)


def _dirsecs(recs):
    """기록들을 섹터 경계 넘지 않게 → 바이트(2048 배수)"""
    out = bytearray(); cur = bytearray()
    for r in recs:
        if len(cur) + len(r) > 2048: out += cur.ljust(2048, b'\0'); cur = bytearray()
        cur += r
    out += cur.ljust(2048, b'\0')
    return bytes(out)


def build(dst, disk, files=None, dirs=None, log=print, into=None):
    files = files or {}; dirs = dirs or {}; moved = []
    src = disc.BIN % (disk, disk)
    recs = {n: (l, s) for n, l, s in disc.files(disk)}
    nsec = os.path.getsize(src) // 2352
    with open(src, 'rb') as f:
        for k in range(nsec - POSTGAP, nsec): assert not any(_sec(f, k)), ('포스트갭 아님', k)
        pvd = _sec(f, 16); assert pvd[1:6] == b'CD001'
        vol = struct.unpack_from('<I', pvd, 80)[0]; pts = struct.unpack_from('<I', pvd, 132)[0]
        ptl = struct.unpack_from('<I', pvd, 140)[0]; ptm = struct.unpack_from('>I', pvd, 148)[0]
        root = pvd[156:190]; rlba = struct.unpack_from('<I', root, 2)[0]; rsize = struct.unpack_from('<I', root, 10)[0]
        date = bytes(root[18:25])
        rs = [_sec(f, rlba + k) for k in range(rsize // 2048)]
        L = _sec(f, ptl); M = _sec(f, ptm)
    # 새 자리 배치
    at = nsec - POSTGAP
    newsec = {}                                                         # lba → 2048 바이트
    droot = []                                                          # 루트에 넣을 (이름, lba, 크기)
    for dn in sorted(dirs):
        fl = dirs[dn]; names = sorted(fl)
        # 디렉터리 크기 먼저(기록 길이로) — 자기 lba 는 나중에 채워도 길이 같음
        tmp = [_rec('\0', 0, 0, 2, date), _rec('\1', 0, 0, 2, date)] + [_rec(n + ';1', 0, 0, 0, date) for n in names]
        dsz = len(_dirsecs(tmp)); dlba = at; at += dsz // 2048
        flba = {}
        for n in names:
            flba[n] = at; at += (len(fl[n]) + 2047) // 2048
        rr = [_rec('\0', dlba, dsz, 2, date), _rec('\1', rlba, rsize, 2, date)] + [_rec(n + ';1', flba[n], len(fl[n]), 0, date) for n in names]
        db = _dirsecs(rr); assert len(db) == dsz
        for k in range(dsz // 2048): newsec[dlba + k] = db[k * 2048:(k + 1) * 2048]
        for n in names:
            d = fl[n]
            for k in range((len(d) + 2047) // 2048): newsec[flba[n] + k] = d[k * 2048:(k + 1) * 2048].ljust(2048, b'\0')
        droot.append((dn, dlba, dsz))
    # ★기존 폴더에 파일 더하기(into): 폴더 기록을 통째로 새로 써서 트랙 끝으로 옮기고 루트 기록·경로표·«.» 기록의 LBA·크기 고침
    #   (2026-10-11 — 새 폴더는 게임 경로 함수가 «다른 읽기 진행 중이면 새 폴더 안 불러옴» 때문에 실패 → 음성과 같은 폴더에)
    with open(src, 'rb') as f:
        for dn in sorted(into or {}):
            loc = None
            for k, sec in enumerate(rs):
                p = 0
                while p < 2048 and sec[p]:
                    ln = sec[p]; nm = bytes(sec[p + 33:p + 33 + sec[p + 32]])
                    if nm == dn.encode('ascii'): loc = (k, p)
                    p += ln
            assert loc, ('루트에 폴더 없음', dn)
            k, p = loc; olba = struct.unpack_from('<I', rs[k], p + 2)[0]; osz = struct.unpack_from('<I', rs[k], p + 10)[0]
            old = b''.join(bytes(_sec(f, olba + j)) for j in range(osz // 2048))
            ents = []; q = 0
            while q < len(old):
                ln = old[q]
                if ln == 0: q = (q // 2048 + 1) * 2048; continue
                nm = old[q + 33:q + 33 + old[q + 32]]
                if nm not in (b'\0', b'\1'):
                    ents.append((nm.decode('latin1'), struct.unpack_from('<I', old, q + 2)[0], struct.unpack_from('<I', old, q + 10)[0], old[q + 25]))
                q += ln
            fl = into[dn]; have = {e[0].split(';')[0] for e in ents}
            assert not (set(fl) & have), ('이미 있는 이름', dn, sorted(set(fl) & have)[:3])
            tmp = [_rec('\0', 0, 0, 2, date), _rec('\1', 0, 0, 2, date)] + [_rec(e[0], 0, 0, e[3], date) for e in ents] + [_rec(n + ';1', 0, 0, 0, date) for n in fl]
            dsz = len(_dirsecs(tmp)); dlba = at; at += dsz // 2048
            flba = {}
            for n in sorted(fl):
                flba[n] = at; at += (len(fl[n]) + 2047) // 2048
            allr = sorted([(e[0], e[1], e[2], e[3]) for e in ents] + [(n + ';1', flba[n], len(fl[n]), 0) for n in fl], key=lambda e: e[0])
            rr = [_rec('\0', dlba, dsz, 2, date), _rec('\1', rlba, rsize, 2, date)] + [_rec(n, l, s, fg, date) for n, l, s, fg in allr]
            db = _dirsecs(rr); assert len(db) == dsz
            for j in range(dsz // 2048): newsec[dlba + j] = db[j * 2048:(j + 1) * 2048]
            for n in fl:
                d = fl[n]
                for j in range((len(d) + 2047) // 2048): newsec[flba[n] + j] = d[j * 2048:(j + 1) * 2048].ljust(2048, b'\0')
            struct.pack_into('<I', rs[k], p + 2, dlba); struct.pack_into('>I', rs[k], p + 6, dlba)
            struct.pack_into('<I', rs[k], p + 10, dsz); struct.pack_into('>I', rs[k], p + 14, dsz)
            for T, end in ((L, '<'), (M, '>')):                          # 경로표 그 폴더 칸
                q = 0
                while q < pts:
                    ln = T[q]
                    if bytes(T[q + 8:q + 8 + ln]) == dn.encode('ascii'): struct.pack_into(end + 'I', T, q + 2, dlba)
                    q += 8 + ln + (ln & 1)
            moved.append((dn, olba, dlba, len(ents), len(fl)))
    added = at - (nsec - POSTGAP)
    # 루트 디렉터리 마지막 섹터 끝에 덧붙임
    last = rs[-1]; used = 0
    while used < 2048 and last[used]: used += last[used]
    add = b''.join(_rec(dn, l, s, 2, date) for dn, l, s in droot)
    assert used + len(add) <= 2048, ('루트 섹터 넘침', used, len(add))
    last[used:used + len(add)] = add
    # 경로표(부모 = 1)
    lt = bytearray(L[:pts]); mt = bytearray(M[:pts])
    for dn, l, s in droot:
        n = dn.encode('ascii'); pad = len(n) & 1
        lt += bytes([len(n), 0]) + struct.pack('<IH', l, 1) + n + bytes(pad)
        mt += bytes([len(n), 0]) + struct.pack('>IH', l, 1) + n + bytes(pad)
    assert len(lt) <= 2048
    L[:len(lt)] = lt; M[:len(mt)] = mt
    struct.pack_into('<I', pvd, 132, len(lt)); struct.pack_into('>I', pvd, 136, len(lt))
    struct.pack_into('<I', pvd, 80, vol + added); struct.pack_into('>I', pvd, 84, vol + added)
    meta = {16: pvd, ptl: L, ptm: M}
    for k, sec in enumerate(rs): meta[rlba + k] = sec
    # 제자리 바꿔 넣을 파일
    rep = {}
    for name, data in files.items():
        lba, size = recs[name]
        assert len(data) == size, ('크기 다름', name, len(data), size)
        for k in range((size + 2047) // 2048): rep[lba + k] = data[k * 2048:(k + 1) * 2048].ljust(2048, b'\0')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, 'rb') as i, open(dst, 'wb') as o:
        CH = 4096
        for b0 in range(0, nsec - POSTGAP, CH):
            n = min(CH, nsec - POSTGAP - b0); buf = bytearray(i.read(n * 2352))
            for k in range(b0, b0 + n):
                d = meta.get(k, rep.get(k))
                if d is not None: buf[(k - b0) * 2352:(k - b0 + 1) * 2352] = iso.sector(k, bytes(d))
            o.write(buf)
        for k in range(nsec - POSTGAP, at): o.write(iso.sector(k, newsec[k]))
        for k in range(at, at + POSTGAP): o.write(iso.sector(k, bytes(2048)))
    log('트랙 1(장 %d): 바꾼 파일 %d · 새 폴더 %d(파일 %d) · 옮긴 폴더 %s · +%d 섹터 → %d 섹터' % (disk, len(files), len(dirs), sum(len(v) for v in dirs.values()), ' '.join('%s(%d+%d)' % (d, a, b) for d, o, n, a, b in moved), added, at + POSTGAP))
    allf = dict(dirs)
    for dn, fl in (into or {}).items(): allf[dn] = fl
    return verify(dst, files, allf)


def verify(dst, files, dirs):
    """되읽기 — gundam disc.files 로 새 이미지를 다시 파싱해 모든 파일 내용 확인"""
    fl = {n: (l, s) for n, l, s in disc._g.files(dst)}
    want = dict(files)
    for dn, d in dirs.items():
        for n, b in d.items(): want['/%s/%s' % (dn, n)] = b
    with open(dst, 'rb') as f:
        for name, data in want.items():
            l, s = fl[name]; assert s == len(data), name
            out = bytearray()
            for k in range((s + 2047) // 2048): f.seek((l + k) * 2352 + 16); out += f.read(2048)
            assert bytes(out[:s]) == data, name
    return len(fl)
