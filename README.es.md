# Servidor MCP Universal del INE

🇪🇸 Español | **[🇬🇧 English Version](./README.md)**

Un servidor robusto del Protocolo de Contexto de Modelo (MCP) que proporciona acceso universal a la API del INE español (Instituto Nacional de Estadística) para acceder a datos económicos, demográficos y estadísticos de España.

## Características

- 🔍 **Buscar Series**: Busca series estadísticas por palabras clave
- 📊 **Obtener Datos**: Recupera datos de series temporales con filtrado flexible
- 📋 **Metadatos**: Accede a metadatos completos de series (unidades, frecuencia, fuente)
- 🏢 **Operaciones**: Lista y explora las principales operaciones del INE (IPC, EPA, PIB, etc.)
- 📑 **Tablas**: Descarga tablas de datos completas
- 🔎 **Variables**: Busca variables del sistema
- 🛡️ **Listo para Producción**: Manejo robusto de errores, logging y gestión de timeouts
- 🚀 **Listo para Desplegar**: Configurado para despliegue en Render Free Tier

## Inicio Rápido

### Instalación Local

```bash
# Clonar el repositorio
git clone https://github.com/yourusername/ine-universal-mcp.git
cd ine-universal-mcp

# Instalar dependencias
npm install

# Iniciar el servidor
npm start
```

El endpoint de health check estará disponible en `http://localhost:10000`

### Desplegar en Render

