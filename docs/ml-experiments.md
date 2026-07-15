# Registro de experimentos del clasificador

Bitácora de lo probado sobre el clasificador BERT, con resultados negativos incluidos,
para no repetir callejones sin salida. Métricas sobre la misma muestra de test de
PubHealth (300 verdadera / 300 falsa / 201 mixture, seed 42) vía
`ml/evaluation/evaluate_classifier.py`, salvo indicación contraria.

## Historial de mejoras (jul 2026)

| Modelo | Acc. firme | verdadera→falsa | falsa→verdadera | Abstención |
|---|---|---|---|---|
| 2 clases original (minúsculas, mixture→falsa) | 79.7% | 34.7% | 6.0% | — |
| 3 clases (mixture→incierta, pesos por clase) | 84.1% | 25.3% | 2.8% | 12.8% |
| + márgenes de decisión (0.25/0.10) | 84.7% | 23.7% | 2.9% | 15.2% |
| + fix del learning rate (2e-5 real) — **desplegado** | **87.9%** | **17.3%** | 1.0% | 24.5% |

Qué corrigió cada salto:

- **3 clases**: plegar `mixture` en `falsa` metía ~32% de ruido de etiqueta en la clase
  positiva y era la causa principal del sesgo verdadera→falsa.
- **Sin minúsculas**: BioBERT es *cased*; `clean_text` pasaba todo a minúsculas y
  degradaba la señal. No reintroducir `lower()` en el preprocesado.
- **Selección por macro-F1**: seleccionar checkpoint por F1 binaria premiaba el sesgo
  hacia `falsa`.
- **Learning rate**: `LEARNING_RATE` nunca se pasaba a `TrainingArguments`; todos los
  entrenamientos previos corrieron al 5e-5 por defecto de HF aunque los metadatos
  dijeran 2e-5. Con 2e-5 real + eval cada 200 pasos + early stopping (paciencia 3),
  el mejor checkpoint fue el paso 1200 (val macro-F1 0.625).

## Bake-off de modelos base (2026-07-14) — BioBERT ganó

Receta idéntica (3 clases, pesos, label smoothing 0.1, LR 2e-5, early stopping),
márgenes barridos por modelo en validación y reportados en test (fm=0.35 para todos):

| Modelo base | Acc. firme (test) | verdadera→falsa | falsa→verdadera | Cobertura |
|---|---|---|---|---|
| dmis-lab/biobert-v1.1 (**desplegado**) | **88.7%** | **15.3%** | 1.0% | 72.5% |
| FacebookAI/roberta-base | 87.7% | 18.7% | **0.7%** | 78.3% |
| microsoft/deberta-v3-base | 87.2% | 15.7% | 2.3% | 70.5% |
| microsoft/BiomedNLP-BiomedBERT (PubMedBERT) | 86.7% | 17.7% | 2.7% | 76.3% |

Notas:

- La ventaja de RoBERTa en validación **no transfirió a test**. Sigue siendo la opción
  de mayor cobertura (86.3% acc. con 83.8% de cobertura sin márgenes) si algún día
  sobran los "Dudoso", pero pierde en falsos positivos.
- DeBERTa-v3 arranca muy lento con LR 2e-5 / warmup 500 (val F1 0.606); necesitaría
  su propia receta para competir y no la vale a igualdad de presupuesto.
- Su checkpoint de HF viene en fp16: `train.py` fuerza `dtype=torch.float32` al cargar.
- El tokenizador de DeBERTa requiere `sentencepiece` + `protobuf` (no están en
  `pyproject.toml` porque perdió el bake-off).

## Renormalización de fake_prob en el pipeline (2026-07-14) — mejora parcial

Fix en `health_expert`: cada veredicto firme por afirmación aporta
`p_falsa / (p_falsa + p_verdadera)` al promedio global en vez de la confianza softmax
de 3 clases (que, diluida en ~0.4–0.5, hacía caer en "incierta" veredictos firmes del
detector). Medido con `ml/evaluation/evaluate_pipeline.py` (150 muestras test, seed 42),
comparación pareada pre/post sobre los mismos textos:

| | Pre | Post |
|---|---|---|
| Cobertura (firmes / con afirmaciones) | 32.4% | 46.4% |
| Accuracy firme | 86.4% (3 err / 22) | 78.1% (7 err / 32) |
| Firmes correctos absolutos | 19 | 25 |
| Firmes incorrectos absolutos | 3 | 7 |

Notas:

