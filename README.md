# APeX-API

<p align="center">
  <img width="819" height="447" alt="apex-api" src="https://github.com/user-attachments/assets/8780d27f-b63d-4baa-a532-265fd201f9d8" />
</p>

API de alta performance para cálculo de alocação de capital regulamentar (RWACPAD) em conformidade com as diretrizes da Resolução BCB nº 229 do Banco Central.

## Estado atual (Fase 8 — exportação do subconjunto)

A API disponibiliza a validação JSON, a validação Parquet e o lote em
`POST /api/v1/batches`. O lote responde `202` e só é processado pelo worker:

```bash
python scripts/run_worker.py
```

O worker grava `results.parquet`, `tranches.parquet`, `issues.parquet`,
`trace.parquet`, `summary.json` e `manifest.json`. O layout `combined_v1` não
carrega as declarações do recorte, então essas linhas saem sem FPR, parcela,
RWA nem contribuição, e o subconjunto agregado fica vazio.

`POST /api/v1/calculations/exposure` demonstra, no modo `DIDACTIC`, o FPR original, as
parcelas, o RWA antes/depois e a contribuição isolada de 8% ao mínimo de PR para o recorte
implementado. Uma exposição de R$ 125.000,00 com colateral de R$ 100.000,00 fecha o
subconjunto em RWA de R$ 38.250,00 e contribuição de R$ 3.060,00. Exposição pendente
permanece no arquivo e fica fora dessa soma. As regras permanecem `IN_REVIEW`;
`REGULATORY` e `VALIDATION_ONLY` não publicam números. O resultado não representa o
RWA total nem o requerimento de PR da instituição. Veja o [plano completo](plan.md).

O título público federal só recebe o tratamento didático quando a instituição
declara o escopo `RWA_CPAD`, a eleição e o uso uniforme da Abordagem Simples,
a ausência de SA-CCR, derivativo de balcão e vedação supervisória. Moeda
nominal, moeda de indexação e indexador financeiro são comparados separadamente;
`NONE` declara ausência de indexação. A marcação deve usar a data-base ou o dia
útil anterior expressamente declarado pela instituição.

A eleição da Abordagem Simples deve ocorrer entre o início e o fim declarados
do exercício social e produz efeitos desde o primeiro dia desse exercício.
Mitigações pendentes ou fora do recorte mostram somente o RWA original
didático; RWA depois, diferença e contribuição de PR ficam vazios. A flag de
garantia, a lista e os vínculos são conferidos antes da alocação.

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
