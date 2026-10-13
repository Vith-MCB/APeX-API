# ADR 0004 — Primeiro recorte normativo

- Status: recorte aceito conceitualmente; fichas e evidências em revisão
- Data: 2026-10-12
- Data-base analisada: 2026-09-30

## Decisão

Documentar, sem executar, um recorte formado por:

1. exposição a pessoa jurídica privada não financeira de pequeno ou médio
   porte, conforme o art. 36 da Resolução BCB nº 229/2022;
2. título público federal em BRL como colateral financeiro na Abordagem
   Simples, conforme os arts. 2º a 7º da Circular nº 3.809/2016.

A não elegibilidade da contraparte ao varejo será provada, neste recorte,
somente por receita bruta anual maior ou igual a R$ 15 milhões. Permanecem
obrigatórios ativo total inferior a R$ 240 milhões e receita inferior a
R$ 300 milhões, ambos do exercício social mais recente disponível.

As duas fichas ficam `IN_REVIEW`. O catálogo permanece sem regra `APPROVED`.
A matriz auditável está em
`regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml`. Ela não
declara os dispositivos mapeados como exaustivos.

## Motivos

- O art. 36 contém categoria, limites e FPR expressos.
- O corte de receita permite afastar o art. 46 sem inferir todas as demais
  condições de varejo.
- O título público federal é um subtipo expresso no art. 4º, inciso III.
- O texto vigente explicita marcação a mercado, custódia, prazo, tratamento das
  parcelas, FPR coberto e redução de 20% do valor de mercado.
- A combinação permite testar no futuro uma parcela coberta e outra descoberta
  com rastreabilidade.

## Alternativas descartadas

- Exposição de varejo: exige agregação por contraparte e pelo portfólio, hoje
  ausentes.
- Financiamentos especializados, imóveis, securitização e fora de balanço:
  exigem classificação ou conversão adicional.
- Depósito na própria instituição: não foi escolhido para evitar decidir nesta
  fase como representar o vencimento efetivo residual de um depósito à vista.
- Ouro, moeda divergente, derivativo, compensação, garantia fidejussória,
  colateral compartilhado e Abordagem Abrangente: fora do recorte.
- Fator de 8% da Resolução CMN nº 4.958: depende do perfil institucional e não
  pertence a esta fase.

## Evidência e limites

As fontes oficiais estão em `regulations/sources/`, com hashes registrados em
`regulations/source_index.yaml`. A Circular possui PDF oficial compilado. Para
as Resoluções BCB nº 229 e CMN nº 4.958, o BCB não oferece PDF compilado; foram
arquivados os JSONs oficiais das versões vigentes.

A instituição financeira declara os fatos cadastrais, jurídicos e operacionais
e responde por sua veracidade e documentação. A APeX não audita comprovantes
nem trata essa declaração como verificação própria. O motor limita-se a
conferências estruturais, quantitativas e de relacionamento.

O primeiro tratamento do colateral aceita um mitigador. A arquitetura continua
preparada para várias garantias por operação; havendo mais de uma, esse
tratamento retorna `UNSUPPORTED` até que a divisão do art. 2º, § 3º, seja
especificada em regra própria.

A parcela coberta especificada, ainda sem implementação, é o menor valor entre
a exposição e 80% do valor de mercado do título. O cenário de prova usa
exposição de R$ 125.000,00 e valor de mercado de R$ 100.000,00, com parcela
coberta de R$ 80.000,00 e parcela descoberta de R$ 45.000,00.

Nenhum FPR, RWA ou capital pode ser emitido até:

1. revisão explícita das fichas pelo autor;
2. promoção posterior e separada para `APPROVED`;
3. modelagem dos campos ausentes;
4. implementação e testes independentes em fase futura.

Os atributos necessários ao contrato estão descritos, sem alteração dos
schemas, em
`regulations/specifications/API_CONTRACT_ATTRIBUTES_IN_REVIEW.md`.

Ainda dependem de autorização explícita para deixar `IN_REVIEW`:

- o texto final das duas fichas e da matriz;
- a conta da parcela coberta antes de qualquer implementação;
- a precedência do art. 36 diante de categorias prudenciais concorrentes.
