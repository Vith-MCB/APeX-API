# Atributos de contrato exigidos pelo primeiro recorte

- Status: `IN_REVIEW`
- Data-base: `2026-09-30`
- Regras relacionadas: `BCB229_ART36_PJ_NAO_FINANCEIRA` e
  `CIRC3809_SIMPLE_TPF_BRL`
- Matriz normativa:
  `regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml`

Este documento descreve campos para uma fase futura. Ele não altera os schemas
atuais, não aprova regras e não habilita cálculo regulatório.

## Duas responsabilidades

A instituição financeira declara fatos que já atestou. Isso inclui veracidade
cadastral, conformidade documental, requisitos jurídicos do art. 2º, § 1º, da
Circular nº 3.809 e elegibilidade prudencial previamente verificada por ela. A
API recebe essas declarações em campos estruturados. Não recebe documentos,
pareceres nem hashes de comprovação, e não apresenta a declaração como
verificação independente da APeX.

O motor avalia apenas o que pode conferir sem auditoria:

- presença, tipo e vocabulário dos campos;
- limites quantitativos e datas;
- moedas, indexadores e vencimentos;
- vínculo entre operação, exposição e garantias;
- contagem de mitigadores aplicável ao primeiro tratamento.

`DECLARED` significa declaração da instituição. `UNKNOWN` torna o campo
insuficiente. `NOT_MET` indica requisito objetivo não atendido. `VERIFIED` não
é usado como carimbo de auditoria da APeX.

## Contexto declarado pela instituição

- `prudential_scope_status`: a instituição declara que a exposição está em
  `RWA_CPAD`.
- `fiscal_year_start` e `simple_approach_election_date`: datas usadas pelo
  motor para verificar coerência da eleição.
- `simple_approach_uniform_use_status`: declaração de uso uniforme da
  Abordagem Simples.
- `mitigation_recognition_bar_status`: `NOT_BARRED`, `BARRED` ou `UNKNOWN`.
- `uses_sa_ccr`: declaração usada para bloquear o art. 3º-A.

O motor rejeita outra abordagem, data de eleição posterior ao exercício e
status desconhecido. `institution_profile` e `capital_regime` continuam sem
substituir a declaração de escopo.

## Operação e contraparte

Declarações da instituição:

- `counterparty_legal_nature`;
- `counterparty_is_financial`;
- `counterparty_total_assets`;
- `counterparty_annual_gross_revenue`;
- `counterparty_financial_year_end`;
- `financial_data_is_latest_available`;
- `prudential_category_conflict_status`;
- `exposure_indexer`;
- `exposure_effective_maturity_date`;
- `is_otc_derivative`.

Condições conferidas pelo motor:

- natureza privada e não financeira;
- ativo total menor que R$ 240.000.000,00;
- receita maior ou igual a R$ 15.000.000,00 e menor que R$ 300.000.000,00;
- exercício social presente e não posterior à data-base;
- exposição em balanço e fora das rotas bloqueadas.

`counterparty_type` livre, `regulatory_exposure_class` e `provided_fpr` não
substituem essas declarações.

## Atributos condicionais do art. 46

A rota atual não usa agregação de varejo. Se a receita declarada for inferior
a R$ 15.000.000,00, o motor retorna `UNSUPPORTED`. Estes campos só seriam
necessários em outra rota, que permanece fora do recorte:

- `retail_excluded_operation_type`;
- `total_exposure_same_counterparty_with_fcc_before_provisions`;
- `retail_portfolio_exposure_amount`;
- `retail_concentration_ratio`;
- `connected_counterparty_group_id`;
- `connected_counterparty_aggregate_exposure`.

## Garantias e limitação temporária

O contrato continua aceitando várias garantias para a mesma operação. Os
vínculos, identificadores e valores permanecem validados estruturalmente.

O primeiro tratamento normativo, porém, só pode produzir parcelas quando houver
exatamente um mitigador, associado a uma única exposição e sem sobreposição. Se
houver mais de um, os registros são preservados e este tratamento retorna
`UNSUPPORTED`. A divisão proporcional do art. 2º, § 3º, fica para regra futura.

Declarações da instituição para o colateral:

- classificação como título público federal;
- provedor `COUNTERPARTY` ou `THIRD_PARTY`;
- consistência da marcação a mercado;
- controle de movimentação pelo credor;
- registro ou depósito autorizado, em entidade distinta, com ônus identificados;
- sustentação legal, execução tempestiva, monitoramento, segregação, controles,
  completude contratual, liquidação e ausência de correlação positiva relevante;
- escopo de associação e ausência de sobreposição.

Condições conferidas pelo motor:

- subtipo, moeda, indexador e frequência `DAILY`;
- valor de mercado positivo e data da marcação;
- vencimento efetivo do colateral igual ou superior ao da exposição;
- `linked_operation_id` correspondente;
- quantidade de mitigadores igual a um para este tratamento;
- conta da parcela coberta:
  `valor_reconhecido = valor_de_mercado × 0.80`;
  `parcela_coberta = mínimo(exposição, valor_reconhecido)`;
  `parcela_descoberta = exposição - parcela_coberta`.

`allocated_coverage_amount` enviado pelo cliente não substitui essa conta.

## Resposta futura

Antes da aprovação humana, a resposta continua com `regulatory_calculation=false`
e sem FPR, RWA, capital ou valor mitigado. Depois da aprovação, a resposta deve
expor o status, as regras, as declarações usadas e os motivos de bloqueio. Os
hashes exigidos continuam sendo os das fontes oficiais e das especificações,
não os de documentos internos da instituição.
