# Pipeline overview

El pipeline se divide en tres etapas:

1. Limpieza (`src/limpieza`)
2. Analisis (`src/analisis`)
3. Modelado (`src/modelado`)

La orquestacion vive en `src/pipeline/run.py`.

## Entradas y salidas

- Entrada principal:
  - `data/raw/dataset_medicos.xlsx`
- Salidas de limpieza:
  - `data/processed/dataset_limpio.csv`
- Salidas de analisis:
  - `models/metrics/analysis_report.json`
- Salidas de modelado:
  - `models/trained/baseline_model.json`
  - `models/metrics/training_metrics.json`

## Comando

```bash
python -m pipeline.run --input data/raw/dataset_medicos.xlsx
```
