# 쿼바디스2 - 혹성강습 오반 레이 (새턴 JP 2장) 한글화

## 내려받기
- 최신 **v0.8** — [릴리즈](https://github.com/hospi0/quovadis2-kr-patch/releases/latest)에서 `QuoVadis2_KR_v0.8.zip`
- 대상: `QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan)` 2장 (장마다 트랙 2개)
  - 1장 트랙 1 — 원본md5 `913FC7D76B0763DD48616509B3203314` → 패치md5 `561D50456F0EB31715980F7B7D605713`
  - 2장 트랙 1 — 원본md5 `BD284547A5D07C7ED7971DF222AC8E5C` → 패치md5 `F92947F9EAEACCCB05BAD7E8BC147120`
  - 트랙 2(오디오)·cue 는 원본 그대로

## 바뀌는 것
- 미션 중 음성 대사 자막(고정 대사·랜덤 공격/피격 대사, 말하는 사람 쪽 화면 위/아래)
- 이야기 동영상 12개 자막
- 브리핑·막간 글, 메뉴·시스템·전투 HUD 그림 글자, 배경 그림 글자, 옵션
- 병사 소개 51명, 병사·적 이름, 무기·장비 이름(8×8 동적 글자 훅 + 메뉴 16×16 글꼴)
- 타이틀 화면

## 작업 저장소
- 인계·빌드 절차: **`docs/00_이어하기.md`** 부터.
- 번역 TSV: `work/text/voice_ko.tsv`(음성 자막) · `pages_ko.tsv`(브리핑·막간 글) · `ui_ko.tsv`·`gfx2_ko.tsv`(그림 글자) · `bio_ko.tsv`(병사 소개) · `kana_ko.tsv`(이름·무기), 동영상 자막 `work/movie/movie_subs.tsv`
- 빌드 `QV_OUT=work/out_now python tools/build.py` → 배포 묶음 `python tools/make_dist.py`
- ROM·빌드 결과물은 들어 있지 않다.
