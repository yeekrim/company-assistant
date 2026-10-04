# SQL 하네스 실험

"큰 데이터는 모델에 넘기지 말고 코드/DB로 처리한다"는 원칙(에이전트 = 모델 + 하네스)을 company-assistant에 적용할 수 있는지 확인하는 실험.
**앱 코드(`backend/app`)는 수정하지 않는다.** 앱의 청킹·임베딩·프롬프트 함수는 import해서 그대로 재사용한다.

## 비교 방식

| 이름 | 의미 | 처리 |
|---|---|---|
| `current` | 지금 앱 | PDF → 텍스트 청킹(표도 펼쳐서 500자씩) → Top-10 검색 → LLM 1회 |
| `kaizen-mae` (改善前) | 개선 전 | 본문 + 표 전체를 JSON으로 프롬프트에 넣고 LLM이 직접 계산 |
| `kaizen-go` (改善後) | 개선 후 | 표 → 읽기 전용 DuckDB, LLM은 스키마만 보고 `run_sql` / `search_documents` 도구 호출 |

kaizen-go의 벡터 인덱스에는 표 행을 넣지 않고 본문 + 표 요약 한 줄만 넣는다 (아래 발견 2 참고).

## 실행

```bash
cd experiments/sql_harness
../../backend/venv/bin/pip install -r requirements.txt   # duckdb, reportlab
../../backend/venv/bin/python make_data.py               # 가짜 PDF/정답 CSV 생성
../../backend/venv/bin/python run_bench.py               # 전체 실행 → results/<시각>/summary.md
../../backend/venv/bin/python run_bench.py --variants kaizen-go --only c01,c06
../../backend/venv/bin/python run_bench.py --model openai/gpt-oss-20b
```

`backend/.env`의 `NVIDIA_API_KEY`를 사용한다. Docker(Postgres/Chroma)는 필요 없다 (인메모리 Chroma 사용).

## 파일

- `make_data.py` — 규정 본문 + 경비 내역 500행 + 연차 현황 200행 PDF 생성 (seed 고정)
- `questions.py` — 계산형 16개(정답은 CSV에 SQL로 계산) + 서술형 4개
- `tables.py` — PDF 표를 구조 그대로 추출 (페이지 넘어가는 표 병합, 숫자/날짜 타입 변환)
- `variants/` — 세 방식 구현
- `run_bench.py` — 실행·채점·요약

## 결과 (2026-10-04, `nvidia/nemotron-3-super-120b-a12b`, thinking off)

| 방식 | 계산형 정답 | 서술형 정답 | 응답시간 p50 | 평균 입력 토큰 |
|---|---|---|---|---|
| current | 1/16 | 2/4 | 0.4s | 4,044 |
| kaizen-mae | 2/16 | 4/4 | 0.3s | 61,083 |
| kaizen-go | 16/16 ¹ | 4/4 | 0.8s | 2,918 |

¹ c10은 첫 실행에서 NVIDIA API 일시 오류(502)가 나서 재실행한 결과.

## 발견

1. **계산 정확도**: 표를 모델이 직접 계산하면 데이터를 전부 줘도(kaizen-mae) 거의 틀린다. SQL로 계산하면 전부 맞는다.
2. **현재 앱의 검색 오염**: 표가 큰 문서는 청크 대부분이 표 행이 되어(214개 중 212개), "식대 상한" 같은 규정 질문에서 규정 본문 청크가 Top-10에 들지 못한다.
3. **속도**: 이 조건에선 세 방식 모두 1~2초 이내라 "1분 → 몇 초" 같은 속도 차이는 재현되지 않았다.
   kaizen-mae가 6만 토큰인데도 빠른 건 같은 프롬프트 앞부분이 반복되어 API 쪽 캐시가 맞았을 가능성이 크다.
   데이터가 바뀌는 실제 환경이나 추론 모드에선 차이가 커질 수 있어 별도 측정이 필요하다.
4. 앱이 쓰던 `meta/llama-3.1-70b-instruct`는 NVIDIA NIM에서 2026-08-26 지원 종료(410 Gone) → 앱 모델을 nemotron으로 교체함.
