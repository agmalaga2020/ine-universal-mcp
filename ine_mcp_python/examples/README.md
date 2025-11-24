# Ejemplos de Uso del Servidor MCP INE

Este directorio contiene ejemplos prácticos de cómo usar el servidor MCP para analizar datos del INE.

## 📁 Contenido

### Ejemplos Básicos

#### 1. `simple_search.py` 🔍
**Demostración de búsqueda semántica**

El ejemplo más simple para empezar. Muestra cómo buscar series del INE usando lenguaje natural.

```bash
docker exec -it ine_mcp_python-ine-mcp-1 uv run python /app/examples/simple_search.py
```

**Qué demuestra:**
- Búsqueda por significado, no solo palabras clave
- "Inflación mensual" → encuentra IPC automáticamente
- Scores de similitud semántica

---

#### 2. `ipc_analysis.py` 📈
**Análisis completo del IPC (Inflación)**

Caso de uso real: obtener y analizar datos de inflación.

```bash
docker exec -it ine_mcp_python-ine-mcp-1 uv run python /app/examples/ipc_analysis.py
```

**Qué demuestra:**
- Pipeline completo: búsqueda → extracción → análisis
- Cálculo de estadísticas (media, cambio porcentual)
- Visualización tabular
- Interpretación automática de resultados

---

### Ejemplos Avanzados - Análisis de Correlación

#### 3. `tourism_rental_correlation.py` 🏖️
**Correlación turismo-vivienda (datos nacionales)**

Primer intento de análisis de correlación con datos agregados a nivel nacional.

**Resultado:** Correlación débil (+0.175) debido a la agregación nacional.

**Archivos de salida:**
- `tourism_rental_analysis_output.txt` - Primera ejecución
- `tourism_rental_final_output.txt` - Versión mejorada

**Lección aprendida:** Los datos nacionales diluyen la señal. Se necesita granularidad provincial.

---

#### 4. `analyze_malaga_provincial.py` 🎯
**Intento de análisis provincial (Málaga)**

Búsqueda de datos específicos de Málaga usando filtros semánticos.

**Resultado:** El buscador semántico no tiene suficientes series provinciales indexadas.

**Archivo de salida:** `malaga_provincial_output.txt`

**Lección aprendida:** La búsqueda semántica prioriza series nacionales. Se necesita explorar por código de operación.

---

#### 5. `investigate_ine_operations.py` 🔬
**Exploración forense de operaciones del INE**

Script de investigación para encontrar las operaciones correctas que contienen datos provinciales.

```bash
docker exec -it ine_mcp_python-ine-mcp-1 uv run python /app/examples/investigate_ine_operations.py
```

**Qué hace:**
- Lista todas las 203 operaciones del INE
- Identifica operaciones de turismo (18 encontradas)
- Identifica operaciones de vivienda (17 encontradas)
- Filtra por códigos específicos (EOH, IPV)

**Archivo de salida:** `investigation_output.txt`

**Operaciones clave encontradas:**
- `30235` - Encuesta de Ocupación Hotelera (EOH)
- `30457` - Índice de Precios de la Vivienda (IPV)

---

#### 6. `final_malaga_analysis.py` 🏁
**Análisis definitivo usando códigos de operación**

Ataque directo usando los códigos de operación correctos encontrados en la investigación forense.

**Resultado:** Error "Expecting value" - La API Tempus del INE no expone series provinciales desagregadas.

**Archivo de salida:** `final_output.txt`

**Conclusión científica:**
> Los datos provinciales de turismo y vivienda existen en el INE, pero **no están disponibles vía API Tempus**. Están en tablas estáticas que requieren descarga manual desde la web del INE.

---

## 🎓 Flujo de Aprendizaje Recomendado

1. **Principiante** → `simple_search.py`: Aprende a buscar series
2. **Intermedio** → `ipc_analysis.py`: Pipeline completo de análisis
3. **Avanzado** → `tourism_rental_correlation.py`: Correlaciones básicas
4. **Experto** → `investigate_ine_operations.py` + `final_malaga_analysis.py`: Investigación forense

## 🔧 Componentes Técnicos Demostrados

### Motor de Búsqueda Semántica
```python
search_engine = SemanticSearchEngine(...)
results = search_engine.search("turistas extranjeros España", top_k=10)
```

### Agregación Inteligente de Datos
```python
aggregator = DataAggregator()
df1_aligned, df2_aligned, freq = aggregator.align_series_frequencies(df1, df2)
```

### Cliente API del INE
```python
async with INEClient() as client:
    data = await client.get_series_data("IPC251856", last_n=12)
```

## 📊 Datos Utilizados

Todos los datos provienen del **Instituto Nacional de Estadística (INE)** de España:
- API oficial: https://servicios.ine.es/wstempus/
- 34,390 series temporales indexadas semánticamente
- Cobertura: economía, demografía, turismo, precios, empleo

## ⚠️ Limitaciones Descubiertas

1. **Granularidad provincial limitada**: Muchas series solo están disponibles a nivel nacional
2. **API Tempus incompleta**: No todas las publicaciones del INE están en la API
3. **Datos no en tiempo real**: Las series tienen lag (última actualización puede ser de meses atrás)
4. **Frecuencias variadas**: Algunas series son anuales, otras mensuales (el sistema las alinea automáticamente)

## 💡 Ideas para Nuevos Ejemplos

- **Inflación vs Salarios**: ¿Los salarios siguen el ritmo de la inflación?
- **Desempleo vs PIB**: Relación inversa entre crecimiento y paro
- **Demografía vs Vivienda**: Impacto del envejecimiento en construcción
- **Exportaciones vs Euro**: Correlación entre tipo de cambio y comercio exterior

## 🚀 Próximos Pasos

1. Lee la documentación principal en `../README.md`
2. Explora las herramientas MCP disponibles
3. Prueba tus propias consultas semánticas
4. Crea tus propios análisis

---

**Nota**: Algunos análisis pueden tomar 1-2 minutos debido a la cantidad de datos procesados y las llamadas a la API del INE.

