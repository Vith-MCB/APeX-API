# ADR 0005 — Hipótese do valor da exposição

- Status: adotada para a Fase 5
- Data: 2026-10-12
- Fonte: Resolução BCB nº 229/2022, arts. 5º e 6º, versão 13.0

## Decisão

E não é o saldo contábil. A APeX não aplica o Cosif nem deduz provisões por
conta própria.

E só existe quando a instituição declara `provided_exposure_amount` com a base
`INSTITUTION_DECLARED_ART5_ART6`, afirmando que o valor já observa o art. 5º e
o art. 6º. Sem essa declaração, o resultado é `INSUFFICIENT_DATA`. Valor
negativo é `INVALID_INPUT`, porque o art. 6º, § 1º, exige resultado igual ou
superior a zero.

## Consequência

O FPR de 85% do art. 36 pode ser demonstrado no modo `DIDACTIC` apenas quando
o recorte e essa declaração estão completos. O modo `REGULATORY` continua sem
número enquanto a regra estiver `IN_REVIEW`.
