# Cavora — Backlog

## Segunda iteración

### Aditivos y nivel de riesgo
Añadir tabla `Additive` con código E, nombre, nivel de riesgo y fuente EFSA.
- Fuente: proyecto open source food-additives en GitHub + EFSA
- Niveles: no_risk, limited, moderate, high
- Relación ManyToMany con ProductCatalog
- Campo `additives_n` en ProductCatalog para contador rápido
- Poblar con script de importación desde CSV

### Scoring propio (1-100)
Calcular un score numérico propio combinando Nutri-Score, Nova group y aditivos.
Depende de tener la tabla Additive implementada primero.

Algoritmo:
- Base por Nutri-Score: A=100, B=75, C=50, D=25, E=0
- Penalización por Nova: 1=0, 2=-5, 3=-15, 4=-25
- Penalización por aditivos según nivel de riesgo:
  - high: -10 por aditivo
  - moderate: -5 por aditivo
  - limited: -2 por aditivo
  - no_risk: 0
- Score final: max(0, base - nova_penalty - additive_penalty)

### Estimación inteligente de caducidad
Actualmente la caducidad estimada se calcula por categoría (shelf_life_days en
ProductCatalog). Es demasiado genérica — una leche fresca y un yogur están en
la misma categoría pero duran distinto.

Mejora propuesta:
- Cuando un usuario confirma una fecha real (expiry_estimated=False), guardar
  esa información para mejorar la estimación futura del mismo producto
- Calcular la media de caducidades confirmadas por producto específico,
  no por categoría
- Campos a añadir en ProductCatalog:
  - confirmed_shelf_life_avg: float (media de días confirmados por usuarios)
  - confirmed_shelf_life_count: int (número de confirmaciones)
- Lógica de estimación por prioridad:
  1. Si confirmed_shelf_life_count >= 5 → usar confirmed_shelf_life_avg
  2. Si no → usar shelf_life_days por categoría como fallback
- Misma filosofía que ProductMatch — la app aprende colectivamente con el uso

## Tercera iteración

### OCR de ticket de compra
- Foto del ticket → Claude normaliza texto crudo → matching con Open Food Facts
- Los nombres en tickets son abreviados ("LECH DSNATA 1L HACEN")
- Endpoint asíncrono con Celery + polling de estado desde el front
- Flujo: POST /ai/ocr/ → recibe task_id → GET /ai/ocr/{task_id}/ → resultado

### Foto general de nevera
- Visión por IA para detectar productos en una foto de la nevera o despensa
- La más compleja e imprecisa de las vías de entrada
- Dejar para el final, una vez que el resto del producto esté estable