# Ficha normativa — BCB229_ART36_PJ_NAO_FINANCEIRA

- ID e versão semântica: `BCB229_ART36_PJ_NAO_FINANCEIRA`, `0.3.0`
- Status: `IN_REVIEW`
- Fonte oficial: `regulations/sources/resolucao_bcb_229_v13_vigente.json`
- URL oficial: `https://www.bcb.gov.br/api/conteudo/app/normativos/exibeversao?p1=51805&p2=13&p3=Vigente`
- SHA-256: `45b3be023b8cbb092aa4ad66c78f96cec6b1621187cd742d67827805cc5c4549`
- Consulta e versão: `2026-10-12`, versão oficial `13.0`, datada de `2025-01-30`
- Normativo: Resolução BCB nº 229/2022, art. 36, caput e parágrafo único
- Dependência para excluir varejo: art. 46, § 1º, inciso I, e § 3º
- Publicação: DOU de `2022-05-16`, com retificação no DOU de `2022-09-02`
- Vigência usada pelo recorte: desde `2023-07-01`; fim não identificado
- Data-base de prova: `2026-09-30`
- Regime: exposição sujeita à abordagem padronizada de risco de crédito
- Matriz detalhada: `regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml`

## Hipótese técnica

O art. 36 determina FPR de 85% para exposição a pessoa jurídica de direito
privado não financeira de pequeno ou médio porte. O parágrafo único exige,
cumulativamente:

1. contraparte não elegível ao art. 46;
2. ativo total inferior a R$ 240.000.000,00;
3. receita bruta anual inferior a R$ 300.000.000,00;
4. ativo e receita referentes ao exercício social mais recente disponível.

Neste recorte, a não elegibilidade ao art. 46 é provada somente por receita
bruta anual maior ou igual a R$ 15.000.000,00. Esse valor não atende à
definição de pessoa jurídica de pequeno porte do art. 46, § 3º. Outras formas
de afastar o art. 46 ficam fora do recorte.

Essa prova não torna os arts. 36 e 46 exaustivos. Conflito com outra categoria
prudencial, remissão externa ou dúvida de precedência exige revisão humana.

## Requisitos do art. 46 considerados

- O art. 46, caput, determina FPR de 75% para exposição de varejo. Esse FPR
  não é aplicado pelo recorte; o artigo é usado somente para provar a não
  elegibilidade exigida pelo art. 36.
- O art. 46, § 1º, exige cumulativamente: produto ou serviço destinado a pessoa
  natural ou PJ de pequeno porte; ausência das operações enumeradas no inciso
  II; limite total por contraparte de até R$ 5.000.000,00; e concentração
  inferior a 0,2% das exposições de varejo.
- O § 2º define a base dos limites dos incisos III e IV, incluindo FCC e
  exclusões específicas.
- O § 3º define PJ de pequeno porte por receita bruta anual inferior a
  R$ 15.000.000,00 no exercício social mais recente disponível.
- O § 4º exige teste individual e conjunto para contrapartes relacionadas.
- Os §§ 5º e 6º tratam exposições imobiliárias específicas e ficam fora deste
  recorte.

Como a rota escolhida demonstra que a contraparte não é PJ de pequeno porte,
os demais testes cumulativos do art. 46 não são usados para classificar o caso.
Se a receita for inferior a R$ 15.000.000,00, esta ficha não pode concluir a
não elegibilidade ao varejo.

## Responsabilidade e condições computáveis

A instituição declara a natureza jurídica, a natureza financeira, o ativo, a
receita, o exercício social e a inexistência de categoria prudencial
concorrente. Ela responde pela veracidade, pela documentação e pelo atestado
prévio desses fatos. A APeX não exige documento, parecer ou hash dessa
comprovação e não trata a declaração como verificação própria.

O motor confere:

- presença e formato das declarações;
- `is_off_balance=false`;
- ativo total inferior a R$ 240.000.000,00;
- receita bruta anual maior ou igual a R$ 15.000.000,00 e inferior a
  R$ 300.000.000,00;
- exercício social informado e não posterior à data-base;
- data-base dentro da vigência do recorte.

