#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";
import express from "express";
import dotenv from "dotenv";

dotenv.config();

// Configuration
const INE_BASE_URL = "https://servicios.ine.es/wstempus/js/ES";
const PORT = process.env.PORT || 10000;
const API_TIMEOUT = 30000; // 30 seconds

// Axios instance with logging and timeout
const ineApi = axios.create({
  baseURL: INE_BASE_URL,
  timeout: API_TIMEOUT,
});

// Request interceptor for logging
ineApi.interceptors.request.use(
  (config) => {
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}] INE API Request: ${config.method?.toUpperCase()} ${config.url}`);
    if (config.params) {
      console.error(`[${timestamp}] Parameters:`, JSON.stringify(config.params));
    }
    config.metadata = { startTime: Date.now() };
    return config;
  },
  (error) => {
    console.error(`[${new Date().toISOString()}] Request Error:`, error.message);
    return Promise.reject(error);
  }
);

// Response interceptor for logging
ineApi.interceptors.response.use(
  (response) => {
    const duration = Date.now() - response.config.metadata.startTime;
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}] INE API Response: ${response.status} (${duration}ms)`);
    return response;
  },
  (error) => {
    const timestamp = new Date().toISOString();
    if (error.code === 'ECONNABORTED') {
      console.error(`[${timestamp}] Timeout Error: Request took longer than ${API_TIMEOUT}ms`);
    } else if (error.response) {
      console.error(`[${timestamp}] API Error: ${error.response.status} - ${error.response.statusText}`);
    } else {
      console.error(`[${timestamp}] Network Error:`, error.message);
    }
    return Promise.reject(error);
  }
);

// Helper function to handle API errors
function handleApiError(error, context = "") {
  const timestamp = new Date().toISOString();
  console.error(`[${timestamp}] Error in ${context}:`, error.message);

  if (error.code === 'ECONNABORTED') {
    return {
      error: "El INE está tardando demasiado. Intenta con menos datos o un rango menor.",
      details: "Timeout después de 30 segundos"
    };
  }

  if (error.response) {
    switch (error.response.status) {
      case 404:
        return {
          error: "Serie/tabla no encontrada. Verifica el ID.",
          details: error.response.data
        };
      case 500:
        return {
          error: "Error del servidor INE. Inténtalo más tarde.",
          details: error.response.statusText
        };
      default:
        return {
          error: `Error HTTP ${error.response.status}`,
          details: error.response.data
        };
    }
  }

  return {
    error: "Error de conexión con el INE.",
    details: error.message
  };
}

// Input validation functions
function validateSeriesId(seriesId) {
  if (!seriesId || typeof seriesId !== 'string') {
    throw new Error("El ID de serie debe ser una cadena no vacía");
  }
  // INE series IDs are typically alphanumeric
  if (!/^[A-Z0-9]+$/i.test(seriesId)) {
    throw new Error("El ID de serie tiene un formato inválido");
  }
  return true;
}

function validateDate(date) {
  if (!date) return true; // Optional dates
  // INE dates are typically in format YYYYMMDD or YYYY
  if (!/^\d{4}(\d{2}\d{2})?$/.test(date)) {
    throw new Error(`Formato de fecha inválido: ${date}. Use YYYYMMDD o YYYY`);
  }
  return true;
}

// Data transformation functions

/**
 * Transforms INE series search results into a clean, LLM-friendly format
 * Only returns essential fields: ID, Title, and Description
 */
function transformSearchResults(rawData) {
  if (!rawData || !Array.isArray(rawData)) {
    return [];
  }

  return rawData.map(item => ({
    id: item.COD || item.Id,
    title: item.Nombre || item.Title,
    description: item.Descripcion || item.Description || ""
  }));
}

/**
 * Transforms INE series data into a simple, analyzable format
 * Converts complex JSON into flat date-value pairs
 */
function transformSeriesData(rawData) {
  if (!rawData || !rawData.Data) {
    return { message: "No hay datos disponibles para los parámetros solicitados", data: [] };
  }

  const data = rawData.Data.map(item => ({
    date: item.Fecha || item.T3_Periodo,
    value: parseFloat(item.Valor) || item.Valor,
    period: item.T3_Periodo || item.Fecha
  }));

  return {
    seriesId: rawData.COD || rawData.Id,
    name: rawData.Nombre || rawData.Name,
    unit: rawData.Unidad || rawData.Unit,
    source: rawData.Fuente || rawData.Source,
    totalDataPoints: data.length,
    data: data
  };
}

/**
 * Transforms series metadata into structured information
 */
