# Contratos HTTP

## Rotas implementadas

- `GET /` e `GET /health`: presença do processo.
- `GET /test/duckdb`: consulta técnica local, sem carteira.
- `GET /api/v1/info`: versão, modos reconhecidos e operação offline.
- `POST /api/v1/validate/exposure`: valida contexto, operação e mitigadores em JSON.
- `POST /api/v1/validate/parquet`: lê um Parquet `combined_v1` e devolve contagens,
  saldo das operações, vínculos e problemas estruturais.
- `POST /api/v1/calculations/exposure`: no modo `DIDACTIC`, publica o recorte já
  implementado. `REGULATORY` e `VALIDATION_ONLY` devolvem a linha sem número prudencial.
- `POST /api/v1/batches`: recebe o Parquet, grava `PENDING` e responde `202`.
- `GET /api/v1/batches/{job_id}`: status persistido.
- `GET /api/v1/batches/{job_id}/summary`: contagens, saldo e subconjunto depois da publicação.
- `GET /api/v1/batches/{job_id}/errors`: issues paginadas, só `code`, `field` e `message`.
- `GET /api/v1/batches/{job_id}/artifacts/{kind}`: `results`, `tranches`, `issues`,
  `trace`, `summary` e `manifest`.
- `POST /api/v1/batches/{job_id}/cancel`: cancelamento cooperativo.
- `DELETE /api/v1/batches/{job_id}`: remove um job que não está em execução.

A validação individual preserva IDs como texto e exige valores monetários como
strings decimais finitas e não negativas. Inconsistências de tipo ou campos
obrigatórios retornam `422` no formato `{code, message, details, correlation_id}`.
Inconsistências estruturais já interpretáveis, como `has_guarantee` sem mitigadores
ou um vínculo para outra operação, retornam `200` com `issues`.

No Parquet, arquivo inválido ou schema divergente retorna `400`. Arquivo acima do
limite retorna `413`. Uma operação com duas garantias produz uma exposição e dois
mitigadores, e o saldo não é repetido nas linhas de garantia.

O relatório de validação contém `regulatory_calculation: false` e não contém FPR,
RWA nem contribuição de PR. O cálculo didático fica no endpoint próprio. O resumo
do lote traz `complete_regulatory_coverage: false`. No `combined_v1` atual,
`calculated_subset_rwa` fica nulo. A chave `rwa_before_mitigation` não entra nesse resumo.

O worker publica a saída só depois de gravar os arquivos. Um job interrompido não
transforma arquivo temporário em resultado. Issues de linha terminam em `PARTIAL`.
