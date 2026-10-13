# Ficha normativa — CIRC3809_SIMPLE_TPF_BRL

- ID e versão semântica: `CIRC3809_SIMPLE_TPF_BRL`, `0.3.0`
- Status: `IN_REVIEW`
- Fonte oficial: `regulations/sources/circular_3809_v18_L.pdf`
- URL oficial: `https://normativos.bcb.gov.br/Lists/Normativos/Attachments/50258/Circ_3809_v18_L.pdf`
- SHA-256: `10e7439e8ca16809730fc466b44a6fe6a20f053953165b9c1f3199e1e061d77a`
- Consulta e versão: `2026-10-12`, PDF oficial compilado `18_L`
- Normativo: Circular nº 3.809/2016, arts. 2º a 7º
- Dispositivos centrais: art. 4º, inciso III e §§ 1º, 7º e 8º; art. 5º;
  art. 6º, inciso I e § 1º
- Publicação: DOU de `2016-08-26`
- Vigência usada pelo recorte: desde `2023-07-01`; fim não identificado
- Data-base de prova: `2026-09-30`
- Regime: `RWA_CPAD`, colateral financeiro, Abordagem Simples
- Matriz detalhada: `regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml`

## Hipótese técnica

Um título público federal em BRL é usado como colateral financeiro de uma
exposição em BRL, sob a Abordagem Simples. A redação vigente consultada:

1. reconhece títulos públicos federais como colateral financeiro;
2. exige marcação a mercado e movimentação somente por ordem do credor;
3. exige registro ou depósito centralizado elegível, em entidade distinta;
4. separa a exposição em parcela coberta e não coberta;
5. mantém na parcela não coberta o FPR original da Resolução BCB nº 229;
6. aplica FPR de 0% à parcela coberta sem descasamento de moeda;
7. reduz em 20% o valor de mercado desse colateral para aplicar o FPR de 0%.

O recorte exclui operação com derivativo de balcão, que recebe tratamento
específico no art. 7º.

Os arts. 2º a 7º são mapeados apenas no que afeta ou delimita este caso. A
ficha não presume que esses dispositivos eliminem remissões, poderes
supervisórios ou categorias concorrentes existentes em outros normativos.

## Responsabilidade e condições computáveis

A instituição declara, de forma estruturada, a eleição e o uso uniforme da
Abordagem Simples, a ausência de vedação do art. 2º, § 8º, a classificação do
título, a consistência da marcação, o controle de movimentação, o registro ou
depósito, a distinção da entidade, a identificação de ônus e todos os requisitos
jurídicos e operacionais do art. 2º, § 1º. Ela responde pela documentação e
pelo atestado prévio. A APeX não pede documento, parecer ou hash dessas
comprovações e não apresenta a declaração como auditoria própria.

O motor confere:

- abordagem `SIMPLE`, datas coerentes e um subtipo de título público federal;
- exposição em balanço, em BRL, sem derivativo de balcão;
- moeda e indexador iguais entre exposição e colateral;
- valor de mercado positivo e marcação diária não posterior à data-base;
- vencimento efetivo do colateral igual ou superior ao da exposição;
- vínculo com uma única operação e ausência de sobreposição declarada;
- exatamente um mitigador para este primeiro tratamento;
- a conta da parcela coberta descrita abaixo.

A operação pode continuar trazendo várias garantias. Essa capacidade estrutural
permanece. Enquanto o art. 2º, § 3º, não tiver algoritmo aprovado, dois ou mais
mitigadores produzem `UNSUPPORTED` neste tratamento, sem apagar os vínculos.

O contrato atual não possui todos os atributos. Até que existam e a ficha seja
aprovada, a saída é `INSUFFICIENT_DATA` ou `REQUIRES_REVIEW`, sem FPR, RWA ou
capital.

## Saídas e critérios de decisão

- `REQUIRES_REVIEW`: regra ainda `IN_REVIEW`; declarações contraditórias;
  sobreposição; situação supervisória desconhecida; ou dúvida de remissão,
  precedência ou vigência.
- `INSUFFICIENT_DATA`: ausência de declaração estruturada ou de valor exigido
  para uma comparação ou conta do motor.
- `UNSUPPORTED`: fato conhecido fora do recorte, como outra abordagem, moeda
  ou indexador descasado, múltiplos mitigadores, derivativo de balcão,
  instrumento diferente de título público federal ou exposição fora de
  balanço.
- `NOT_APPLICABLE`: requisito de reconhecimento comprovadamente não atendido,
  como vencimento residual menor, movimentação fora do controle do credor ou
  vedação supervisória comprovada.
- Enquanto o catálogo estiver `IN_REVIEW`, FPR, RWA, valor mitigado e
  contribuição de capital permanecem vazios.

## Exceções e não aplicação

- Abordagem Abrangente, SA-CCR, derivativo de balcão, compensação, garantia
  fidejussória, derivativo de crédito, securitização e fora de balanço;
- instrumento diferente de título público federal;
- moedas ou indexadores descasados;
- vencimento efetivo do colateral inferior ao da exposição;
- marcação a mercado não diária;
- custódia, registro, contrato, execução ou controles declarados como não
  atendidos;
