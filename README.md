# TFG-Donacion-Renal-ml-web

## Descripción
Trabajo de Fin de Grado - Aplicación móvil para la **predicción de donantes renales válidos en asistolia no controlada (uDCD)** usando **capnometría** (EtCO₂ en punto medio y en transferencia) y variables clínicas mínimas.
---

El trabajo completo consta de dos repositorios:

- Un primer repositorio que desarrolla una aplicación móvil en Android Studio basada en reglas clínicas derivadas de una tesis doctoral.
- Un segundo repositorio (este), que integra tanto el desarrollo de modelos de aprendizaje automático como una plataforma web para su utilización.

Este repositorio incluye:

- el pipeline completo de datos y modelado (limpieza, análisis, entrenamiento, evaluación y exportación),
- y una aplicación web (backend + frontend) que permite utilizar y comparar los modelos en un entorno interactivo.

---

## Objetivo del repositorio

El objetivo de este repositorio es implementar un flujo reproducible para:

1. Cargar y limpiar los datos clínicos proporcionados por el equipo médico.
2. Construir datasets de modelado para distintos momentos clínicos.
3. Realizar análisis exploratorio.
4. Entrenar y comparar distintos modelos de clasificación.
5. Evaluar el rendimiento final.
6. Exportar los modelos finales para su integración en la plataforma web de predicción.

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

### 5. Exportación de modelos finales
- selección del mejor candidato para cada momento clínico,
- reentrenamiento con todos los datos disponibles,
- exportación de los modelos finales en formato `joblib`,
- guardado de metadatos y métricas finales.

---

## Plataforma web

El repositorio incluye una aplicación web completa (backend y frontend) que permite utilizar los modelos desarrollados en el pipeline.

La plataforma está diseñada para:

- Introducir los datos de un posible donante y obtener una predicción mediante modelos de aprendizaje automático.
- Comparar la predicción del modelo de machine learning con la obtenida mediante reglas clínicas derivadas de una tesis doctoral.
- Analizar las diferencias entre ambos enfoques utilizando la misma entrada de datos.
- Exportar los resultados obtenidos.
- Incorporar nuevos datos clínicos al sistema.

Además, el diseño del pipeline permite, a futuro, reentrenar los modelos automáticamente al añadir nuevos datos, facilitando la evolución del sistema conforme se disponga de más información.

### Arquitectura

La aplicación web está estructurada en dos componentes principales:

- **Backend**: encargado de la lógica de negocio, carga de modelos y generación de predicciones.
- **Frontend**: interfaz de usuario que permite introducir datos clínicos, visualizar resultados y comparar modelos.

El backend utiliza los modelos exportados en el pipeline (`outputs/final_model_export/`) para realizar predicciones en tiempo real.

--- 

## Estructura del repositorio

```text
TFG-Donacion-Renal-ml-web/
├── data/
│   ├── raw/                      # Datos originales proporcionados por el equipo médico
│   ├── processed/                # Datasets limpios, sintéticos y reportes de limpieza
│   └── external/                 # Datos externos complementarios (si aplica)
├── docs/                         # Documentación técnica del proyecto
├── outputs/
│   ├── exploratory_analysis/     # Gráficas y reportes del análisis exploratorio
│   ├── model_training/           # Resultados del entrenamiento (métricas, modelos, CV)
│   ├── model_evaluation/         # Comparativa final de modelos y métricas
│   └── final_model_export/       # Modelos finales exportados (mid y transfer)
├── src/
│   ├── 01_data_cleaning/         # Limpieza de datos y generación de datasets (real y sintético)
│   ├── 02_exploratory_analysis/  # Análisis exploratorio y generación de reportes
│   ├── 03_model_training/        # Entrenamiento de modelos y búsqueda de hiperparámetros
│   ├── 04_model_evaluation/      # Evaluación final y selección de modelos por dataset
│   ├── 05_final_model_export/    # Reentrenamiento y exportación de los modelos finales
│   ├── common/                   # Utilidades compartidas entre módulos
│   └── main.py                   # Orquestador global del pipeline
├── tests/                        # Tests (en desarrollo)
├── web/
│   ├── backend/                  # Backend de la aplicación web (API y lógica de predicción)
│   └── frontend/                 # Interfaz de usuario para introducir datos y visualizar resultados
├── pyproject.toml                # Configuración del proyecto y dependencias
├── uv.lock                       # Versionado reproducible de dependencias
└── README.md                     # Este documento
```

---

## Requisitos

Para ejecutar el proyecto se recomienda:

- Python 3.11 o superior  
- uv para la gestión del entorno y dependencias  

---

## Instalación del entorno

**1.** Clonar el repositorio:

```bash
git clone https://github.com/maritriv/TFG-Donacion-Renal-ml-web.git
cd TFG-Donacion-Renal-ml-web
```

