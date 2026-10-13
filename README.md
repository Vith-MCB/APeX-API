# APeX-API

<p align="center">
  <img width="819" height="447" alt="apex-api" src="https://github.com/user-attachments/assets/8780d27f-b63d-4baa-a532-265fd201f9d8" />
</p>

Protótipo acadêmico que transforma um recorte das regras de capital do Sistema Financeiro Nacional em validação, cálculo explicável e arquivos conferíveis. O serviço roda na máquina local. A carteira sintética não precisa ser enviada a um terceiro para a demonstração.

Este repositório é um trabalho de conclusão de curso. O objetivo é mostrar o que se ganha, e o que ainda falta, quando uma norma deixa de ser só texto e passa a ser uma função com entrada, status e rastro. A aplicação organiza esse recorte para ser reutilizado por quem envia os fatos da exposição. Ela não substitui o jurídico, o compliance nem o sistema prudencial de uma instituição.

## O que a aplicação faz

Há dois caminhos.

No caminho individual, um JSON descreve o contexto, a operação e os mitigadores. `POST /api/v1/validate/exposure` confere o contrato e os vínculos. `POST /api/v1/calculations/exposure`, no modo `DIDACTIC`, preenche número somente quando a exposição fecha o recorte já implementado: pessoa jurídica não financeira do art. 36 da Resolução BCB nº 229 e, no máximo, um título público federal em reais na abordagem simples da Circular nº 3.809. A contribuição isolada de 8% usa o art. 4º da Resolução CMN nº 4.958 quando o contexto declara que a instituição está no art. 1º dessa resolução.

No caminho de lote, um Parquet no layout `combined_v1` entra por `POST /api/v1/batches`. A API responde `202` e grava o arquivo. Um worker separado lê, valida os vínculos e publica os resultados. Esse layout não traz as declarações do art. 36 nem do título. O lote portanto valida e exporta, e deixa FPR, parcela, RWA e contribuição vazios.

```text
JSON ou Parquet
    -> contrato e normalização
    -> vínculos entre operação e garantia
    -> cálculo didático, só no JSON e só no recorte fechado
    -> Parquet e JSON de saída, no lote
```

## Tecnologias

Python 3.14, FastAPI, Pydantic, PyArrow, DuckDB, SQLite, Uvicorn, pytest e ruff. Os valores monetários circulam como `Decimal`. O DuckDB lê Parquet nos testes de equivalência e no endpoint técnico `/test/duckdb`. O worker percorre o arquivo com PyArrow, em lotes, e o SQLite guarda apenas o estado do job.

## Pastas

| Pasta | Função |
| --- | --- |
| `app/api` | Rotas HTTP |
| `app/schemas` | Contratos de entrada e saída |
| `app/ingestion` | Parquet `combined_v1`, normalização e vínculos |
| `app/domain` | Regras e cálculo do recorte |
| `app/reporting` | Exportação, subconjunto e manifesto |
| `app/worker` | Fila local e publicação da saída |
| `app/infrastructure` | SQLite e diretórios do job |
| `regulations` | Textos oficiais, hashes e fichas em revisão |
| `examples` | Amostras sintéticas |
| `scripts` | Worker, gerador e benchmark |
| `tests` | Testes automatizados |
| `docs` | Arquitetura, contratos e medições |

O detalhe das camadas está em [docs/architecture.md](docs/architecture.md). Os endpoints estão em [docs/api-contracts.md](docs/api-contracts.md).

## Instalação e execução

Os comandos assumem um terminal na raiz do repositório, depois que o ambiente virtual estiver ativo.

1. Clonar o repositório.

```bash
git clone https://github.com/Vith-MCB/APeX-API.git
cd APeX-API
```

2. Criar e ativar o ambiente virtual.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalar as dependências.

```bash
python -m pip install -r requirements.txt
```