O contrato atual ainda não possui todos esses campos. Até que existam e a
ficha seja aprovada, a decisão é `INSUFFICIENT_DATA` ou `REQUIRES_REVIEW`,
sem número. `regulatory_exposure_class` e `provided_fpr` não substituem as
declarações estruturadas.

## Saídas e critérios de decisão

- `REQUIRES_REVIEW`: regra ainda `IN_REVIEW`; declarações contraditórias;
  possível categoria concorrente; ou dúvida sobre remissão, precedência ou
  vigência.
- `INSUFFICIENT_DATA`: ausência de declaração estruturada ou de valor exigido
  para uma comparação do motor.
- `UNSUPPORTED`: fato conhecido fora do recorte, incluindo exposição fora de
  balanço, data anterior à vigência adotada ou necessidade de testar outra
  rota do art. 46.
- `NOT_APPLICABLE`: requisitos objetivos do art. 36 comprovadamente não
  atendidos, sem ambiguidade.
- Enquanto o catálogo estiver `IN_REVIEW`, FPR, RWA e contribuição de capital
  permanecem vazios em todos os casos.

## Exceções e não aplicação

- pessoa natural, pessoa jurídica pública ou instituição financeira;
- ativo total maior ou igual a R$ 240.000.000,00;
- receita bruta anual inferior a R$ 15.000.000,00, pois a exclusão de varejo
  exigiria verificar todas as condições do art. 46;
- receita bruta anual maior ou igual a R$ 300.000.000,00;
- demonstrações que não sejam do exercício social mais recente disponível;
- exposição fora de balanço, securitização, derivativo, financiamento
  especializado ou qualquer categoria concorrente sem análise de precedência;
- data anterior a `2023-07-01`;
- declaração ausente ou contraditória. A simples condição de declarada não
  impede o enquadramento.

## Valor normativo e precisão

- FPR original citado no art. 36: `85%` (`0.85`).
- Esta ficha não define exposição, RWA, capital, FMR nem arredondamento.
- O artigo não estabelece regra de arredondamento para o FPR.
- O número é evidência documental. Nenhum módulo pode retorná-lo enquanto o
  status for `IN_REVIEW`.

## Casos especificados

1. **Positivo completo, candidato:** data `2026-09-30`; PJ privada não
   financeira declarada; ativo total declarado de R$ 100.000.000,00; receita
   declarada de R$ 15.000.000,00 no exercício encerrado em `2025-12-31`; sem
   categoria concorrente declarada. O motor verifica os dois limites do art. 36
   e que a receita não é inferior ao limite do art. 46, § 3º. Resultado
   normativo candidato após aprovação: enquadramento no art. 36 e FPR original
   `85%`. Resultado atual: `REQUIRES_REVIEW`, campos numéricos vazios.
2. **Atributo ausente:** mesmo caso sem o ativo total declarado. Resultado:
   `INSUFFICIENT_DATA`, campos numéricos vazios.
3. **Fora da vigência do recorte:** data `2023-06-30`. Resultado:
   `UNSUPPORTED`, campos numéricos vazios.
4. **Limite do ativo:** ativo total declarado igual a R$ 240.000.000,00. Como
   o art. 36 exige valor inferior, resultado: `NOT_APPLICABLE`, campos
   numéricos vazios.
5. **Limite inferior da receita:** receita declarada de R$ 14.999.999,99. A
   rota escolhida não afasta o art. 46. Resultado: `UNSUPPORTED`, campos
   numéricos vazios.
6. **Declaração contraditória:** categoria concorrente declarada ou dados
   cadastrais incompatíveis entre si. Resultado: `REQUIRES_REVIEW`, campos
   numéricos vazios. A declaração consistente, por si só, não gera revisão.

## Revisão e limitações

- Autor da revisão: não preenchido
- Data da revisão: não preenchida
- Decisão aberta: validar a precedência do art. 36 frente às categorias
  específicas antes de implementar classificação.
- Decisão adotada neste ajuste: a instituição atesta os fatos cadastrais; a
  APeX não audita os documentos correspondentes.

> Esta ficha não está aprovada e não autoriza cálculo regulatório.
