# Atributos de contrato exigidos pelo primeiro recorte

- Status: `IN_REVIEW`
- Data-base: `2026-09-30`
- Regras relacionadas: `BCB229_ART36_PJ_NAO_FINANCEIRA` e
  `CIRC3809_SIMPLE_TPF_BRL`
- Matriz normativa:
  `regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml`

As declarações do art. 36 e a base de E entraram no contrato individual. O
layout Parquet não mudou. As regras não estão aprovadas e o modo `REGULATORY`
não devolve número.

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
- `fiscal_year_start`, `fiscal_year_end` e
  `simple_approach_election_date`: período e data usados para verificar a
  eleição.
- `simple_approach_uniform_use_status`: declaração de uso uniforme da
  Abordagem Simples.
- `mitigation_recognition_bar_status`: `NOT_BARRED`, `BARRED` ou `UNKNOWN`.
- `uses_sa_ccr`: declaração usada para bloquear o art. 3º-A.

O art. 3º, § 1º, permite que a opção ocorra durante o exercício social em que
vigorará, com aplicação desde o início desse exercício. O motor exige início
menor ou igual ao fim, eleição entre essas datas e data-base dentro do mesmo
período. Não presume duração anual nem exige eleição anterior ao início.
`prudential_scope_status=RWA_CPAD` confirma o escopo declarado deste
tratamento. `institution_profile` e `capital_regime` continuam sem substituir
a declaração de escopo.

## Operação e contraparte

Declarações da instituição:

- `counterparty_legal_nature`;
- `counterparty_is_financial`;
- `counterparty_total_assets`;
- `counterparty_annual_gross_revenue`;
- `counterparty_financial_year_end`;
- `financial_data_is_latest_available`;
- `prudential_category_conflict_status`;
- `exposure_indexation_currency`, com código de moeda ou `NONE` explícito;
- `exposure_financial_indexer`, com nome do indexador ou `NONE` explícito;
- `exposure_effective_maturity_date`;
- `is_otc_derivative`;
- `exposure_value_basis=INSTITUTION_DECLARED_ART5_ART6`, junto de
  `provided_exposure_amount`, para declarar E já apurado nos arts. 5º e 6º.

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
- `guarantee_type=COLLATERAL` e provedor `COUNTERPARTY` ou `THIRD_PARTY`;
- consistência da marcação a mercado;
- controle de movimentação pelo credor;
- registro ou depósito autorizado, em entidade distinta, com ônus identificados;
- sustentação legal, execução tempestiva, monitoramento, segregação, controles,
  completude contratual, liquidação e ausência de correlação positiva relevante;
- escopo de associação e ausência de sobreposição.

Moeda de indexação e indexador financeiro são fatos diferentes. O contrato usa
`collateral_indexation_currency` e `collateral_financial_indexer`. Ausência de
indexação é declarada com `NONE` nos dois lados da comparação; campos nulos não
são interpretados como coincidência.

Para a data do valor de mercado, `market_value_date_policy` aceita:

- `REFERENCE_DATE`: `market_value_as_of` deve ser igual à data-base;
- `PREVIOUS_BUSINESS_DAY_DECLARED`: a data deve ser anterior à data-base e a
  instituição declara que ela corresponde ao dia útil imediatamente anterior.

A APeX confere a coerência entre a política e as datas. A instituição responde
pelo calendário usado na declaração de dia útil. Frequência `DAILY` e
`mark_to_market_consistency_status=DECLARED` continuam obrigatórios.

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

## Resposta

Enquanto as fichas estão `IN_REVIEW`, somente `DIDACTIC` publica candidatos de
FPR, parcelas, RWA e contribuição isolada de PR, sempre com
`regulatory_calculation=false` e `complete_regulatory_coverage=false`.
`REGULATORY` e `VALIDATION_ONLY` mantêm esses números vazios. A resposta expõe
status, regras e motivos de bloqueio. Os hashes exigidos continuam sendo os das
fontes oficiais e das especificações, não os de documentos internos da
instituição.

No modo didático, `rwa_before_mitigation` pode ser publicado quando E e FPR
original estão fechados. RWA depois, diferença e contribuição de PR só são
publicados quando a mitigação foi calculada, quando não existe garantia, ou
quando a garantia é expressamente `NOT_APPLICABLE`. Status `UNSUPPORTED`,
`INSUFFICIENT_DATA`, `REQUIRES_REVIEW` e `INVALID_INPUT` deixam esses resultados
posteriores vazios.

O endpoint de cálculo reutiliza as mesmas conferências estruturais do endpoint
de validação. Divergência entre `has_guarantee` e a lista ou
`linked_operation_id` incorreto gera issue, `mitigation_status=INVALID_INPUT` e
impede resultados de mitigação.
