# Contratos HTTP

Consultar §8 do [plan.md](../plan.md) para o contrato alvo completo.

## Rotas implementadas

- `GET /api/v1/info`: versão, modos reconhecidos pelo contrato e operação offline.
- `POST /api/v1/validate/exposure`: valida contexto, operação e mitigadores em JSON.
- `POST /api/v1/validate/parquet`: lê um Parquet `combined_v1` e devolve contagens, saldo das
  operações, vínculos e problemas estruturais.

A validação individual preserva IDs como texto e exige valores monetários como strings
decimais finitas e não negativas. Inconsistências de tipo ou campos obrigatórios retornam
`422` no formato `{code, message, details, correlation_id}`. Inconsistências estruturais já
interpretáveis, como `has_guarantee` sem mitigadores ou um vínculo para outra operação,
retornam `200` com `issues`.

No Parquet, arquivo inválido ou schema divergente retorna `400`. Arquivo acima do limite
retorna `413`. Uma operação com duas garantias produz uma exposição e dois mitigadores, e o
saldo não é repetido nas linhas de garantia.

O relatório sempre contém `regulatory_calculation: false`. Ele não contém FPR, RWA nem
contribuição de PR.

- `POST /api/v1/batches`: recebe o Parquet, grava `PENDING` e responde `202`.
- `GET /api/v1/batches/{job_id}`: status persistido.
- `GET /api/v1/batches/{job_id}/summary`: contagens e saldo depois da publicação.
- `GET /api/v1/batches/{job_id}/errors`: issues paginadas.
- `GET /api/v1/batches/{job_id}/artifacts/{kind}`: somente `issues`, `summary` e `manifest`.
- `POST /api/v1/batches/{job_id}/cancel`: cancelamento cooperativo.
- `DELETE /api/v1/batches/{job_id}`: remove um job que não está em execução.

O worker publica a saída só depois de gravar os três artefatos. Um job interrompido não
transforma arquivo temporário em resultado. Issues de linha terminam em `PARTIAL`. O summary
traz `complete_regulatory_coverage` falso e não traz RWA.

Catálogo HTTP de regras e cálculo individual continuam indisponíveis.
