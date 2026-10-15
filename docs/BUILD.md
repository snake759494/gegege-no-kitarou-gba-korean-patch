# 소스에서 빌드

Python 3.13과 `requirements.txt`의 패키지를 준비합니다. 공개 소스는 원본 게임 자료를 포함하지 않으며, 원본 ROM과 폰트를 직접 준비해야 합니다.

1. README의 정확한 일본판 ROM을 저장소 루트에 둡니다. 파일 이름도 README의 이름과 같아야 합니다.
2. [갈무리 공식 저장소](https://github.com/quiple/galmuri/tree/71e1cacf1437a11220307120e63e30bc275312d4/dist)의 `Galmuri9.bdf`, `Galmuri11.bdf`, `Galmuri14.bdf`를 `work/fonts/galmuri/`에 둡니다. 고정 커밋은 `71e1cacf1437a11220307120e63e30bc275312d4`이며 각 파일의 SHA-256은 `data/font_manifest.json`에 있습니다. 폰트는 SIL OFL 1.1을 따릅니다.
3. 다음 명령을 저장소 루트에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -X utf8 tools/rebuild.py
```

`prepare_inputs.py`는 주소·길이 목록을 원본 ROM에 적용해 비공개 원문과 장 이미지의 투명 영역을 복원하고, 스프라이트·배경을 추출합니다. `build_patch.py`는 번역과 글자 그림을 반영합니다. `rebuild.py`는 결과가 정식 릴리즈 SHA-256과 일치하는지 검사합니다. 모든 추출물과 폰트는 Git에서 제외되는 `work/` 아래에 생성됩니다.

패치 생성은 별도로 준비한 xdelta3로 실행합니다.

```powershell
./xdelta3.exe -f -e -0 -s "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan).gba" "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Korean).gba" "Gegege_no_Kitarou_GBA_KR.xdelta"
```

xdelta 버전이나 입력 파일 이름에 따라 패치 컨테이너의 바이트는 달라질 수 있습니다. ROM 결과 해시가 재현 기준입니다. 릴리즈 첨부 패치 자체의 해시는 SHA256SUMS.txt를 따릅니다.

선택 검증 도구에는 Windows용 VBA, Unicorn, Capstone이 필요합니다. 에뮬레이터 실행 도구는 특정 VBA 빌드의 메모리 배치와 원래 ROM 해시에 의존합니다. 검증을 재실행할 때는 원본 저장·설정을 별도로 보존하고, 종료 시 VBA를 닫아야 합니다. 일반 빌드에는 에뮬레이터가 필요하지 않습니다.
