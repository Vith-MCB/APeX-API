# Exemplos sintéticos

`combined_input.jsonl` traz uma operação e duas garantias ligadas por
`granted_operation`. `structural_exposure.json` repete esse tipo de validação
em JSON. `didactic_exposure.json` é o caso individual de exposição declarada
de R$ 125.000,00 com um título público federal.

Nenhum desses arquivos é carteira bancária nem prova de elegibilidade. O
gerador abaixo só converte o JSONL de exemplo em Parquet:

```bash
python scripts/generate_synthetic_data.py examples/combined_input.jsonl data/input/combined_v1.parquet
```

O layout `combined_v1` não carrega as declarações do art. 36 nem do título.
O lote resultante valida vínculos e exporta linhas sem FPR, parcela, RWA ou
contribuição. O cálculo didático desses números fica no JSON individual.
