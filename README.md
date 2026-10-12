# APeX-API

<p align="center">
  <img width="819" height="447" alt="apex-api" src="https://github.com/user-attachments/assets/8780d27f-b63d-4baa-a532-265fd201f9d8" />
</p>

API de alta performance para cálculo de alocação de capital regulamentar (RWACPAD) em conformidade com as diretrizes da Resolução BCB nº 229 do Banco Central.

## Estado atual (Fase 2 — ingestão Parquet)

A API disponibiliza `/`, `/health`, `/test/duckdb`, `/docs`, `/api/v1/info`,
`POST /api/v1/validate/exposure` e `POST /api/v1/validate/parquet`. O Parquet `combined_v1`
é separado em operações, exposições e garantias. O saldo soma apenas as operações.
Nenhuma rota calcula FPR, mitigação, RWA ou contribuição de PR. Jobs e o worker continuam
fora desta fase. Veja o [plano completo](plan.md).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal (com `.venv` ativada): `python -m pytest -q`.

Para gerar um Parquet sintético:

```bash
python scripts/generate_synthetic_data.py examples/combined_input.jsonl data/input/combined_v1.parquet
```

Exemplos de chamadas locais estão em [`examples/requests.http`](examples/requests.http).

**Privacidade:** não commitar `data/`, Parquets, segredos ou amostras reais de carteiras.
