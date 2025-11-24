#!/usr/bin/env python3
"""
Ejemplo: Obtención de Datos del IPC (Índice de Precios al Consumo)

Demuestra cómo:
1. Buscar series del IPC
2. Obtener los datos más recientes
3. Formatear y visualizar la información

Autor: INE MCP Server
Licencia: MIT
"""

import asyncio
from pathlib import Path
from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

async def main():
    print("=" * 80)
    print("EJEMPLO: Análisis del IPC (Inflación)")
    print("=" * 80)
    print()
    
    # Paso 1: Buscar serie del IPC general
    print("PASO 1: Búsqueda de la serie IPC General")
    print("-" * 80)
    
    search_engine = SemanticSearchEngine(
        index_path=Path("/app/data/faiss_index.bin"),
        metadata_path=Path("/app/data/series_metadata.pkl"),
    )
    
    try:
        search_engine.load_index()
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    results = search_engine.search("IPC índice general consumo", top_k=5)
    
    if not results:
        print("✗ No se encontraron series")
        return
    
    print(f"Encontradas {len(results)} series:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['name']}")
        print(f"     ID: {result['id']} | Score: {result['similarity_score']:.3f}")
    
    # Usar la primera serie encontrada
    ipc_id = results[0]['id']
    ipc_name = results[0]['name']
    
    print()
    print(f"Seleccionada: {ipc_name}")
    print(f"ID: {ipc_id}")
    
    # Paso 2: Obtener datos
    print()
    print("PASO 2: Obtención de datos (últimos 12 meses)")
    print("-" * 80)
    
    aggregator = DataAggregator()
    
    async with INEClient() as client:
        try:
            raw_data = await client.get_series_data(ipc_id, last_n=12)
            df = aggregator.parse_ine_data(raw_data)
            
            if df.empty:
                print("✗ No hay datos disponibles")
                return
            
            print(f"✓ {len(df)} datos obtenidos")
            print(f"  Período: {df.index[0].date()} a {df.index[-1].date()}")
            
            # Paso 3: Análisis
            print()
            print("PASO 3: Análisis de la Inflación")
            print("-" * 80)
            
            # Estadísticas
            mean_val = df['value'].mean()
            latest_val = df['value'].iloc[-1]
            first_val = df['value'].iloc[0]
            change_pct = ((latest_val - first_val) / first_val) * 100
            
            print(f"\nEstadísticas:")
            print(f"  • Valor promedio: {mean_val:.2f}")
            print(f"  • Valor más reciente: {latest_val:.2f} ({df.index[-1].date()})")
            print(f"  • Cambio en 12 meses: {change_pct:+.2f}%")
            
            # Mostrar datos tabulados
            print()
            print("Últimos 12 valores:")
            print("-" * 40)
            print(f"{'Fecha':<15} {'Valor':>10} {'Var %':>10}")
            print("-" * 40)
            
            for i in range(len(df)):
                date = df.index[i].strftime("%Y-%m")
                value = df['value'].iloc[i]
                
                if i > 0:
                    prev_value = df['value'].iloc[i-1]
                    var_pct = ((value - prev_value) / prev_value) * 100
                    print(f"{date:<15} {value:>10.2f} {var_pct:>9.2f}%")
                else:
                    print(f"{date:<15} {value:>10.2f} {'---':>10}")
            
            print()
            print("=" * 80)
            print("Interpretación:")
            print("=" * 80)
            
            if change_pct > 2:
                print("\n⚠️  Inflación elevada detectada")
                print(f"   El IPC ha aumentado un {change_pct:.2f}% en los últimos 12 meses.")
            elif change_pct > 0:
                print("\n✓ Inflación moderada")
                print(f"   El IPC ha aumentado un {change_pct:.2f}% en los últimos 12 meses.")
            elif change_pct < -2:
                print("\n⚠️  Deflación detectada")
                print(f"   El IPC ha disminuido un {abs(change_pct):.2f}% en los últimos 12 meses.")
            else:
                print("\n✓ Precios estables")
                print(f"   Cambio mínimo: {change_pct:+.2f}%")
            
            print()
            
        except Exception as e:
            print(f"✗ Error obteniendo datos: {e}")
            return

if __name__ == "__main__":
    asyncio.run(main())
