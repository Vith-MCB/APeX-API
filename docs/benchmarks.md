# Benchmarks

Medição feita em 13/10/2026 com `scripts/benchmark.py`. Os números abaixo saíram dessa execução. O JSON completo ficou em `data/benchmarks/results.json`, pasta ignorada pelo Git.

## O que foi medido

O lote contém só operações sintéticas do layout `combined_v1`: `has_guarantee` falso, saldo contábil `1.00`, sem linha de garantia. O contexto é `VALIDATION_ONLY`. O worker valida o arquivo, normaliza, confere vínculos e grava os seis arquivos de saída.

Não há cálculo didático de FPR, parcela, RWA ou contribuição. Em todas as execuções, `calculated_subset_rwa` ficou nulo e o status foi `COMPLETED`.

O tempo de gerar o Parquet é outra etapa. A vazão usa só o tempo de `run_job`. Cada processamento correu num processo novo. A memória é o pico de residente desse processo (`ru_maxrss` do Linux), já incluindo o interpretador e a cópia do upload para a pasta do job. Não é a memória isolada de uma função.

A validação reúne a inspeção do Parquet, a normalização e os vínculos. A exportação reúne a montagem das linhas e a gravação dos arquivos, inclusive o manifesto. A publicação da pasta e o encerramento no SQLite ficam no tempo total e fora desses dois trechos. Por isso a soma dos dois trechos é um pouco menor que o total.

Os volumes de 1.000, 10.000, 50.000 e 100.000 linhas foram repetidos três vezes. O volume de 1.000.000 foi uma execução exploratória e terminou. Nenhum arquivo passou do limite padrão de upload, 200 MiB.

`tranches.parquet`, `issues.parquet` e `trace.parquet` quase não crescem: não há garantia, issue nem trilha de cálculo. O arquivo que acompanha o volume é `results.parquet`.

## Ambiente

| Item | Valor lido na máquina |
| --- | --- |
| Sistema | Linux-7.2.5-200.fc44.x86_64-x86_64-with-glibc2.43 |
| Python | 3.14.8 |
| CPU | Intel(R) Core(TM) i5-7400 CPU @ 3.00GHz |
| Memória total | 8077372 kB |
| PyArrow | 26.0.0 |

## Resultado

Tempos em segundos, vazão em linhas por segundo e memória em MiB. A tabela usa a mediana. O intervalo é o menor e o maior tempo de `run_job` entre as repetições. A vazão e a memória também são medianas. Os tempos estão arredondados para milissegundo, a vazão para o inteiro mais próximo e a memória para uma casa. Os tamanhos estão em bytes, sem arredondamento.

| Linhas | Geração | Lote | Intervalo do lote | Validação | Exportação | Linhas/s | Memória | Entrada | results.parquet |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 0,187 | 0,061 | 0,061–0,067 | 0,039 | 0,022 | 16.264 | 86,3 | 24.032 | 39.932 |
| 10.000 | 0,209 | 0,439 | 0,413–0,442 | 0,327 | 0,102 | 22.767 | 114,2 | 203.990 | 385.853 |
| 50.000 | 0,389 | 2,254 | 2,192–2,285 | 1,671 | 0,555 | 22.184 | 223,0 | 1.016.218 | 2.027.590 |
| 100.000 | 0,817 | 4,394 | 4,179–4,408 | 3,267 | 1,046 | 22.756 | 317,8 | 2.024.396 | 4.031.105 |
| 1.000.000 | 3,337 | 45,016 | uma execução | 32,777 | 11,773 | 22.215 | 1.524,7 | 20.175.043 | 37.343.318 |

A primeira geração de 1.000 linhas levou 1,633 s. As duas seguintes levaram 0,184 s e 0,187 s. A mediana dessa linha é 0,187 s. O maior pico de memória nas três repetições de 50.000 linhas foi 229,2 MiB. Nos outros volumes a diferença entre a mediana e o maior pico ficou abaixo de 1 MiB.

Nos quatro volumes repetidos, `tranches.parquet` ficou com 2.304 bytes, `issues.parquet` com 1.218 e `trace.parquet` com 767. No milhão de linhas esses três tamanhos se repetiram. `summary.json` variou de 492 a 513 bytes, conforme a contagem escrita. `manifest.json` ficou com 1.711 bytes.

## Como repetir

Na raiz do repositório, com o ambiente virtual ativo:

```bash
python scripts/benchmark.py --output data/benchmarks/results.json
```

O comando repete três vezes os quatro volumes e faz uma tentativa de 1.000.000 linhas. Para omitir o milhão, use `--no-million`. A suíte `pytest` só dispara o mesmo caminho com 32 linhas, para conferir que a medição existe e que o subconjunto prudencial continua nulo.