**2.** Instalar `uv` (si no está instalado):

```bash
pip install uv
```

**3.** Instalar dependencias base:

```bash
uv sync
```

**4.** Instalar dependencias para generar datos sintéticos:

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
```

Actualmente se utiliza la hoja **Donante**.

---

## Salidas principales

### Datos procesados

En `data/processed/` se generan, entre otros:

- `dataset_mid_clean.csv` → dataset limpio para el punto medio de predicción  
- `dataset_transfer_clean.csv` → dataset limpio para el momento de transferencia  
- `dataset_mid_synthetic.csv` → datos sintéticos generados para el escenario `mid`  
- `dataset_transfer_synthetic.csv` → datos sintéticos generados para el escenario `transfer`  
- `cleaning_report.json` → resumen del proceso de limpieza (valores nulos, transformaciones...)  
- `synthetic_report.json` → información sobre la generación de datos sintéticos  

---

### Análisis exploratorio

En `outputs/exploratory_analysis/` se generan:

- histogramas → distribución de variables relevantes  
- mapas de correlación → relación entre variables  
- distribuciones de la variable objetivo → balance de clases  
- `eda_report.json` → resumen automático del análisis exploratorio  

---

### Entrenamiento

En `outputs/model_training/` se generan:

- métricas de validación cruzada → rendimiento medio de cada modelo  
- resultados de búsqueda de hiperparámetros → combinaciones evaluadas  
- `best_model.joblib` → mejor modelo encontrado en cada experimento  
- métricas sobre conjunto de test → evaluación inicial fuera de entrenamiento  

---

### Evaluación final

En `outputs/model_evaluation/` se generan:

- comparativa final entre modelos → ranking de modelos por dataset  
- métricas finales (`mid` y `transfer`) → rendimiento en test del modelo seleccionado  
- matrices de confusión → análisis de errores de clasificación  
- `final_comparison_report.json` → resumen estructurado de la comparación final  

---

### Modelos finales

En `outputs/final_model_export/` se exportan los modelos finales reentrenados:

- `mid/final_model.joblib` → modelo final para predicción en punto medio  
- `mid/final_model_metadata.json` → información sobre entrenamiento y datos usados  
- `mid/final_metrics.json` → métricas finales del modelo  

- `transfer/final_model.joblib` → modelo final para predicción en transferencia  
- `transfer/final_model_metadata.json` → información del modelo y entrenamiento  
- `transfer/final_metrics.json` → métricas finales del modelo  

- `final_models_report.json` → resumen global de los modelos exportados  

---

## Resultados finales actuales

De acuerdo con la última ejecución completa del pipeline, se seleccionó y exportó un modelo final independiente para cada momento clínico:

### Predicción en punto medio (`mid`)

- **modelo seleccionado:** `logistic_regression`
- **experimento:** `real`
- **semilla:** `999`
- **F1-score en evaluación final:** `0.6667`
- **recall en evaluación final:** `0.8`

### Predicción en transferencia (`transfer`)

- **modelo seleccionado:** `logistic_regression`
- **experimento:** `real_plus_synthetic`
- **semilla:** `999`
- **F1-score en evaluación final:** `0.8333`
- **recall en evaluación final:** `1.0`

Estos resultados muestran que el mejor modelo no fue el mismo escenario experimental para ambos momentos clínicos. En el caso de `mid`, el mejor rendimiento se obtuvo utilizando únicamente datos reales, mientras que en `transfer` el mejor resultado se consiguió combinando datos reales y sintéticos.

> Estos resultados deben interpretarse dentro del contexto del tamaño muestral disponible y del carácter académico-experimental del proyecto.

---

## Ejecución de la aplicación web

La aplicación web está implementada como un frontend en HTML y JavaScript (ES modules), por lo que necesita ejecutarse sobre un servidor local.

### Opción 1 · Servidor local con Python (recomendada)

Desde la raíz del proyecto:

```bash
cd web/frontend
uv run -m http.server 8000
```

Abrir en el navegador:
`http://localhost:8000/html/index.html`

