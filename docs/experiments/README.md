# Registro de experimentos del pipeline

Bitácora de lo probado, con resultados negativos incluidos, para no repetir callejones
sin salida. Este README resume el estado actual; las entradas fechadas, un archivo por
mes, guardan el porqué. Una entrada nueva va al final del archivo del mes en curso y,
si cambia el estado, se refleja aquí.

Desde agosto de 2026 el dataset es HealthVer, la medida limpia es el conjunto dorado
`data/gold_es.jsonl` vía `evaluation/evaluate_pipeline.py --partition gold`, y **el
clasificador BERT ya no forma parte del pipeline** (ver «Retirada del clasificador BERT»
en [2026-08.md](2026-08.md)). Desde el 2026-10-12 el arnés vive en `evaluation/`; las
entradas anteriores citan `ml/`, su ruta de entonces.

## Cómo medir

Cada fila del checkpoint guarda en `evidence` la evidencia bruta de cada búsqueda.
`--replay-evidence <ckpt>` sirve esas búsquedas desde la grabación, también las caídas,
y solo consulta en vivo las que no encuentra:

```bash
uv run --directory backend --extra evaluation python -m evaluation.evaluate_pipeline --partition gold --limit 100 --checkpoint results/base.jsonl
uv run --directory backend --extra evaluation python -m evaluation.evaluate_pipeline --partition gold --limit 100 --checkpoint results/variante.jsonl --replay-evidence results/base.jsonl
```

- **Cambios en el juez o en la regla de veredicto**: extractor y traductor corren a
  temperatura 0, así que las consultas se repiten y casi toda la evidencia se reproduce.
- **Cambios en extractor o traductor**: las consultas cambian y esas búsquedas van en
  vivo. La línea `Evidencia : N/M búsquedas reproducidas` del informe dice cuántas se
  reprodujeron; si son pocas, la comparación no está pareada en evidencia.
- **No fija al juez**: con la evidencia congelada, la variación que queda entre corridas
  es la del propio LLM, que sí es parte de lo que se mide.

Los checkpoints anteriores al 2026-09-22 no guardan evidencia bruta y no sirven de base.

Para comparar **solo el juez**, `evaluation.evaluate_judge` vuelve a juzgar las
afirmaciones y fuentes candidatas de un checkpoint del pipeline, sin extractor ni
traductor: solo carga el modelo del juez. Toma las muestras de una afirmación (con
varias, la fila no dice qué búsquedas son de cuál) y elige proveedor y modelo por
entorno, como el pipeline:

```bash
OLLAMA_JUDGE_MODEL=gemma4:12b uv run --directory backend --extra evaluation python -m evaluation.evaluate_judge --cases results/base.jsonl --checkpoint results/judge_gemma4.jsonl
```

`--minutes N` deja de empezar casos pasado ese tiempo y la corrida se reanuda después.

## No volver a intentar

- **Afinar el clasificador solo-claim** (otro modelo base, más épocas, más márgenes):
  cuatro arquitecturas convergen en ~87–89%. El techo lo pone la tarea (clasificar
  veracidad sin evidencia aprende estilo, no verdad), no la arquitectura. Detalle en
  [2026-07-bert-pubhealth.md](2026-07-bert-pubhealth.md).
- **Plegar `mixture` en `falsa`** o cualquier reetiquetado que contamine una clase.
- **Reentrenar BERT sobre HealthVer y volver a meterlo en el pipeline**: dos pruebas
  pareadas independientes (p = 0.0127 y p = 0.0013) dicen que sobra, y aislado da 42.31%
  frente al 60.6% de un predictor constante. El techo es el de la tarea, no el del
  entrenamiento. Desde el 2026-09-01 el código ya no está en el árbol: habría que
  recuperarlo de `a95e318` primero, que es fricción a favor.
- **Retirar el traductor**: no alimentaba solo al clasificador. `investigator.py` corta
  la recuperación si `translated_statements` viene vacío; sin traductor no hay evidencia
  y sin evidencia no hay veredicto.
- **Tratar la ausencia de evidencia como falsedad**: puntúa bien en un conjunto lleno de
  bulos conocidos y produce «la fiebre es falsa». Cualquier regla que premie el silencio
  de la literatura está midiendo la cobertura de PubMed, no la veracidad.
- **Empujar al juez a `contradicts` por prompt**: v4 lo consiguió y el reparto fue 4
  aciertos y 4 fallos (p = 0.42). Sobre una afirmación cuya literatura no la aborda, más
  decisión es más azar, no más señal. Ver la sección del 2026-09-01 en
  [2026-09.md](2026-09.md).
- **Juzgar una fuente por llamada**: con `llama3.2` es más decidido, pero llama
  `verdadera` a más falsas (25 frente a 22 de 95 sobre la misma evidencia) y cuesta una
  llamada por fuente. Ver la sección del 2026-09-30 en [2026-09.md](2026-09.md).
- **`llama3` (8B) como juez**: más decidido en la misma dirección equivocada, 30 de 33
  falsas firmes salen `verdadera`. Un modelo mayor de la misma familia no es la salida.
- **Campos de razonamiento antes de `stances`**: `claim_analysis` hunde `contradicts`
  sobre falsas de 85 a 51 y rompe verdadera→falsa = 0. Enunciar la tesis en positivo ceba
  la coincidencia temática. Con `mistral-small`, el juez etiqueta mejor sin preámbulo.