4. Iniciar a API, escutando só em localhost.

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Abrir a documentação Swagger em [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

6. Em outro terminal, com o mesmo ambiente ativo, subir o worker. O processo permanece em laço até ser interrompido.

```bash
source .venv/bin/activate
python scripts/run_worker.py
```

7. Gerar um Parquet sintético a partir do exemplo versionado.

```bash
python scripts/generate_synthetic_data.py examples/combined_input.jsonl data/input/combined_v1.parquet
```

8. Validar uma operação individual.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/validate/exposure \
  -H 'Content-Type: application/json' \
  --data-binary @examples/structural_exposure.json
```

O cálculo didático usa outro arquivo:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/calculations/exposure \
  -H 'Content-Type: application/json' \
  --data-binary @examples/didactic_exposure.json
```

9. Enviar o lote. A resposta traz `job_id` e o status `PENDING`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/batches \
  -F "context=<examples/calculation_context.json;type=application/json" \
  -F "file=@data/input/combined_v1.parquet"
```

10. Com o worker no outro terminal, consultar o status, o resumo e baixar um arquivo.

```bash
curl -s http://127.0.0.1:8000/api/v1/batches/JOB_ID
curl -s http://127.0.0.1:8000/api/v1/batches/JOB_ID/summary
curl -s http://127.0.0.1:8000/api/v1/batches/JOB_ID/errors
curl -s -o results.parquet http://127.0.0.1:8000/api/v1/batches/JOB_ID/artifacts/results
```

Troque `JOB_ID` pelo valor recebido no passo 9. Os outros artefatos usam `tranches`, `issues`, `trace`, `summary` e `manifest` no lugar de `results`.

11. Executar os testes e o verificador estático.

```bash
python -m pytest -q
python -m ruff check .
```

Outras chamadas estão em [examples/requests.http](examples/requests.http).

## Funcionalidades atuais

A validação de operações e garantias recusa tipo errado, valor monetário inválido e campo obrigatório ausente. Vínculos incoerentes continuam na resposta, com código próprio: flag de garantia sem a linha correspondente, garantia órfã, operação duplicada e `row_id` repetido.

O cálculo didático identifica o FPR original de 85% no recorte do art. 36 quando a instituição declara os fatos exigidos e a exposição `E`. O saldo contábil (`balance_amount`) permanece distinto dessa exposição. Um título público federal elegível, único, gera a parcela coberta e a parcela descoberta. Garantia fora do recorte, dado faltante, sobreposição ou entrada inválida não recebe FPR zero de colateral. Mais de um mitigador permanece no modelo e não é rateado.

O lote é assíncrono. O worker publica, de uma vez, `results.parquet`, `tranches.parquet`, `issues.parquet`, `trace.parquet`, `summary.json` e `manifest.json`. O manifesto traz o hash da entrada, o hash de cada saída, o modo, a data-base e as regras e fontes visíveis. As regras do catálogo permanecem em `IN_REVIEW` ou `DRAFT`. Nenhuma está `APPROVED`.

No lote sintético atual o resumo traz contagens, saldo contábil das operações e subconjunto prudencial nulo. O endpoint de erros devolve só `code`, `field` e `message`.

## Exemplo numérico didático

O arquivo [examples/didactic_exposure.json](examples/didactic_exposure.json) é o caso coberto por `tests/unit/test_capital.py`. Data-base de 30/09/2026. Exposição declarada de R$ 125.000,00, com base `INSTITUTION_DECLARED_ART5_ART6`. O saldo contábil informado nessa operação é R$ 100.000,00 e não entra na conta do RWA.

A contraparte é pessoa jurídica de direito privado, não financeira, com ativo total de R$ 100.000.000,00 e receita bruta anual de R$ 15.000.000,00. O modo `DIDACTIC` aplica o FPR original de 85% da Resolução BCB nº 229, art. 36 (`BCB229_ART36_PJ_NAO_FINANCEIRA`).

A garantia é um título público federal de valor de mercado R$ 100.000,00. Na abordagem simples da Circular nº 3.809, o valor reconhecido usa o fator 0,80, portanto R$ 80.000,00. A parcela coberta fica em R$ 80.000,00 com FPR 0, porque moeda, indexação e indexador foram declarados coincidentes. A parcela descoberta é R$ 45.000,00 e conserva o FPR de 85%. A regra da parcela é `CIRC3809_SIMPLE_TPF_BRL`.

| Grandeza | Valor |
| --- | --- |
| Exposição declarada | R$ 125.000,00 |
| FPR original | 85% |
| Valor de mercado da garantia | R$ 100.000,00 |
| Valor reconhecido | R$ 80.000,00 |
| Parcela coberta | R$ 80.000,00 com FPR 0 |
| Parcela descoberta | R$ 45.000,00 com FPR 85% |
| RWA antes da mitigação | R$ 106.250,00 |
| RWA depois da mitigação | R$ 38.250,00 |
| Contribuição isolada ao mínimo de PR | R$ 3.060,00 |

A contribuição é 8% do RWA posterior e só aparece porque o exemplo declara `minimum_pr_scope` como `ARTICLE_1_INCLUDED`, no art. 4º da Resolução CMN nº 4.958 (`CMN4958_MINIMUM_PR`). Esses três números são didáticos. O campo `complete_regulatory_coverage` permanece falso. Uma segunda exposição não resolvida, quando exportada junto, fica no arquivo e fora dessa soma.

`REGULATORY` e `VALIDATION_ONLY`, com o mesmo JSON, devolvem a operação sem esses valores.

## Limitações

O sistema é um protótipo acadêmico. As regras do catálogo continuam em revisão (`IN_REVIEW`); a ficha de rateio entre vários mitigadores continua `DRAFT`. O modo `REGULATORY` grava a resposta e deixa os valores prudenciais nulos. O recorte não cobre os demais FPRs da Resolução BCB nº 229, outros instrumentos da Circular nº 3.809, abordagem abrangente, derivativos, SA-CCR, ouro, descasamento de moeda nem a recomposição contábil da exposição. O RWA do subconjunto calculado é o RWA das exposições que fecharam esse recorte. Ele não é o RWA total da instituição, nem o patrimônio de referência, nem um índice de suficiência de capital.

A instituição declara os fatos. A APeX confere a coerência do que foi declarado com o recorte. Ela não audita documento, laudo ou hash de prova. O texto oficial consultado está em `regulations/sources/`, com o hash registrado em `regulations/source_index.yaml`.

## Demonstração do projeto

Deixe a API e o worker em dois terminais, como nos passos 4 e 6.

1. Abra [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) e mostre as rotas de validação, cálculo e lote.
2. Envie `examples/structural_exposure.json` para `/api/v1/validate/exposure`. A resposta lista a operação, a garantia e os problemas estruturais, se houver, sem FPR nem RWA.
3. Envie `examples/didactic_exposure.json` para `/api/v1/calculations/exposure`.
4. Na resposta, mostre `original_fpr`, as duas parcelas, `rwa_before_mitigation`, `rwa_after_mitigation`, `minimum_pr_contribution` e `applied_rules`. Os valores esperados estão na tabela acima.
5. Gere o Parquet de exemplo e envie-o para `/api/v1/batches`, com `examples/calculation_context.json`.
6. Consulte `/api/v1/batches/JOB_ID` até o status sair de `PENDING`. Com o worker ativo, o exemplo pequeno termina em `COMPLETED`.
7. Abra o resumo, o manifesto e o `results.parquet`. O resumo do exemplo tem saldo contábil e `calculated_subset_rwa` nulo. Inconsistências de um arquivo propositalmente inválido aparecem em `/errors`, com o job em `PARTIAL`.

O lote de demonstração não repete os R$ 38.250,00. Esse número pertence ao JSON didático, porque o Parquet `combined_v1` não carrega as declarações usadas no passo 3.

## Desempenho medido

O script `scripts/benchmark.py` gera operações sintéticas e mede a validação estrutural e a exportação do lote. O tempo de gerar o Parquet fica de fora da vazão. Não há cálculo didático nesse experimento. A medição desta máquina, em 13/10/2026, está em [docs/benchmarks.md](docs/benchmarks.md). A tabela usa a mediana de três execuções, exceto 1.000.000 de linhas, que teve uma execução e terminou.

| Linhas | Tempo do lote | Linhas/s | Memória | Entrada | results.parquet |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 0,061 s | 16.264 | 86,3 MiB | 24.032 bytes | 39.932 bytes |
| 10.000 | 0,439 s | 22.767 | 114,2 MiB | 203.990 bytes | 385.853 bytes |
| 50.000 | 2,254 s | 22.184 | 223,0 MiB | 1.016.218 bytes | 2.027.590 bytes |
| 100.000 | 4,394 s | 22.756 | 317,8 MiB | 2.024.396 bytes | 4.031.105 bytes |
| 1.000.000 | 45,016 s | 22.215 | 1.524,7 MiB | 20.175.043 bytes | 37.343.318 bytes |

Para repetir a medição:

```bash
python scripts/benchmark.py --output data/benchmarks/results.json
```

O JSON bruto fica em `data/`, que não é versionado. A suíte `pytest` não executa os volumes de 1.000 linhas ou mais. Ela só confere o mesmo script com um lote pequeno.

## Privacidade

Não commitar `data/`, Parquet gerado, banco SQLite local, segredo ou amostra real de carteira. O `.gitignore` cobre esses caminhos. As fontes oficiais em `regulations/sources/` permanecem no Git porque os testes conferem o SHA-256.
