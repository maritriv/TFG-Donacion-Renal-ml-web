# TFG-Donacion-Renal-ml-web

Repositorio del **Trabajo de Fin de Grado en Ingeniería de Datos e Inteligencia Artificial** centrado en la **predicción de donantes renales válidos en asistolia no controlada** mediante técnicas de análisis de datos y aprendizaje automático.

El proyecto forma parte de un sistema más amplio compuesto por:

- una **aplicación móvil**, orientada al uso clínico basado en reglas médicas derivadas de una tesis doctoral,
- y una **plataforma web**, orientada a la predicción mediante modelos de *machine learning*.

Este repositorio contiene principalmente el **pipeline de datos y modelado**, incluyendo limpieza, análisis exploratorio, entrenamiento, evaluación y exportación del modelo final.

---

## Objetivo del repositorio

El objetivo de este repositorio es implementar un flujo reproducible para:

1. cargar y limpiar los datos clínicos proporcionados por el equipo médico,
2. construir datasets de modelado para distintos momentos clínicos,
3. realizar análisis exploratorio,
4. entrenar y comparar distintos modelos de clasificación,
5. evaluar el rendimiento final,
6. exportar el modelo seleccionado para su integración posterior en la plataforma web.

---

## Fases del pipeline

El proyecto está organizado en cinco fases principales:

### 1. Limpieza y preparación de datos
- lectura de la hoja `Donante` del Excel clínico,
- normalización de nombres de columnas,
- eliminación de duplicados,
- limpieza de variables binarias y numéricas,
- creación de la variable objetivo `DONANTE_VALIDO`,
- construcción de datasets para dos momentos clínicos:
  - `MID`
  - `TRANSFER`

### 2. Análisis exploratorio
- estudio descriptivo de variables,
- distribución de la variable objetivo,
- histogramas,
- matrices de correlación,
- generación de reportes automáticos.

### 3. Entrenamiento de modelos
Comparación de varios modelos de clasificación, entre ellos:
- Dummy Classifier
- Logistic Regression
- Random Forest
- SVM
- XGBoost
- Voting Classifier

Se contemplan dos escenarios experimentales:
- entrenamiento con **datos reales**,
- entrenamiento con **datos reales + sintéticos**.

### 4. Evaluación final
- selección de modelos candidatos,
- evaluación sobre conjunto de prueba,
- generación de métricas,
- matrices de confusión,
- comparación final entre configuraciones.

### 5. Exportación del modelo final
- selección del mejor candidato global,
- reentrenamiento con todos los datos disponibles,
- exportación del modelo final en formato `joblib`,
- guardado de metadatos y métricas finales.

---

## Estructura del repositorio

```text
TFG-Donacion-Renal-ml-web/
├── data/
│   ├── raw/                  # Datos originales
│   ├── processed/            # Datasets limpios, sintéticos y reportes
│   └── external/             # Datos externos complementarios
├── docs/                     # Documentación técnica complementaria
├── outputs/
│   ├── exploratory_analysis/ # Gráficas y reportes del EDA
│   ├── model_training/       # Resultados de entrenamiento
│   ├── model_evaluation/     # Evaluación final
│   └── final_model_export/   # Modelo final exportado
├── src/
│   ├── 01_data_cleaning/
│   ├── 02_exploratory_analysis/
│   ├── 03_model_training/
│   ├── 04_model_evaluation/
│   ├── 05_final_model_export/
│   ├── common/
│   └── main.py               # Orquestador global del pipeline
├── tests/
├── web/
│   ├── backend/
│   └── frontend/
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Requisitos
- Python 3.11 o superior
- [uv](https://github.com/astral-sh/uv) para la gestión del entorno y dependencias

---

## Instalación del entorno

**1.** Clonar el repositorio:

```bash
git clone https://github.com/maritriv/TFG-Donacion-Renal-ml-web.git
cd TFG-Donacion-Renal-ml-web
```

**2.** Instalar `uv` (si no esta instalado):

```bash
pip install uv
```

**3.** Instalar dependencias base:

```bash
uv sync
```

**4.** Instalar dependenciaS opcionales para datos sintéticos:

```bash
uv sync --extra synthetic
```
--- 

## Ejecución

**Ejecutar el pipeline completo:**

```bash
uv run -m src.main
```

**Ejecutar solo la fase de limpieza y generación de datos sintéticos**
```bashe
uv run -m src.01_data_cleaning.main
```

**Ejecutar solo limpieza**
```bashe
uv run -m src.01_data_cleaning.clean_data
```

**Ejecutar solo generación sintética**
```bashe
uv run -m src.01_data_cleaning.generate_synthetic_data
```

**Ejecutar solo análisis exploratorio**
```bashe
uv run -m src.02_exploratory_analysis.main
```

**Ejecutar solo entrenamiento**
```bashe
uv run -m src.03_model_training.main
```

**Ejecutar solo evaluación final**
```bashe
uv run -m src.04_model_evaluation.main
```

**Ejecutar solo exportación final**
```bashe
uv run -m src.05_final_model_export.main
```
---

## Datos de entrada

La entrada principal del pipeline es el archivo:
```bash
data/raw/dataset_medicos.xlsx
````