[![Desplegar en Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

O manualmente:

1. Haz fork de este repositorio
2. Crea un nuevo Web Service en [Render](https://render.com)
3. Conecta tu repositorio
4. Render detectará automáticamente la configuración de `render.yaml`
5. ¡Despliega!

## Configuración

Crea un archivo `.env` basado en `.env.example`:

```bash
PORT=10000  # Puerto para el endpoint de health check
```

## Herramientas Disponibles

### 1. `search_ine_series`
Busca series estadísticas por palabras clave.

**Parámetros:**
- `query` (string, requerido): Palabras clave de búsqueda (ej., "IPC", "EPA", "PIB")
- `limit` (number, opcional): Máximo de resultados a devolver (por defecto: 20)

**Ejemplo:**
```json
{
  "query": "IPC",
  "limit": 10
}
```

### 2. `get_series_data`
Recupera puntos de datos de una serie específica.

**Parámetros:**
- `seriesId` (string, requerido): ID de serie del INE (ej., "IPC251856")
- `lastN` (number, opcional): Obtener últimos N puntos de datos
- `startDate` (string, opcional): Fecha de inicio (YYYYMMDD o YYYY)
- `endDate` (string, opcional): Fecha de fin (YYYYMMDD o YYYY)
- `dataType` (string, opcional): Formato de salida ("flat" o "csv")

**Ejemplo:**
```json
{
  "seriesId": "IPC251856",
  "lastN": 12
}
```

### 3. `get_series_metadata`
Obtiene metadatos completos de una serie (unidades, frecuencia, fuente, etc.)

**Parámetros:**
- `seriesId` (string, requerido): ID de serie del INE

### 4. `list_operations`
Lista las principales operaciones del INE (IPC, EPA, PIB, etc.)

**Parámetros:** Ninguno

### 5. `get_series_by_operation`
Lista todas las series pertenecientes a una operación específica.

**Parámetros:**
- `operation` (string, requerido): Código de operación (ej., "30" para IPC, "45" para EPA)
- `limit` (number, opcional): Máximo de series a devolver (por defecto: 100)

### 6. `get_table_data`
Descarga datos completos de una tabla del INE.

**Parámetros:**
- `tableId` (string, requerido): ID de tabla del INE

### 7. `search_variables`
Busca variables en el sistema del INE.

**Parámetros:**
- `query` (string, requerido): Término de búsqueda para variables

## Ejemplos de Pruebas

### Ejemplo 1: Buscar Series del IPC (Índice de Precios de Consumo)

**Solicitud:**
```json
{
  "tool": "search_ine_series",
  "arguments": {
    "query": "IPC",
    "limit": 5
  }
}
```

**Resultado Esperado:**
```json
{
  "query": "IPC",
  "totalResults": 150,
  "returnedResults": 5,
  "series": [
    {
      "id": "IPC251856",
      "title": "Índice de Precios de Consumo. General",
      "description": "Base 2021"
    }
    // ... más resultados
  ]
}
```

### Ejemplo 2: Obtener Últimos 12 Datos de una Serie del IPC

**Solicitud:**
```json
{
  "tool": "get_series_data",
  "arguments": {
    "seriesId": "IPC251856",
    "lastN": 12
  }
}
```

**Resultado Esperado:**
```json
{
  "seriesId": "IPC251856",
  "name": "Índice de Precios de Consumo. General",
  "unit": "Índice",
  "totalDataPoints": 12,
  "data": [
    { "date": "2024M01", "value": 113.5, "period": "2024M01" },
    { "date": "2024M02", "value": 114.2, "period": "2024M02" }
    // ... más puntos de datos
  ]
}
```

### Ejemplo 3: Listar Series de la Operación EPA (Encuesta de Población Activa)

**Solicitud:**
```json
{
  "tool": "get_series_by_operation",
  "arguments": {
    "operation": "45",
    "limit": 10
  }
}
```

**Resultado Esperado:**
```json
{
  "operation": "45",
  "totalSeries": 250,
  "returnedSeries": 10,
  "series": [
    {
      "id": "EPA123456",
      "title": "Población activa. Total",
      "description": "Encuesta de Población Activa"
    }
    // ... más series
  ]
}
```

## Conectar a Herramientas de IA

### Claude Desktop

Añade a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ine": {
      "command": "node",
      "args": ["/ruta/a/ine-universal-mcp/server.js"]
    }
  }
}
```

### Cursor / Windsurf

Añade a tu configuración de MCP:

```json
{
  "mcpServers": {
    "ine": {
      "command": "node",
      "args": ["/ruta/absoluta/a/server.js"],
      "cwd": "/ruta/absoluta/a/ine-universal-mcp"
    }
  }
}
```

## Arquitectura

### Manejo de Errores

El servidor implementa manejo exhaustivo de errores:

- **Errores de timeout** (>30s): Sugiere reducir el rango de datos
- **Errores 404**: Mensaje claro sobre IDs de series/tablas inválidos
- **Errores 500**: Indica problemas con el servidor del INE
- **Datos vacíos**: Mensaje explícito cuando no hay datos disponibles

### Logging

Todas las llamadas a la API se registran con:
- Marca de tiempo
- Método HTTP y URL
- Parámetros de solicitud
- Tiempo de respuesta
- Códigos de estado
- Detalles de errores

Los logs se escriben en `stderr` para compatibilidad con el sistema de logging de Render.

### Transformación de Datos

Las respuestas crudas de la API del INE se transforman en formatos limpios y amigables para LLMs:
- **Resultados de búsqueda**: Solo ID, título y descripción
- **Datos de series**: Pares fecha-valor planos o formato CSV
- **Metadatos**: Información clave estructurada
- **Paginación automática**: Maneja conjuntos grandes de resultados

## Referencia de la API

El servidor utiliza la API oficial del INE Tempus:
- **URL Base**: https://servicios.ine.es/wstempus/js/ES
- **Documentación**: https://www.ine.es/dyngs/DAB/index.htm

## Desarrollo

```bash
# Instalar dependencias
npm install

# Ejecutar en modo desarrollo (con reinicio automático)
npm run dev

# Ejecutar en modo producción
npm start
```

## Licencia

MIT

## Contribuciones

¡Las contribuciones son bienvenidas! Por favor, siéntete libre de enviar un Pull Request.

## Soporte

Para problemas relacionados con:
- **Este servidor MCP**: Abre un issue en este repositorio
- **API del INE**: Consulta la [documentación oficial](https://www.ine.es/dyngs/DAB/index.htm)
- **Protocolo MCP**: Ver [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk)

---

Hecho con ❤️ para la comunidad de ciencia de datos e IA
