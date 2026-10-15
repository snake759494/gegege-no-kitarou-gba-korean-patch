# 게게게의 키타로: 위기일발! 요괴열도 — GBA 한글패치

일본판 **Gegege no Kitarou - Kikiippatsu! Youkai Rettou**용 비공식 한글패치 **v1.0.0 (2026-10-15)**입니다.

[패치 다운로드](https://github.com/snake759494/gegege-no-kitarou-gba-korean-patch/releases/latest) · [빌드](docs/BUILD.md) · [기술 설명](docs/TECHNICAL.md) · [검증](docs/VALIDATION.md) · [권리 안내](RIGHTS.md)

## 적용 방법

1. 직접 준비한 일본판 ROM의 SHA-256을 아래 `source` 값과 비교합니다.
2. 릴리즈에서 `Gegege_no_Kitarou_GBA_KR.xdelta` 하나를 받습니다.
3. xdelta UI에서 패치·원본 ROM·새 출력 파일을 지정해 적용합니다.
4. 결과 해시를 확인하고 새로 부팅합니다. 기존 세이브 스테이트는 옛 코드나 그림을 유지할 수 있습니다.

```powershell
./xdelta3.exe -d -s "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan).gba" "Gegege_no_Kitarou_GBA_KR.xdelta" "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Korean).gba"
Get-FileHash -Algorithm SHA256 "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Korean).gba"
```

| 파일 | 바이트 | SHA-256 |
| --- | ---: | --- |
| source | 16,777,216 | `7c6c4806b637e6326cfc7e242a38fc3d3dcc53abaab9be96b8388f04bf1976cc` |
| output | 17,354,408 | `8fc91da197a79cd2e447c9fe38da12a12f361d4e257ceb1c81d76decfcb73307` |
| patch | 112,952 | `11fc2ed92f5be19bb91e1b3d7c4a627e58c4f41a522f51186796449a77990674` |

패치는 xdelta `-0`으로 생성했습니다. 릴리즈 첨부물은 xdelta 한 개입니다. ROM·추출 게임 이미지·폰트 파일·에뮬레이터·외부 실행파일은 포함하지 않습니다.

## 한글화 내용

- 직접 번역한 대사·메뉴·아이템·설명·도감·시스템 안내.
- 중복 타이틀과 장 제목, 상태·동료·도감 표찰, 간판·효과 글자, 레벨 상승·게임 종료 이미지.
- 본문 갈무리11의 원래 픽셀 사용, 대사 공백은 6픽셀 반각 폭. 작은 안내는 갈무리9, 일부 큰 안내는 갈무리14를 원래 크기로 사용합니다.
- 타이틀과 주요 표찰은 직접 그린 글자 그림을 사용해 원본의 배치·팔레트·분위기에 맞췄습니다.
- 아이템 설명 줄 넘침과 메뉴 글자 정렬·굵기·타이틀 장식 겹침을 수정했습니다.

번역 자료에는 전개 스포일러와 문자열 식별용 원문 키가 포함됩니다. 원문 대사 추출본 전체는 배포하지 않으며, 빌드에 필요한 원문은 제공된 ROM의 주소와 길이로 복원합니다.

## 검증 범위

최종 ROM에서 VBA 장면 50개, 대사 캡처 762개, 조건 분기 CPU 검사 93개를 확인했습니다. 엔딩 두 장면에서 결과·제작진 30구간·완료 저장 선택·새 부팅 EX 해금과 주요 메뉴를 확인했습니다. 표시 중인 대사의 미등록 글리프·가나·한자는 발견되지 않았습니다.

장면 검증에는 에뮬레이터 메모리에 진행 조건을 준비하고 원래 장면 초기화 함수를 호출한 절차가 포함됩니다. **일반 조작으로 이동·전투·수집·모든 분기를 완료한 전체 완주 검증과 실기 검증은 하지 않았습니다.** 자세한 방법과 한계는 [검증 문서](docs/VALIDATION.md)를 확인하세요.

문제 제보에는 ROM 해시, 진행 위치, 재현 순서와 스크린샷을 첨부해 주세요.