⚠️ Es importante acceder siempre a través de /html/index.html y no abrir el archivo directamente (file://), ya que los módulos de JavaScript y las rutas no funcionarán correctamente.

### Opción 2 · Live Server (VS Code)

1. Instalar la extensión Live Server

Para ello:

    - Abrir Visual Studio Code
    - Ir a la pestaña de extensiones (icono de bloques en la barra lateral izquierda)
    - Buscar **"Live Server"**
    - Instalar la extensión desarrollada por *Ritwick Dey*


2. Abrir el proyecto en VS Code, desde la raíz del proyecto:
```bash
code .
```

3. Click derecho sobre:
`web/frontend/html/index.html`

4. Seleccionar "Open with Live Server"

Se abrirá automáticamente en el navegador, normalmente en:
`http://127.0.0.1:5500/html/index.html`

---

## Flujo de uso de la aplicación web

La aplicación web permite gestionar usuarios y realizar predicciones clínicas en distintos momentos del proceso, integrando tanto modelos de aprendizaje automático como reglas clínicas.

### 1. Autenticación

Al acceder a la aplicación (`/html/index.html`), el usuario se encuentra con una pantalla de inicio de sesión donde puede:

- iniciar sesión con su cuenta,
- registrarse si no dispone de una,
- recuperar la contraseña en caso de olvido.

Una vez autenticado, el usuario accede a la aplicación según su rol (Médico o Administrador).


### 2. Pantalla principal

Existen dos tipos de usuarios:

- **Médico**
- **Administrador**

En ambos casos, la pantalla principal muestra:

- un gráfico tipo *donut* con el número total de predicciones realizadas,
- el porcentaje de predicciones válidas y no válidas,
- un menú de usuario para editar datos personales o cerrar sesión.


### 3. Funcionalidad para médicos

Los usuarios con rol médico disponen de tres acciones principales:

#### Función 1: Realizar predicción

1. Selección del momento clínico:
   - **Punto medio**
   - **Transferencia**

2. En función del momento seleccionado:
   - se carga el modelo correspondiente,
   - se muestra un formulario clínico para introducir los datos del paciente.

3. Tras enviar el formulario:
   - se calcula la predicción,
   - se muestran los resultados:
     - resultado basado en reglas clínicas,
     - resultado del modelo de machine learning,
     - indicación de si el donante es válido o no.

4. El usuario puede:
   - exportar el resultado y los parámetros en PDF,
   - volver a la pantalla principal.


#### Función 2: Historial de predicciones

Permite visualizar todas las predicciones realizadas por el médico en formato tabla.

Incluye:

- ordenación por variables (edad, momento, capnometría),
- filtrado y búsqueda de predicciones (por ejemplo, pacientes de cierta edad),
- exportación individual de predicciones en PDF,
- exportación completa del historial en formato CSV.


#### Función 3: Importar predicciones

Permite cargar un archivo CSV con nuevas predicciones. Tras validar los datos y comprobar que no existan duplicados entonces, las prediciones se incorporan al sistema.


### 4. Funcionalidad para administradores

Los usuarios con rol administrador disponen de funcionalidades adicionales:


#### Función 1: Gestión de usuarios

Permite:

- visualizar todos los usuarios registrados (médicos y administradores),
- consultar sus datos y predicciones,
- modificar sus datos personales,
- eliminar o dar de baja a usuarios.

#### Función 2: Historial global

- acceso a todas las predicciones realizadas por todos los médicos,
- mismas capacidades de filtrado, ordenación y exportación que el rol médico.


### 5. Persistencia de datos

La gestión de usuarios y predicciones se realiza mediante **Firebase**, lo que permite:

- mantener sincronizados los datos entre la aplicación web y la aplicación móvil,
- garantizar que las predicciones y registros estén disponibles independientemente del dispositivo utilizado.

---

## Estado del proyecto

Estado actual del repositorio:

- [x] limpieza y preparación de datos  
- [x] generación de datasets de modelado  
- [x] análisis exploratorio  
- [x] entrenamiento y comparación de modelos  
- [x] evaluación final  
- [x] exportación de modelos finales  
- [x] desarrollo de la aplicación web (frontend y backend)  
- [ ] validación completa en entorno real  
- [ ] batería de tests automatizados  
- [ ] despliegue final del sistema 

---

## Tecnologías utilizadas

### Modelado y procesamiento de datos
- Python  
- pandas  
- numpy  
- scikit-learn  
- xgboost  
- matplotlib  
- openpyxl  
- sdv / CTGAN (generación de datos sintéticos)  
- joblib  

### Visualización y utilidades
- rich  

### Aplicación web
- HTML  
- CSS  
- JavaScript (ES Modules)  
- Firebase (autenticación y base de datos)  

---

## Consideraciones

- Este repositorio forma parte de un TFG con aplicación en un contexto clínico real.  
- Los modelos desarrollados tienen fines académicos y de apoyo a la decisión, no sustituyen la valoración médica.  
- La validez de los resultados depende del tamaño, calidad y representatividad del dataset proporcionado.  

---

## Autora

**Marina Triviño de las Heras**

Estudiante de caurto año del grado en Ingeniería de Datos e Inteligencia Artificial  
Universidad Complutense de Madrid  

---

## Repositorios relacionados

- Aplicación móvil: [TFG-Donacion-Renal](https://github.com/maritriv/TFG-Donacion-Renal)