Actualmente se utiliza la hoja **Donante**.

---

## Salidas principales

### Datos procesados

En `data/processed/` se generan, entre otros:

- `dataset_mid_clean.csv`
- `dataset_transfer_clean.csv`
- `cleaning_report.json`
- `dataset_mid_synthetic.csv`
- `dataset_transfer_synthetic.csv`
- `synthetic_report.json`

---

### Análisis exploratorio

En `outputs/exploratory_analysis/` se generan:

- histogramas de variables relevantes,
- distribuciones de la variable objetivo,
- mapas de correlación,
- `eda_report.json`.

---

### Entrenamiento y evaluación

En `outputs/model_training/` y `outputs/model_evaluation/` se generan:

- métricas por modelo,
- resultados de validación cruzada,
- matrices de confusión,
- comparativas entre modelos,
- predicciones sobre test.

---

### Modelo final

En `outputs/final_model_export/` se exportan:

- `final_model.joblib`
- `final_model_metadata.json`
- `final_metrics.json`

---

## Resultado final actual

De acuerdo con la última ejecución almacenada en el repositorio, el modelo final exportado corresponde a:

- **dataset seleccionado:** `transfer`
- **modelo seleccionado:** `xgboost`
- **experimento:** `real_plus_synthetic`
- **métrica principal de selección:** `F1-score`
- **recall en evaluación final:** `0.8`
- **F1-score en evaluación final:** `0.8`

> Estos resultados deben interpretarse dentro del contexto del tamaño muestral disponible y del carácter académico-experimental del proyecto.

---

## Estado del proyecto

Estado actual del repositorio:

- [x] limpieza y preparación de datos  
- [x] generación de datasets de modelado  
- [x] análisis exploratorio  
- [x] entrenamiento y comparación de modelos  
- [x] evaluación final  
- [x] exportación del modelo final  
- [ ] integración completa con la aplicación web  
- [ ] batería de tests automatizados  
- [ ] despliegue final del backend y frontend  

---

## Tecnologías utilizadas

- Python  
- pandas  
- numpy  
- scikit-learn  
- xgboost  
- matplotlib  
- openpyxl  
- rich  
- sdv / CTGAN (para generación sintética)  
- joblib  

---

## Consideraciones

- Este repositorio forma parte de un TFG con aplicación en un contexto clínico real.  
- Los modelos desarrollados tienen fines académicos y de apoyo a la decisión, no sustituyen la valoración médica.  
- La validez de los resultados depende del tamaño, calidad y representatividad del dataset proporcionado.  

---

## Autora

**Marina Triviño de las Heras**

Grado en Ingeniería de Datos e Inteligencia Artificial  
Universidad Complutense de Madrid  

---

## Repositorios relacionados

- Aplicación móvil: [TFG-Donacion-Renal](https://github.com/maritriv/TFG-Donacion-Renal)
