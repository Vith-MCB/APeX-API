# Arquitetura

A APeX-API é um serviço HTTP local. A pasta `data/` guarda entrada, trabalho e
saída de cada lote. O SQLite guarda só o estado do job.

## Camadas

- `app/api`: rotas FastAPI. Recebe JSON ou Parquet, devolve status e arquivos.
- `app/schemas`: contratos Pydantic. Campo desconhecido é recusado.
- `app/ingestion`: leitura de Parquet em lotes, normalização do `combined_v1` e
  vínculos entre operação e garantia.
- `app/domain`: FPR didático do art. 36, elegibilidade de um título público
  federal, parcelas, RWA e contribuição isolada de 8%.
- `app/reporting`: linhas exportadas, subconjunto calculado, manifesto e fontes.
- `app/worker`: reserva um job, processa e publica a pasta de saída.
- `app/infrastructure`: SQLite, diretórios do job e publicação por `replace`.
- `regulations`: textos oficiais, hashes e fichas em revisão.

## Fluxo do lote

1. `POST /api/v1/batches` grava o upload e cria um job `PENDING`.
2. `python scripts/run_worker.py` reserva o job e lê o Parquet em lotes.
3. A normalização separa operações e garantias. A validação aponta órfãs,
   duplicatas e flag de garantia incoerente.
4. O worker grava `results.parquet`, `tranches.parquet`, `issues.parquet`,
   `trace.parquet`, `summary.json` e `manifest.json` numa pasta de trabalho.
5. A pasta só substitui a saída publicada quando esses arquivos já existem.
   Cancelamento ou heartbeat vencido descarta o trabalho e não publica.

O `combined_v1` não traz as declarações do recorte. Por isso o lote não chama
o cálculo didático. Esse cálculo existe em `POST /api/v1/calculations/exposure`,
no modo `DIDACTIC`, para uma exposição por vez.

DuckDB confirma somas decimais nos testes. O worker grava Parquet com PyArrow.
