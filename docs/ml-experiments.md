# Registro de experimentos del pipeline

Bitácora de lo probado, con resultados negativos incluidos, para no repetir callejones
sin salida.

Las secciones de julio de 2026 miden el clasificador BERT sobre la muestra de test de
PubHealth (300 verdadera / 300 falsa / 201 mixture, seed 42) vía
`ml/evaluation/evaluate_classifier.py`. A partir de agosto de 2026 el dataset es
HealthVer, la medida limpia es el conjunto dorado `data/gold_es.jsonl` vía
`ml/evaluation/evaluate_pipeline.py --partition gold`, y **el clasificador ya no forma
parte del pipeline** (ver «Retirada del clasificador BERT»).

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

## Diagnóstico: el pipeline destruye ~30 puntos frente a su propio clasificador (2026-07-15)

BioBERT aplicado directamente al texto crudo de las mismas 150 muestras del eval
solo-médico: **90.3% de accuracy firme** (62 firmes, FP=4, FN=2, cobertura 41.3%)
frente al 60.5% del pipeline completo. El subconjunto médico no es más difícil para
el clasificador; es la maquinaria del pipeline la que pierde la accuracy. Trazando
muestras erróneas por etapas:

- «Tests show King Tut died from malaria, study says» → directo verdadera 0.86;
  el extractor lo reduce a «King Tut died from malaria» → falsa 0.71.
- «Heparin recalled in France, Italy, Denmark: report» → directo verdadera 0.86;
  normalizado a declarativa sin atribución → falsa 0.51.
- El titular de la FDA/Farxiga pasa de verdadera 0.82 a falsa 0.54 con una
  paráfrasis casi idéntica.

