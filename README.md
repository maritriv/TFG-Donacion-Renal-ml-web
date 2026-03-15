# renal-dcd-ml-web

## Descripcion

Proyecto de **Trabajo de Fin de Grado (TFG)** orientado a la prediccion de viabilidad de donacion renal.  
En la fase actual se ha implementado la **primera capa del pipeline de datos**, centrada en:

- Limpieza y validacion de la hoja `Donante` del Excel clinico
- Generacion de datasets limpios para dos momentos clinicos (`MID` y `TRANSFERENCIA`)
- Generacion de datasets sinteticos y reporte comparativo basico

---
### Funcionalidades

---

## Estructura general del repositorio
```text
TFG-Donacion-Renal-ml-web/
|-- .gitignore
|-- pyproject.toml
|-- README.md
|-- uv.lock
|-- data/
|   |-- external/
|   |   `-- .gitkeep
|   |-- processed/
|   |   |-- .gitkeep
|   |   |-- cleaning_report.json
|   |   |-- dataset_mid_clean.csv
|   |   |-- dataset_mid_synthetic.csv
|   |   |-- dataset_transfer_clean.csv
|   |   |-- dataset_transfer_synthetic.csv
|   |   `-- synthetic_report.json
|   `-- raw/
|       |-- .gitkeep
|       `-- dataset_medicos.xlsx
|-- docs/
|   |-- .gitkeep
|   |-- pipeline_overview.md
|   `-- README.md
|-- src/
|   |-- 01_data_cleaning/
|   |   |-- clean_data.py
|   |   |-- generate_synthetic_data.py
|   |   |-- main.py
|   |   |-- __init__.py
|   |   `-- modules/
|   |       |-- cleaning_pipeline.py
|   |       |-- cleaning_steps.py
|   |       |-- config.py
|   |       |-- synthetic_pipeline.py
|   |       |-- synthetic_steps.py
|   |       |-- visual_logger.py
|   |       `-- __init__.py
|   |-- 02_exploratory_analysis
|   |   `-- __init__.py
|   |-- 03_model_training/
|   |   `-- __init__.py
|   |-- 04_model_evaluation/
|   |   `-- train.py
|   `-- 05_final_model_export/
|       `-- __init__.py
|-- tests/
|   `-- .gitkeep
|-- web/
|   |-- backend/
|   |   `-- .gitkeep
|   `-- frontend/
|       `-- .gitkeep
```

---

## Indice
Detalles de subdirectorios y archivos principales existentes:

- Directorio __`src/`__: Codigo fuente del proyecto.
    - Directorio __`01_data_cleaning/`__: Implementacion de la fase actual del pipeline.
        - Archivo `main.py`: Orquesta el flujo completo (limpieza y sintesis) en un unico comando.
        - Archivo `clean_data.py`: Ejecuta unicamente la etapa de limpieza de datos.
        - Archivo `generate_synthetic_data.py`: Ejecuta unicamente la etapa de generacion sintetica.
        - Directorio __`modules/`__: Modulos internos reutilizables de la fase.
            - Archivo `config.py`: Centraliza umbrales, rutas, nombres de salida y listas de columnas.
            - Archivo `visual_logger.py`: Implementa logs visuales con banners y pasos numerados.
            - Archivo `cleaning_steps.py`: Contiene funciones atomicas de limpieza y validacion.
            - Archivo `cleaning_pipeline.py`: Define y ejecuta la secuencia completa de limpieza.
            - Archivo `synthetic_steps.py`: Contiene funciones de sintesis y validacion estadistica basica.
            - Archivo `synthetic_pipeline.py`: Define y ejecuta la secuencia completa de sintesis.
    - Directorio __`03_model_training/`__: Espacio base para la etapa de entrenamiento.
    - Directorio __`04_model_evaluation/`__: Incluye `train.py` para pruebas de entrenamiento/evaluacion.
    - Directorio __`05_final_model_export/`__: Espacio reservado para exportacion del modelo final.

- Directorio __`data/`__: Datos de entrada y salidas del pipeline.
    - Directorio `raw/`: Datos originales (incluye `dataset_medicos.xlsx`).
    - Directorio `processed/`: Salidas generadas por el pipeline.
        - Archivo `dataset_mid_clean.csv`: Dataset limpio para el momento clinico medio.
        - Archivo `dataset_transfer_clean.csv`: Dataset limpio para el momento clinico de transferencia.
        - Archivo `dataset_mid_synthetic.csv`: Dataset sintetico generado a partir de `dataset_mid_clean.csv`.
        - Archivo `dataset_transfer_synthetic.csv`: Dataset sintetico generado a partir de `dataset_transfer_clean.csv`.
        - Archivo `cleaning_report.json`: Informe estructurado de trazabilidad de la limpieza.
        - Archivo `synthetic_report.json`: Informe estructurado de validacion basica real vs sintetico.
    - Directorio `external/`: Espacio reservado para datos externos complementarios.

- Directorio __`docs/`__: Documentacion tecnica complementaria.
    - Archivo `pipeline_overview.md`: Resumen del funcionamiento del pipeline.
    - Archivo `README.md`: Nota de entrada a la documentacion del directorio.

- Directorio __`tests/`__: Carpeta de pruebas (actualmente mantenida con `.gitkeep`).
- Directorio __`web/`__: Estructura inicial de aplicacion (`backend/` y `frontend/`, ambas con `.gitkeep`).

- Archivo __`pyproject.toml`__: Define metadatos del proyecto y dependencias con `uv`.
- Archivo __`uv.lock`__: Congela versiones de dependencias para reproducibilidad.
- Archivo __`.gitignore`__: Evita subir artefactos temporales o de entorno.

---

## Instalacion del entorno

**1.** Clonar el repositorio:

```bash
git clone https://github.com/maritriv/TFG-Donacion-Renal-ml-web.git
cd TFG-Donacion-Renal-ml-web
```

**2.** Instalar `uv` (si no esta instalado):

```bash
pip install uv
```

**3.** Instalar dependencias:

```bash
uv sync
```

**4.** Instalar dependenciaS de sintesis avanzada (CTGAN):

```bash
uv sync --extra synthetic
```

**5.** Ejecutar pipelines:

```bash
# Pipeline completo (limpieza + sintetico)
uv run -m src.01_data_cleaning.main

# Solo limpieza
uv run -m src.01_data_cleaning.clean_data

# Solo sintetico
uv run -m src.01_data_cleaning.generate_synthetic_data
```

**Outputs generados:**
En data/processed/ se generan:
- dataset_mid_clean.csv
- dataset_transfer_clean.csv
- cleaning_report.json
- dataset_mid_synthetic.csv
- dataset_transfer_synthetic.csv
- synthetic_report.json

---

## Equipo de desarrollo

- Marina Trivino de las Heras

---

## Recursos adicionales

- [Memoria]()
- [Repositorio a aplicacion movil](https://github.com/maritriv/TFG-Donacion-Renal)