function transformMetadata(rawData) {
  if (!rawData) {
    return { error: "No hay metadatos disponibles" };
  }

  return {
    id: rawData.COD || rawData.Id,
    name: rawData.Nombre || rawData.Name,
    unit: rawData.Unidad || rawData.Unit,
    frequency: rawData.T3_Periodicidad || rawData.Frequency,
    source: rawData.Fuente || rawData.Source,
    lastUpdate: rawData.T3_FechaUltDato || rawData.LastUpdate,
    decimals: rawData.Decimales || rawData.Decimals,
    scale: rawData.Escala || rawData.Scale
  };
}

// MCP Server setup
const server = new Server(
  {
    name: "ine-universal-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const TOOLS = [
  {
    name: "search_ine_series",
    description: "Search for INE statistical series by keywords. Returns series ID, title, and description.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search keywords (e.g., 'IPC', 'EPA', 'PIB')"
        },
        limit: {
          type: "number",
          description: "Maximum number of results to return (default: 20)",
          default: 20
        }
      },
      required: ["query"]
    }
  },
  {
    name: "get_series_data",
    description: "Get data points from a specific INE series. Returns dates and values in a clean format.",
    inputSchema: {
      type: "object",
      properties: {
        seriesId: {
          type: "string",
          description: "INE series ID (e.g., 'IPC251856')"
        },
        lastN: {
          type: "number",
          description: "Get last N data points"
        },
        startDate: {
          type: "string",
          description: "Start date in YYYYMMDD or YYYY format"
        },
        endDate: {
          type: "string",
          description: "End date in YYYYMMDD or YYYY format"
        },
        dataType: {
          type: "string",
          description: "Type of data transformation (default: 'flat')",
          enum: ["flat", "csv"],
          default: "flat"
        }
      },
      required: ["seriesId"]
    }
  },
  {
    name: "get_series_metadata",
    description: "Get complete metadata for an INE series (units, frequency, source, etc.)",
    inputSchema: {
      type: "object",
      properties: {
        seriesId: {
          type: "string",
          description: "INE series ID"
        }
      },
      required: ["seriesId"]
    }
  },
  {
    name: "list_operations",
    description: "List main INE operations (IPC, EPA, PIB, etc.)",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "get_series_by_operation",
    description: "List all series belonging to a specific operation. Handles automatic pagination.",
    inputSchema: {
      type: "object",
      properties: {
        operation: {
          type: "string",
          description: "Operation code (e.g., '30', '45' for IPC, EPA)"
        },
        limit: {
          type: "number",
          description: "Maximum number of series to return (default: 100)",
          default: 100
        }
      },
      required: ["operation"]
    }
  },
  {
    name: "get_table_data",
    description: "Download complete data from an INE table",
    inputSchema: {
      type: "object",
      properties: {
        tableId: {
          type: "string",
          description: "INE table ID"
        }
      },
      required: ["tableId"]
    }
  },
  {
    name: "search_variables",
    description: "Search for variables in the INE system",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search term for variables"
        }
      },
      required: ["query"]
    }
  }
];

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search_ine_series": {
        const { query, limit = 20 } = args;

        if (!query) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({ error: "Se requiere un término de búsqueda" }, null, 2)
            }]
          };
        }

        try {
          const response = await ineApi.get('/SEARCH', {
            params: { text: query }
          });

          const transformedData = transformSearchResults(response.data);
          const limitedData = transformedData.slice(0, limit);

          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                query: query,
                totalResults: transformedData.length,
                returnedResults: limitedData.length,
                series: limitedData
              }, null, 2)
            }]
          };
        } catch (error) {
          const errorInfo = handleApiError(error, "search_ine_series");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      case "get_series_data": {
        const { seriesId, lastN, startDate, endDate, dataType = 'flat' } = args;

        try {
          validateSeriesId(seriesId);
          if (startDate) validateDate(startDate);
          if (endDate) validateDate(endDate);

          const params = {};
          if (lastN) params.nult = lastN;
          if (startDate) params.date = startDate;
          if (endDate) params.dateEnd = endDate;

          const response = await ineApi.get(`/DATOS_SERIE/${seriesId}`, { params });

          const transformedData = transformSeriesData(response.data);

          if (transformedData.data && transformedData.data.length === 0) {
            return {
              content: [{
                type: "text",
                text: JSON.stringify({
                  message: "No hay datos disponibles para los parámetros solicitados",
                  seriesId: seriesId
                }, null, 2)
              }]
            };
          }

          // Convert to CSV if requested
          if (dataType === 'csv' && transformedData.data) {
            const csvData = "Date,Value\n" + transformedData.data
              .map(d => `${d.date},${d.value}`)
              .join("\n");

            return {
              content: [{
                type: "text",
                text: csvData
              }]
            };
          }

          return {
            content: [{
              type: "text",
              text: JSON.stringify(transformedData, null, 2)
            }]
          };
        } catch (error) {
          if (error.message.includes("formato") || error.message.includes("ID de serie")) {
            return {
              content: [{
                type: "text",
                text: JSON.stringify({ error: error.message }, null, 2)
              }],
              isError: true
            };
          }
          const errorInfo = handleApiError(error, "get_series_data");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      case "get_series_metadata": {
        const { seriesId } = args;

        try {
          validateSeriesId(seriesId);

          const response = await ineApi.get(`/SERIE/${seriesId}`);
          const metadata = transformMetadata(response.data);

          return {
            content: [{
              type: "text",
              text: JSON.stringify(metadata, null, 2)
            }]
          };
        } catch (error) {
          if (error.message.includes("ID de serie")) {
            return {
              content: [{
                type: "text",
                text: JSON.stringify({ error: error.message }, null, 2)
              }],
              isError: true
            };
          }
          const errorInfo = handleApiError(error, "get_series_metadata");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      case "list_operations": {
        // Curated list of main INE operations
        const mainOperations = [
          { code: "30", name: "IPC - Índice de Precios de Consumo", description: "Consumer Price Index" },
          { code: "45", name: "EPA - Encuesta de Población Activa", description: "Labour Force Survey" },
          { code: "31", name: "IPRI - Índice de Precios Industriales", description: "Industrial Price Index" },
          { code: "36", name: "CNE - Contabilidad Nacional", description: "National Accounts (GDP)" },
          { code: "56", name: "Demografía y Población", description: "Demographics and Population" },
          { code: "23", name: "Comercio Exterior", description: "Foreign Trade" },
          { code: "50", name: "Encuesta de Condiciones de Vida", description: "Living Conditions Survey" }
        ];

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              message: "Principales operaciones del INE",
              operations: mainOperations
            }, null, 2)
          }]
        };
      }

      case "get_series_by_operation": {
        const { operation, limit = 100 } = args;

        if (!operation) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({ error: "Se requiere un código de operación" }, null, 2)
            }],
            isError: true
          };
        }

        try {
          const response = await ineApi.get(`/SERIES_OPERACION/${operation}`);

          let series = response.data;
          if (!Array.isArray(series)) {
            series = [];
          }

          const transformedSeries = transformSearchResults(series);
          const limitedSeries = transformedSeries.slice(0, limit);

          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                operation: operation,
                totalSeries: transformedSeries.length,
                returnedSeries: limitedSeries.length,
                series: limitedSeries
              }, null, 2)
            }]
          };
        } catch (error) {
          const errorInfo = handleApiError(error, "get_series_by_operation");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      case "get_table_data": {
        const { tableId } = args;

        if (!tableId) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({ error: "Se requiere un ID de tabla" }, null, 2)
            }],
            isError: true
          };
        }

        try {
          const response = await ineApi.get(`/DATOS_TABLA/${tableId}`);

          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                tableId: tableId,
                data: response.data
              }, null, 2)
            }]
          };
        } catch (error) {
          const errorInfo = handleApiError(error, "get_table_data");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      case "search_variables": {
        const { query } = args;

        if (!query) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({ error: "Se requiere un término de búsqueda" }, null, 2)
            }],
            isError: true
          };
        }

        try {
          const response = await ineApi.get('/VARIABLES');

          let variables = response.data;
          if (!Array.isArray(variables)) {
            variables = [];
          }

          // Local filtering
          const filtered = variables.filter(v =>
            JSON.stringify(v).toLowerCase().includes(query.toLowerCase())
          );

          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                query: query,
                totalMatches: filtered.length,
                variables: filtered
              }, null, 2)
            }]
          };
        } catch (error) {
          const errorInfo = handleApiError(error, "search_variables");
          return {
            content: [{
              type: "text",
              text: JSON.stringify(errorInfo, null, 2)
            }],
            isError: true
          };
        }
      }

      default:
        return {
          content: [{
            type: "text",
            text: JSON.stringify({ error: `Herramienta desconocida: ${name}` }, null, 2)
          }],
          isError: true
        };
    }
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Unhandled error in ${name}:`, error);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: "Error interno del servidor",
          details: error.message
        }, null, 2)
      }],
      isError: true
    };
  }
});

// Express health check endpoint
const app = express();

app.get("/", (req, res) => {
  res.json({
    name: "ine-universal-mcp",
    version: "1.0.0",
    description: "Universal MCP server for Spanish INE (Instituto Nacional de Estadística) API",
    status: "healthy",
    tools: TOOLS.map(t => ({
      name: t.name,
      description: t.description
    })),
    documentation: "https://www.ine.es/dyngs/DAB/index.htm"
  });
});

app.listen(PORT, () => {
  console.error(`[${new Date().toISOString()}] Health check endpoint running on port ${PORT}`);
});

// Start MCP server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`[${new Date().toISOString()}] INE Universal MCP Server running`);
}

main().catch((error) => {
  console.error(`[${new Date().toISOString()}] Fatal error:`, error);
  process.exit(1);
});
