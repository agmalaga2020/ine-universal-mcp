# INE Universal MCP Server

**[🇪🇸 Versión en Español](./README.es.md)** | 🇬🇧 English

A robust Model Context Protocol (MCP) server providing universal access to the Spanish INE (Instituto Nacional de Estadística) API for accessing economic, demographic, and statistical data from Spain.

## Features

- 🔍 **Search Series**: Search for statistical series by keywords
- 📊 **Get Data**: Retrieve time series data with flexible filtering
- 📋 **Metadata**: Access complete series metadata (units, frequency, source)
- 🏢 **Operations**: List and explore major INE operations (IPC, EPA, PIB, etc.)
- 📑 **Tables**: Download complete data tables
- 🔎 **Variables**: Search system variables
- 🛡️ **Production-Ready**: Robust error handling, logging, and timeout management
- 🚀 **Deploy-Ready**: Configured for Render Free Tier deployment

## Quick Start

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ine-universal-mcp.git
cd ine-universal-mcp

# Install dependencies
npm install

# Start the server
npm start
```

The health check endpoint will be available at `http://localhost:10000`

### Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Or manually:

1. Fork this repository
2. Create a new Web Service on [Render](https://render.com)
3. Connect your repository
4. Render will automatically detect the `render.yaml` configuration
5. Deploy!

## Configuration

Create a `.env` file based on `.env.example`:

```bash
PORT=10000  # Port for health check endpoint
```

## Available Tools

### 1. `search_ine_series`
Search for statistical series by keywords.

**Parameters:**
- `query` (string, required): Search keywords (e.g., "IPC", "EPA", "PIB")
- `limit` (number, optional): Maximum results to return (default: 20)

**Example:**
```json
{
  "query": "IPC",
  "limit": 10
}
```

### 2. `get_series_data`
Retrieve data points from a specific series.

**Parameters:**
- `seriesId` (string, required): INE series ID (e.g., "IPC251856")
- `lastN` (number, optional): Get last N data points
- `startDate` (string, optional): Start date (YYYYMMDD or YYYY)
- `endDate` (string, optional): End date (YYYYMMDD or YYYY)
- `dataType` (string, optional): Output format ("flat" or "csv")

**Example:**
```json
{
  "seriesId": "IPC251856",
  "lastN": 12
}
```

### 3. `get_series_metadata`
Get complete metadata for a series (units, frequency, source, etc.)

**Parameters:**
- `seriesId` (string, required): INE series ID

### 4. `list_operations`
List main INE operations (IPC, EPA, PIB, etc.)

**Parameters:** None

### 5. `get_series_by_operation`
List all series belonging to a specific operation.

**Parameters:**
- `operation` (string, required): Operation code (e.g., "30" for IPC, "45" for EPA)
- `limit` (number, optional): Maximum series to return (default: 100)

### 6. `get_table_data`
Download complete data from an INE table.

**Parameters:**
- `tableId` (string, required): INE table ID

### 7. `search_variables`
Search for variables in the INE system.

**Parameters:**
- `query` (string, required): Search term for variables

## Testing Examples

### Example 1: Search for IPC (Consumer Price Index) Series

**Request:**
```json
{
  "tool": "search_ine_series",
  "arguments": {
    "query": "IPC",
    "limit": 5
  }
}
```

**Expected Result:**
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
    // ... more results
  ]
}
```

### Example 2: Get Last 12 Data Points from IPC Series

**Request:**
```json
{
  "tool": "get_series_data",
  "arguments": {
    "seriesId": "IPC251856",
    "lastN": 12
  }
}
```

**Expected Result:**
```json
{
  "seriesId": "IPC251856",
  "name": "Índice de Precios de Consumo. General",
  "unit": "Índice",
  "totalDataPoints": 12,
  "data": [
    { "date": "2024M01", "value": 113.5, "period": "2024M01" },
    { "date": "2024M02", "value": 114.2, "period": "2024M02" }
    // ... more data points
  ]
}
```

### Example 3: List Series from EPA (Labour Force Survey) Operation

**Request:**
```json
{
  "tool": "get_series_by_operation",
  "arguments": {
    "operation": "45",
    "limit": 10
  }
}
```

**Expected Result:**
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
    // ... more series
  ]
}
```

## Connecting to AI Tools

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ine": {
      "command": "node",
      "args": ["/path/to/ine-universal-mcp/server.js"]
    }
  }
}
```

### Cursor / Windsurf

Add to your MCP settings:

```json
{
  "mcpServers": {
    "ine": {
      "command": "node",
      "args": ["/absolute/path/to/server.js"],
      "cwd": "/absolute/path/to/ine-universal-mcp"
    }
  }
}
```

## Architecture

### Error Handling

The server implements comprehensive error handling:

- **Timeout errors** (>30s): Suggests reducing data range
- **404 errors**: Clear message about invalid series/table IDs
- **500 errors**: Indicates INE server issues
- **Empty data**: Explicit message when no data is available

### Logging

All API calls are logged with:
- Timestamp
- HTTP method and URL
- Request parameters
- Response time
- Status codes
- Error details

Logs are written to `stderr` for compatibility with Render's logging system.

### Data Transformation

Raw INE API responses are transformed into clean, LLM-friendly formats:
- **Search results**: Only ID, title, and description
- **Series data**: Flat date-value pairs or CSV format
- **Metadata**: Structured key information
- **Automatic pagination**: Handles large result sets

## API Reference

The server uses the official INE Tempus API:
- **Base URL**: https://servicios.ine.es/wstempus/js/ES
- **Documentation**: https://www.ine.es/dyngs/DAB/index.htm

## Development

```bash
# Install dependencies
npm install

# Run in development mode (with auto-restart)
npm run dev

# Run in production mode
npm start
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues related to:
- **This MCP server**: Open an issue in this repository
- **INE API**: Consult the [official documentation](https://www.ine.es/dyngs/DAB/index.htm)
- **MCP Protocol**: See [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk)

---

Made with ❤️ for the data science and AI community
