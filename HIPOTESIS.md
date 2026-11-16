# Hipótesis previas a las corridas finales

> Registradas el 2026-11-12, **antes** de ejecutar las 36 corridas de la parte A y las de la parte B.
> No se modifican después de ver resultados; si el equipo cambia de opinión, se agrega una nota fechada al final.

## Elementos fijos en todas las comparaciones

Corpus (5 archivos, 3 formatos), 9 preguntas, LLM (`LLM_MODEL`), temperatura 0, `top_p` 1, límite de salida 512 tokens, semilla 42 (si el proveedor la respeta), límite de contexto 2400 tokens y plantilla `rag-v1` para R0, R1, R2 y B*. La unidad de token para fragmentar y medir el contexto es siempre el tokenizador de `intfloat/multilingual-e5-base`.

## R1 frente a R0 (fragmentación estructural frente a fija 400/60)

**Qué cambia:** los fragmentos dejan de cortarse a mitad de párrafo y no mezclan secciones; quedan más fragmentos y más cortos (en promedio ~100–200 tokens frente a ~350–400).

**Qué esperamos:**
- **Cobertura de evidencia igual o mejor** en las preguntas directas (D1–D3): cada pasaje necesario cabe completo en un párrafo y ya no puede quedar partido entre dos ventanas.
- **Menos texto irrelevante** en cada fragmento (R0 mezcla, por ejemplo, instalación, conexión y errores de la VPN en un mismo fragmento), lo que debería facilitar citas más precisas: **mayor respaldo de las citas**.
- **Riesgo en preguntas multidocumento (M1–M3):** con k=4 y fragmentos más pequeños se recupera menos texto total (~600 frente a ~1600 tokens). Si una pregunta necesita tres pasajes de dos documentos (M1), es posible que uno quede fuera: **la cobertura multidocumento podría bajar**.
- **Abstención:** sin cambio esperado.

**Por qué:** la similitud coseno de un fragmento corto y temático se parece más a la de la consulta que la de un fragmento largo que diluye varios temas.

## R2 frente a R0 (búsqueda híbrida densa + BM25 con RRF, k=4)

**Qué esperamos:**
- **Mejor cobertura en preguntas con términos exactos**: códigos de error (VPN-809, VPN-401) y cifras/entidades (AndinaDrive, P2, cuota). BM25 premia la coincidencia literal, que los embeddings densos tienden a suavizar (VPN-809 y VPN-619 son casi idénticos para un modelo denso).
- **Corrección igual o algo mayor** como consecuencia de la mejor cobertura.
- **Riesgo:** en preguntas sin respuesta (U1–U3) BM25 puede subir fragmentos que comparten palabras (por ejemplo «copias de seguridad» en U3), lo que podría **empeorar la abstención** si el LLM usa ese distractor.

## C0 frente a R0 (sin recuperación)

**Qué esperamos:**
- **Corrección muy baja en C0** (0–1 de 6): las respuestas dependen de datos internos ficticios (códigos de error, plazos, cuotas) que el LLM no puede conocer.
- **Abstención en C0 alta** si sigue la instrucción, pero con riesgo de respuestas genéricas plausibles («contacte a soporte», «reinicie el router») que no son abstenciones; en U2 y U3 es probable que el LLM dé recomendaciones generales (por ejemplo, 10–25 Mbps), lo que cuenta como **abstención inapropiada**.
- R0 debería superar ampliamente a C0 en corrección y comportarse igual o mejor en abstención.
- Nota: C0 tiene instrucciones adaptadas a la ausencia de documentos, y las citas solo se evalúan en R0, R1 y R2.

## Experimento B (sobre R0)

- **B1 (embeddings `BAAI/bge-m3`):** modelo más grande y de contexto largo; esperamos cobertura igual o mejor, sobre todo en preguntas multidocumento redactadas con lenguaje distinto al del corpus (M2: «restablecí» frente a «restablecimiento»). Mayor tiempo de indexación.
- **B2 (otro LLM):** la recuperación es idéntica a R0, así que la cobertura no cambia; las diferencias aparecerán en corrección, respaldo de citas y, sobre todo, en la **obediencia a la regla de abstención** y al formato de citas `[F#]`.
- **B3 (ambos):** se usa para ver si los efectos se suman o se compensan.

## Límites conocidos de la comparación

- Los modelos gratuitos de OpenRouter pueden enrutarse a distintos proveedores y no todos respetan `seed`; se registra el modelo y el proveedor efectivamente servidos en cada corrida.
- Con solo 9 preguntas, una diferencia de 1/6 no es concluyente; el análisis se apoya en la inspección cualitativa de los fragmentos y las respuestas.
