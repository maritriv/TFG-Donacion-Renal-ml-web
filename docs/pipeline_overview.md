# Pipeline overview

El pipeline del proyecto está organizado en cinco fases principales:

1. `src/01_data_cleaning`
2. `src/02_exploratory_analysis`
3. `src/03_model_training`
4. `src/04_model_evaluation`
5. `src/05_final_model_export`

La orquestación global se realiza desde:

- `src/main.py`

## Flujo general

```text
data/raw/dataset_medicos.xlsx
        ↓
01_data_cleaning
        ↓
data/processed/
        ↓
02_exploratory_analysis
        ↓
outputs/exploratory_analysis/
        ↓
03_model_training
        ↓
outputs/model_training/
        ↓
04_model_evaluation
        ↓
outputs/model_evaluation/
        ↓
05_final_model_export
        ↓
outputs/final_model_export/
```


## Entradas principales

- `data/raw/dataset_medicos.xlsx`

---

## Salidas principales

### Fase 01 · Limpieza y datos sintéticos

- `data/processed/dataset_mid_clean.csv`
- `data/processed/dataset_transfer_clean.csv`
- `data/processed/cleaning_report.json`
- `data/processed/dataset_mid_synthetic.csv`
- `data/processed/dataset_transfer_synthetic.csv`
- `data/processed/synthetic_report.json`

---

### Fase 02 · Análisis exploratorio

- `outputs/exploratory_analysis/eda_report.json`
- histogramas
- mapas de correlación
- distribuciones de la variable objetivo

---

### Fase 03 · Entrenamiento

- `outputs/model_training/.../cv_metrics.json`
- `outputs/model_training/.../test_metrics.json`
- `outputs/model_training/.../grid_search_results.csv`
- `outputs/model_training/.../best_model.joblib`

---

### Fase 04 · Evaluación final

La fase de evaluación compara los modelos entrenados para cada momento de predicción:

- `mid`
- `transfer`

A partir de esta comparativa, se selecciona el mejor candidato final para cada dataset según las métricas de evaluación.

Salidas principales:

- `outputs/model_evaluation/final_comparison_report.json`
- `outputs/model_evaluation/final_evaluation_report.json`
- `outputs/model_evaluation/final_metrics.json`

---

### Fase 05 · Exportación final

La fase de exportación final reentrena y exporta un modelo final independiente para cada momento de predicción:

- un modelo final para `mid`
- un modelo final para `transfer`

Cada modelo se reentrena usando:

- todos los datos reales del dataset correspondiente
- y además los datos sintéticos si el experimento ganador fue `real_plus_synthetic`

Salidas principales:

- `outputs/final_model_export/mid/final_model.joblib`
- `outputs/final_model_export/mid/final_model_metadata.json`
- `outputs/final_model_export/mid/final_metrics.json`
- `outputs/final_model_export/transfer/final_model.joblib`
- `outputs/final_model_export/transfer/final_model_metadata.json`
- `outputs/final_model_export/transfer/final_metrics.json`
- `outputs/final_model_export/final_models_report.json`

## Ejecución Pipeline Completo_
```bash
uv run -m src.main
```