- **Ampliar el conjunto dorado con más bulos escritos a mano**: ~15 de cada 100 caen en
  el punto ciego de cobertura y sólo repetirían el mismo techo con barras de error algo
  más estrechas (SE 4.7 → 3.3 al duplicar n). Si se escriben más filas, que sea un
  conjunto **retenido**: extractor v4, juez v3 y traductor v3 se ajustaron mirando este
  conjunto, así que el 71 es en parte dentro de muestra.

## Pendiente con mayor expectativa

Reordenado tras las corridas v6 y v7 del 2026-09-01, que agotaron el juez como palanca
por prompt y por andamiaje:

1. **Cobertura de recuperación para bulos de divulgación** — el cubo mayor y el único que
   queda con mecanismo claro: ~15/100 afirmaciones sin ninguna postura porque PubMed y
   Europe PMC no indexan refutaciones de creencias populares (zanahorias y miopía, pelo
   mojado y resfriado, 10% del cerebro). Necesita una fuente que sí las cubra —Cochrane
   en lenguaje llano, MedlinePlus, NHS Health A–Z—, no un prompt. Es trabajo de
   arquitectura, no de texto.

   Riesgo a declarar antes de elegir fuente: una API de _fact-checking_ (Google Fact Check
   Tools, que se usó en `ml/evaluation/evaluate_factcheck.py` hasta su borrado) indexa
   justo los bulos **conocidos**, que es de lo que está hecho el conjunto dorado. Apuntar
   una contra el otro infla la accuracy por un motivo que no transfiere a desinformación
   nueva; es la misma forma de error que la separabilidad por estilo de PubHealth. Si se
   toma esa vía, el conjunto retenido tiene que existir antes de medirla.

2. **Capacidad del modelo juez** — resuelta en código: sobre falsas, `llama3.2` da
   1.3–1.7 `supports` por `contradicts` y `llama3` (8B) 6.0, y el cribado del 2026-10-01
   ([2026-10.md](2026-10.md)) da 0.05 con `ministral-3:14b` en Ollama, que ya es el juez
   por defecto (`ollama_judge_model`). Queda el despliegue: necesita una GPU de 16 GB y
   rehacer el presupuesto de memoria (ver [docs/deploy/ops.md](../deploy/ops.md)).
3. **Conjunto retenido de ~50 filas** — no por precisión, sino para medir cuánto del 71
   transfiere fuera de muestra. Se escribe una vez, se guarda y se mira una sola vez.
   Prerrequisito del punto 1 si la fuente elegida es de _fact-checking_.

## Ya no son palancas

La banda y el umbral de decisión (barrido plano dentro del ruido a n=100), el prompt del
juez con `mistral-small` (v4, p = 0.42; con `llama3.2` sí lo es, ver 2026-09-25 en
[2026-09.md](2026-09.md)), el orden de generación del juez (v7, p = 0.052 en contra) y
ampliar el dorado con más bulos del mismo tipo.

## Techo conocido

Con las fuentes actuales, ~15 de las 50 falsas del conjunto dorado no son verificables,
así que el máximo alcanzable ronda 85/100, no 100.

## Índice

[2026-07-bert-pubhealth.md](2026-07-bert-pubhealth.md) — clasificador BERT sobre
PubHealth, era cerrada:

- Historial de mejoras: 3 clases, sin minúsculas, learning rate real → 87.9% firme
- 2026-07-14 Bake-off de modelos base — BioBERT ganó
- 2026-07-14 Renormalización de fake_prob — mejora parcial
- 2026-07-15 Mezcla de fake_prob con la postura de la evidencia — neutra
- 2026-07-15 Barrido de la banda global de veredicto — la actual ya es óptima
- 2026-07-15 «Sin afirmaciones» es filtrado de dominio, no fallo del extractor
- 2026-07-15 Muestreo solo-médico — baseline honesto, y es peor
- 2026-07-15 Diagnóstico: BioBERT lee registro, no contenido

[2026-08.md](2026-08.md):

- 2026-08-30 Sustitución del dataset: PubHealth → HealthVer
- 2026-08-31 Conjunto dorado escrito a mano
- 2026-08-30/31 Prompts: juez v3 (polaridad) y extractor v4 (ámbito)
- 2026-08-31 Retirada del clasificador BERT — dos pruebas pareadas
- 2026-08-31 La ausencia de evidencia no es prueba de falsedad
- 2026-08-31 Diagnóstico: el cuello de botella es el juez, no la recuperación
- 2026-08-31 Umbral en el punto neutro — correcto, pero ya no compra nada
- 2026-08-31 El traductor corregía la desinformación — traductor v3

[2026-09.md](2026-09.md):

- 2026-09-01 Juez v4: obligar al juez a mojarse — rechazado
- 2026-09-01 Razonar antes de etiquetar (`claim_analysis`) — rechazado
- 2026-09-01 Borrado del código de BERT
- 2026-09-22 Evidencia grabada para comparaciones pareadas
- 2026-09-25 Juez v5 y traductor v4: marcadores contra la inyección — adoptado
- 2026-09-30 Juez v6 con un campo por fuente; extractor y traductor v5 — adoptado

[2026-10.md](2026-10.md):

- 2026-10-01 Cribado de jueces solo-juez — Ministral 14B, candidato local
- 2026-10-12 Veredicto global por afirmaciones: «parcialmente falsa» — adoptado