- De las 10 conversiones incierta→firme, 6 correctas y 4 incorrectas: la zona marginal
  que desbloquea la renormalización hereda el sesgo verdadera→falsa del clasificador.
- **Los 7 errores post tienen confianza < 0.65; los 13 veredictos con ≥ 0.65 aciertan
  todos.** La banda global (0.30–0.50) se calibró para la escala diluida; con la escala
  renormalizada hay que recalibrarla (en validación, no en test).
- El 54% de las muestras (81/149) terminó "sin afirmaciones": el extractor (llama3) no
  extrae claims de titulares cortos tipo PubHealth. Es el mayor cuello de botella del
  pipeline y es independiente del clasificador.

## Mezcla de fake_prob con la postura de la evidencia (2026-07-15) — neutra en la práctica

Cambio: cada afirmación mezcla su `fake_prob` con la postura de la literatura
(`contradicts / (supports + contradicts)`, peso `0.5 · min(n, 3)/3` en
`blend_fake_prob_with_stance`), sustituyendo al ablandador defensivo
`soften_verdict_with_opposition` (mantener ambos contaría dos veces la misma señal).
La evidencia ya puede en teoría invertir un veredicto o resolver una abstención.
Medido pareado sobre las mismas 150 muestras test (seed 42,
`results/eval_pipeline_{post,stance}.jsonl`):

| | Pre (renorm) | Post (stance) |
|---|---|---|
| Accuracy firme | 78.1% (25/32) | 80.0% (24/30) |
| Cobertura | 46.4% | 42.9% |
| FP / FN | 6 / 1 | 6 / 0 |

Notas:

- **En la práctica se comportó como el ablandador que sustituye**: 0 inversiones y
  0 abstenciones resueltas; solo movió 3 firmes a incierta (1 error corregido, el
  único FN, y 2 aciertos perdidos). La señal de postura es demasiado escasa: llegar
  al peso máximo exige 3 fuentes pronunciadas sobre la misma afirmación, y el juez
  marca la mayoría como `inconclusive`.
- La transición sin_afirmaciones→verdadera restante es ruido del extractor entre
  ejecuciones, no efecto del cambio.
- **La separación por confianza se repite**: los 6 errores tienen conf < 0.65 y los
  15 veredictos con ≥ 0.65 aciertan todos. Recalibrar la banda global sigue siendo
  el ajuste pendiente más barato (en validación, no en test).
- Para que la evidencia pague en accuracy hace falta más señal pronunciada, no más
  peso: mejorar el juez de relevancia (que se moje más en supports/contradicts) o
  pasar al entrenamiento con evidencia (`claim [SEP] evidencia`).

## Barrido de la banda global de veredicto (2026-07-15) — la banda actual ya es óptima

Hipótesis (dos evaluaciones de test seguidas): todos los errores caían con confianza
< 0.65 y todo veredicto ≥ 0.65 acertaba, así que recalibrar la banda (0.30–0.50 sobre
`fake_avg`) parecía la mejora más barata. Para barrer sin re-ejecutar el pipeline,
`evaluate_pipeline.py` ahora persiste la `fake_avg` cruda por muestra (reconstruida
invirtiendo la atenuación por cobertura; el barrido reproduce los 63 veredictos
almacenados con 0 desajustes). Medido en **validación** (150 muestras, seed 42,
`results/eval_pipeline_validation.jsonl`):

| Banda (lower, upper) | Firmes | Aciertos | Errores | Acc. | Cobertura |
|---|---|---|---|---|---|
| (0.30, 0.50) — actual | 33 | 24 | 9 | 72.7% | 52.4% |
| (0.275, 0.50) | 32 | 24 | 8 | 75.0% | 50.8% |
| (0.275, 0.65) | 31 | 23 | 8 | 74.2% | 49.2% |
| (0.275, 0.775) | 26 | 19 | 7 | 73.1% | 41.3% |

Notas:

- **La separación por confianza 0.65 de test NO replica en validación**: era suerte
  de muestra pequeña (6–7 errores). En validación hay errores hasta conf 0.68 y los
  8 FP mantienen `fake_avg` alto hasta ~0.775: subir el umbral pierde aciertos al
  mismo ritmo que errores.
- La única mejora (lower 0.30→0.275) elimina exactamente 1 muestra errónea: ajustar
  por un solo dato es sobreajuste, no señal. **Se mantiene la banda actual.**