- entidade de registro ou depósito não autorizada ou não distinta;
- compartilhamento, associação múltipla ou sobreposição;
- data anterior a `2023-07-01`;
- FPR original ausente ou proveniente de regra não aprovada.

## Determinação da parcela coberta

A determinação usa somente dispositivos já lidos e o limite próprio da
exposição:

1. Art. 6º, § 1º: para aplicar o inciso I aos títulos do art. 4º, inciso III,
   o valor de mercado é reduzido em 20%.
   `valor_reconhecido = valor_de_mercado × 0.80`.
2. Art. 5º, caput: a exposição é separada em parcela coberta e parcela não
   coberta. A parcela coberta é uma parcela da exposição, portanto não pode
   ultrapassá-la.
   `parcela_coberta = mínimo(exposição, valor_reconhecido)`.
   `parcela_descoberta = exposição - parcela_coberta`.
3. Art. 6º, inciso I, como exceção ao piso de 20% do art. 5º, § 2º: a parcela
   coberta recebe FPR `0%` quando não há descasamento de moeda ou indexador.
4. Art. 5º, inciso II: a parcela descoberta mantém o FPR original. No recorte,
   esse FPR é `85%` apenas quando a exposição cumprir a ficha do art. 36.
5. A estrutura de agregação é `RWA = parcela_coberta × 0 + parcela_descoberta ×
   FPR_original`. Nenhum fator de capital da Resolução CMN nº 4.958 entra nessa
   conta.

A fórmula não está implementada. Ela somente poderá ser executada depois da
aprovação desta ficha, da integridade das fontes e dos testes exigidos pelo
registro.

### Cenário numérico

Data-base `2026-09-30`. Exposição em balanço de R$ 125.000,00, em BRL e sem
indexador divergente. Um título público federal em BRL, com valor de mercado
de R$ 100.000,00, marcação diária e vencimento efetivo não inferior ao da
exposição. Todas as declarações institucionais estão preenchidas como
atendidas e não há sobreposição.

- redução de 20%: R$ 20.000,00;
- valor reconhecido: R$ 80.000,00;
- parcela coberta: R$ 80.000,00, com FPR `0%`;
- parcela descoberta: R$ 45.000,00, com FPR `85%`;
- RWA candidato: R$ 38.250,00.

Se o valor reconhecido fosse R$ 160.000,00, a parcela coberta ficaria limitada
à exposição de R$ 125.000,00 e a parcela descoberta seria zero. Dois mitigadores
na mesma operação continuam armazenados, mas este tratamento retorna
`UNSUPPORTED`.

A Circular não define arredondamento monetário nesses dispositivos. A futura
implementação deve preservar `Decimal` e adiar arredondamento. Enquanto a ficha
estiver `IN_REVIEW`, o resultado efetivo permanece vazio.

## Casos especificados

1. **Positivo completo, candidato:** o cenário numérico acima. Resultado
   normativo candidato após aprovação: parcela coberta de R$ 80.000,00 com FPR
   `0%`, parcela descoberta de R$ 45.000,00 com FPR `85%` e RWA candidato de
   R$ 38.250,00. Resultado atual: `REQUIRES_REVIEW`, campos numéricos vazios.
2. **Atributo ausente:** sem a declaração estruturada do registro ou depósito.
   Resultado: `INSUFFICIENT_DATA`, campos numéricos vazios.
3. **Fora da vigência do recorte:** data `2023-06-30`. Resultado:
   `UNSUPPORTED`, campos numéricos vazios.
4. **Vínculo inválido:** sobreposição declarada. Resultado:
   `REQUIRES_REVIEW`, campos numéricos vazios. Mais de um mitigador preserva
   os registros e retorna `UNSUPPORTED` neste tratamento.
5. **Limite de vencimento:** vencimentos residuais iguais. O requisito
   comparativo do art. 5º, § 3º, é atendido; a regra continua
   `REQUIRES_REVIEW` e sem número. Se o vencimento do colateral for menor,
   resultado `NOT_APPLICABLE`, sem número.
6. **Descasamento conhecido:** moeda ou indexador divergente. O art. 6º,
   inciso II, existe, mas não pertence ao caso BRL sem descasamento escolhido.
   Resultado: `UNSUPPORTED`, sem número.
7. **Derivativo de balcão:** o art. 7º prevê tratamento próprio. Resultado:
   `UNSUPPORTED`, sem número.
8. **Vedação supervisória:** vedação do art. 2º, § 8º, declarada pela
   instituição. Resultado:
   `NOT_APPLICABLE`, sem número; situação desconhecida resulta em
   `REQUIRES_REVIEW`.

## Revisão e limitações

- Autor da revisão: não preenchido
- Data da revisão: não preenchida
- Decisão especificada e ainda não implementada: parcela coberta igual ao
  mínimo entre a exposição e 80% do valor de mercado.
- Decisão adotada neste ajuste: requisitos jurídicos e operacionais são
  declarações da instituição; a APeX não audita seus documentos.
- Limitação temporária: o cálculo normativo inicial aceita um mitigador,
  embora a arquitetura preserve várias garantias por operação.
- A Resolução CMN nº 4.958 permanece apenas como contexto; nenhum fator de
  capital é aplicado.

> Esta ficha não está aprovada e não autoriza cálculo regulatório.