Causa raíz: **BioBERT lee registro, no contenido**. Los marcadores de evidencialidad
("study says", "tests show", ": report") codifican verdadera; la aserción declarativa
desnuda codifica falsa (estilo bulo viral). El extractor y el traductor ("inglés
clínico") normalizan sistemáticamente hacia ese registro falso-codificado: de ahí la
explosión de FP (precisión falsa 48%) y que pipeline y clasificador solo coincidan
en 24 de 33 veredictos firmes comunes. El clasificador es frágil a la paráfrasis; el
pipeline se lo expone en cada muestra.

## Sustitución del dataset: PubHealth → HealthVer (2026-08-30)

PubHealth quedó descartado por dos motivos medidos, no por intuición:

- **Separable por estilo**: un clasificador sobre features de superficie (longitud,
  puntuación, mayúsculas) más TF-IDF distingue `verdadera` de `falsa` con AUC 0.72–0.81
  sin leer el contenido. Etiqueta procedencia, no veracidad; es la misma fuga que
  explicaba el diagnóstico de 2026-07-15 («BioBERT lee registro, no contenido»).
- **80% de extracción vacía** sobre la muestra médica: los titulares periodísticos con
  atribución no sobreviven al extractor.

Además incluye política y no solo medicina, lo que contaminaba cualquier métrica de
dominio. HealthVer es exclusivamente médico y trae evidencia por afirmación.

**Error propio durante la conversión, corregido**: al mapear HealthVer a las etiquetas
del pipeline se colapsó cualquier afirmación con una fuente que la contradijera a
`falsa`. Eso mal etiquetó el 26% de validation. La regla correcta manda la evidencia
mixta a `incierta`: la partición pasó de 71/89/70 a 71/48/111.

**Auditoría de desacuerdos**: revisando a mano los casos en que el pipeline discrepa de
HealthVer, **~60% son culpa del benchmark**, no del pipeline. HealthVer sirve para
comparar arms entre sí, pero su techo de ruido impide leer su accuracy como capacidad.

## Conjunto dorado escrito a mano (2026-08-31)

`backend/data/gold_es.jsonl`: 100 afirmaciones, 50 temas × (1 verdadera + 1 falsa), en
español y sin ambigüedad deliberada. JSONL para que el diff sea revisable.

Existe porque el ruido de etiqueta de HealthVer impedía separar *incapacidad del
pipeline* de *error del benchmark*. El contraste es inmediato: sobre el conjunto dorado
el pipeline detecta 20/50 afirmaciones falsas, frente a 2/19, 0/19 y 1/19 en las
sucesivas medidas sobre HealthVer. La señal existía; HealthVer la enterraba.

Sesgo conocido: el conjunto lo escribimos nosotros, así que hereda nuestra idea de qué
es una afirmación verificable, y sus 50 bulos son bulos *conocidos* (justo los que la
literatura biomédica primaria no indexa; ver más abajo).

## Prompts: juez v3 y extractor v4 (2026-08-30 / 2026-08-31)

**Juez v2 → v3 — hacía coincidencia temática, no detección de postura.** Instrumentando
al juez se vio que respondía `supports` a resúmenes que *refutaban* la afirmación: le
bastaba con que hablaran del mismo tema. Ésta era la causa raíz de que el pipeline no
detectara afirmaciones falsas. v3 añade tratamiento explícito de polaridad («compartir
tema NO es respaldar»), el caso de la afirmación negativa desmentida y tres ejemplos
resueltos. En casos controlados pasó de 2/4 a 4/4.

Nota: la mejora **no transfiere del todo a resúmenes reales**. En el conjunto dorado
quedan 9 afirmaciones falsas llamadas `verdadera` por este mismo mecanismo.

**Extractor v3 → v4 — el ámbito era demasiado estrecho.** Rechazaba 8/100 afirmaciones
del conjunto dorado devolviendo lista vacía (bail en <1.1 s): fisiología («el hígado
elimina los productos de desecho»), neurociencia popular («solo usamos el 10% del
cerebro»), salud mental, y bulos de contagio (5G). v4 amplía el ámbito a fisiología y
anatomía, salud mental, transmisión y seguridad alimentaria, y añade una regla explícita
para **no descartar creencias populares por parecer obviamente falsas: verificarlas es
la tarea**. Recupera 5 de las 8.

Las 3 que siguen sin extraerse son genuinamente discutibles como afirmación verificable
y se dejan así.

## Retirada del clasificador BERT (2026-08-31) — dos pruebas pareadas

El veredicto pasa a derivarse solo de la postura de la literatura recuperada. Medido con
dos comparaciones pareadas independientes:

**HealthVer validation (59 muestras comunes)**

| | acc. firme | verdadera→falsa |
|---|---|---|
| con BERT | 34.4% | 13 |
| sin BERT | 52.9% | 4 |

McNemar exacto: 14 a favor de sin-BERT, 3 a favor de con-BERT, **p = 0.0127**.

**Conjunto dorado (100 muestras, extractor v4 y juez v3 fijos en ambos arms)**

| | acc. | firmes | acc. firme | incierta | recall falsas | **verdadera→falsa** |
|---|---|---|---|---|---|---|
| con BERT | 42/100 | 64 | 65.6% | 34 | 41/50 | **17** |
| sin BERT | **69/100** | 80 | **86.2%** | 18 | 23/50 | **2** |

McNemar exacto: 47 a favor de sin-BERT, 20 a favor de con-BERT, **p = 0.0013**.

**La trampa a no repetir**: BERT tiene *mejor* recall de falsas (41/50 vs 23/50). Lo
compra llamando falsas a 17 afirmaciones verdaderas. Un sesgo hacia `falsa` puntúa bien
en un conjunto que es mitad bulos y es inaceptable en una herramienta que lee un
paciente. La accuracy sobre veredictos firmes (86.2% vs 65.6%) es la métrica honesta:
BERT no sabía más, adivinaba más fuerte.

Coherente con la medida aislada previa: BERT solo sobre HealthVer validation da 42.31%,
por debajo del 60.6% de un predictor constante «todo es verdad».

Se conserva `app/tools/model_tool.py` y los scripts `ml/evaluation/evaluate_classifier.py`
y `evaluate_factcheck.py` para que los experimentos de esta bitácora sigan siendo
reproducibles; lo que se retira es BERT de la ruta de servicio.

**El traductor NO se retira.** Se creía que solo alimentaba al clasificador, pero
`investigator.py` corta la recuperación de evidencia si `translated_statements` viene
vacío y recorre esa lista para construir las consultas. Es la espina dorsal de la
recuperación, que ahora es la *única* fuente del veredicto.

## La ausencia de evidencia no es prueba de falsedad (2026-08-31)

Al estrechar la banda de incertidumbre de ±0.10 a ±0.05 la accuracy del conjunto dorado
saltó de 55 a 79. Casi todo el salto era un artefacto y se revirtió parcialmente.

Con suavizado de Laplace, una afirmación sin ninguna fuente pronunciada puntúa
exactamente 0.5. Con `FAKE_THRESHOLD = 0.40` y banda ±0.05 ese 0.5 queda *por encima* de
la banda, así que **«no hemos encontrado nada» se leía como «es falso»**. La banda
antigua terminaba justo en 0.50 y por eso el problema estaba oculto.

27 de las 100 muestras no tienen ninguna postura: la regla las llamaba todas `falsa`,
acertando 20 y fallando 7. Puntúa bien solo porque el conjunto dorado está hecho de
bulos conocidos, que son exactamente los que la literatura biomédica primaria no indexa.
Lo que producía:

```text
La fiebre es una respuesta del organismo frente a una infeccion.          -> FALSA
El uso innecesario de antibioticos favorece la aparicion de resistencias  -> FALSA
La reanimacion cardiopulmonar precoz puede aumentar la supervivencia      -> FALSA
La ingestion de lejia puede provocar quemaduras graves                    -> FALSA
```

`_has_stance_evidence` manda ahora esos casos a `incierta`, y el promedio global solo
recorre las afirmaciones sobre las que la literatura se pronuncia. Cuesta 10 puntos de
titular (79 → 69) y baja las verdaderas-llamadas-falsas de 7 a 2. Se acepta el cambio:
79 que llama falsa a la fiebre no vale nada.

Descomposición honesta de la mejora 55 → 69:

| componente | aporte | ¿sólido? |
|---|---|---|
| recuperación de extracción (prompt v4) | +5 | sí |
| estrechar la banda sobre señal real | ~+6 | sí |
| ausencia de evidencia como `falsa` | +13 neto | **no, revertido** |

## No volver a intentar

- **Cambiar de modelo base con entrada solo-claim**: cuatro arquitecturas convergen en
  ~87–89%. El techo lo pone la tarea (clasificar veracidad sin evidencia aprende
  estilo, no verdad), no la arquitectura.
- **Más épocas / entrenar más**: las épocas 2–3 sobreajustan; early stopping ya
  captura el pico dentro de la época 1–2.
- **Afinar más los márgenes**: el barrido es casi plano; subir fm 0.25→0.35 compra
  ~+0.9 de accuracy a cambio de −3 de cobertura y ahí se acaba el recorrido.
- **Plegar `mixture` en `falsa`** o cualquier reetiquetado que contamine una clase.
- ~~**Recalibrar la banda global de veredicto**~~: **superado el 2026-08-31**. Con el
  veredicto derivado de la evidencia, estrechar la banda a ±0.05 sí compra accuracy
  (la banda ±0.10 dejaba 29/100 muestras en «incierta» por evidencia escasa, no
  ambigua). El barrido de julio describía el clasificador, no el pipeline actual.
- **Reentrenar BERT sobre HealthVer y volver a meterlo en el pipeline**: dos pruebas
  pareadas independientes (p = 0.0127 y p = 0.0013) dicen que sobra, y aislado da 42.31%
  frente al 60.6% de un predictor constante. El techo es el de la tarea, no el del
  entrenamiento.
- **Retirar el traductor**: no alimentaba solo al clasificador. `investigator.py` corta
  la recuperación si `translated_statements` viene vacío; sin traductor no hay evidencia
  y sin evidencia no hay veredicto.
- **Tratar la ausencia de evidencia como falsedad**: puntúa bien en un conjunto lleno de
  bulos conocidos y produce «la fiebre es falsa». Cualquier regla que premie el silencio
  de la literatura está midiendo la cobertura de PubMed, no la veracidad.

## Pendiente con mayor expectativa

Ordenado por dónde están realmente los 31 errores del conjunto dorado (2026-08-31):

1. **Cobertura de recuperación** — 17/100 afirmaciones falsas acaban en `incierta`
   porque no se recupera ninguna evidencia. Es el mayor cubo con diferencia. Son bulos
   populares (homeopatía, microondas, azúcar y tumores, desodorantes con aluminio, ocho
   vasos de agua) que la literatura biomédica primaria no aborda: haría falta un segundo
   canal de recuperación orientado a corpus de verificación, no a investigación
   original, o aceptar `incierta` y reportar la cobertura con honestidad.
2. **El juez sigue leyendo literatura temática como respaldo** — 9/100 falsas llamadas
   `verdadera` con 4–6 fuentes `supports` y ninguna `contradicts`. El prompt v3 lo
   arregló en resúmenes escritos a mano pero no transfiere del todo a los reales.
3. **Alinear `FAKE_THRESHOLD` con el punto neutro** — el score suavizado es neutro en
   0.5 pero el umbral está en 0.40, así que la evidencia *equilibrada* (1 a favor, 1 en
   contra) se lee como `falsa`. Cuesta ~2 puntos en el conjunto dorado (ruido a n=100),
   pero es corrección de razonamiento, no de métrica.