- Los FP restantes son errores seguros del clasificador (afirmaciones verdaderas con
  `fake_avg` > 0.75), el mismo sesgo verdadera→falsa de siempre: ninguna banda los
  separa. La vía sigue siendo mejorar la señal (evidencia en el entrenamiento).

## "Sin afirmaciones" es filtrado de dominio, no fallo del extractor (2026-07-15)

Revisadas una a una las 87 muestras de validación sin afirmaciones extraídas:
~2/3 son claramente ajenas al dominio (fact-checks políticos, leyendas urbanas,
noticias generales — PubHealth arrastra PolitiFact/Snopes) y la mayoría del resto
son titulares de política sanitaria sin ninguna afirmación médica verificable.
Fallos reales del extractor: ~5–8 (titulares tipo estudio, p. ej. "Study adds to
evidence of vaccine safety"). Corrige la conclusión del 2026-07-14: el 54% de
descartes NO es el mayor cuello de botella del pipeline, es en su mayoría el
comportamiento correcto para el alcance médico de VeriTrust. Si se quiere medir
solo el dominio médico, el ajuste va en el muestreo de la evaluación (filtrar
PubHealth a afirmaciones médicas), no en el extractor.

## Muestreo solo-médico en la evaluación (2026-07-15) — baseline honesto, y es peor

Nuevo `--medical-only` en `evaluate_pipeline.py`: un juez LLM (modelo del juez de
relevancia, no el del extractor, para que los fallos del extractor sigan aflorando)
filtra el muestreo a textos con cuestión médica verificable; prompt en
`ml/evaluation/prompts.yaml`. Los metadatos de PubHealth no sirven como filtro
(subjects: 45% vs 39% de extracción entre etiquetadas médicas y no; fact_checkers
son firmas de periodistas). Primera medición (test, 150 muestras, seed 42,
`results/eval_pipeline_test_medical.jsonl`; filtro: 526 juzgadas → 150):

| | Mezclado (stance, 2026-07-15) | Solo-médico |
|---|---|---|
| Sin afirmaciones | 53% (80/150) | **12% (18/150)** |
| Veredictos firmes | 30 | 43 |
| Accuracy firme | 80.0% | **60.5%** |
| Cobertura | 42.9% | 32.6% |
| FP / FN | 6 / 0 | 14 / 3 |

Notas:

- **Los evals mezclados inflaban la accuracy**: las muestras no médicas que sí
  pasaban el extractor (leyendas urbanas, política) son estilísticamente fáciles.
  En dominio médico real el lado "falsa" tiene precisión 48% (14 FP de 27) — los
  errores son titulares sanitarios verdaderos (aprobaciones FDA, hallazgos de
  estudios) marcados como falsos: el sesgo verdadera→falsa a plena potencia.
- La abstención sube al 67% de las muestras con afirmaciones: el pipeline se moja
  poco justo en su dominio.
- Errores con confianza 0.66–0.73: entierra definitivamente la "separación 0.65".
- **Este es el baseline a batir** (60.5% acc, 32.6% cobertura). Refuerza que la
  palanca real es el clasificador con evidencia (`claim [SEP] evidencia`), no la
  agregación.

## No volver a intentar

- **Cambiar de modelo base con entrada solo-claim**: cuatro arquitecturas convergen en
  ~87–89%. El techo lo pone la tarea (clasificar veracidad sin evidencia aprende
  estilo, no verdad), no la arquitectura.
- **Más épocas / entrenar más**: las épocas 2–3 sobreajustan; early stopping ya
  captura el pico dentro de la época 1–2.
- **Afinar más los márgenes**: el barrido es casi plano; subir fm 0.25→0.35 compra
  ~+0.9 de accuracy a cambio de −3 de cobertura y ahí se acaba el recorrido.
- **Plegar `mixture` en `falsa`** o cualquier reetiquetado que contamine una clase.
- **Recalibrar la banda global de veredicto**: barrida en validación (2026-07-15),
  la banda (0.30, 0.50) ya está en el óptimo práctico; los errores restantes tienen
  `fake_avg` alto y ningún umbral los separa de los aciertos.

## Pendiente con mayor expectativa

1. **Entrenamiento con evidencia** (`claim [SEP] evidencia`, estilo NLI): la única vía
   con margen real; ataca los errores no verificables desde el claim.
2. LR 1e-5 con 4–5 épocas: pulido menor sobre BioBERT, nunca probado, expectativa baja.
3. Reequilibrar pesos hacia `verdadera`: los errores siguen asimétricos (52 FP vs 3 FN).
