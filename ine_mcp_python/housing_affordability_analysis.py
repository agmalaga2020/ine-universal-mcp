#!/usr/bin/env python3
"""
ANÁLISIS MEJORADO: ¿Está la vivienda más cara que nunca?

Versión mejorada con búsquedas más específicas de series del INE
"""

import asyncio
from pathlib import Path
from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator
import pandas as pd

async def main():
    print("=" * 80)
    print("ANÁLISIS: Accesibilidad a la Vivienda en España (Histórico)")
    print("=" * 80)
    print()
    
    search_engine = SemanticSearchEngine(
        index_path=Path("/app/data/faiss_index.bin"),
        metadata_path=Path("/app/data/series_metadata.pkl"),
    )
    
    try:
        search_engine.load_index()
        print(f"✓ Índice cargado: {search_engine.get_stats()['total_series']:,} series")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    aggregator = DataAggregator()
    
    # PASO 1: Buscar series específicas con queries más precisas
    print()
    print("=" * 80)
    print("PASO 1: Búsqueda de Series")
    print("=" * 80)
    
    # IPV - Índice de Precios de Vivienda
    print("\n🏠 Buscando IPV (Índice de Precios de Vivienda)...")
    ipv_queries = [
        "IPV índice precio vivienda",
        "precio vivienda nueva segunda mano",
    ]
    
    all_ipv = []
    for query in ipv_queries:
        results = search_engine.search(query, top_k=5, score_threshold=0.4)
        all_ipv.extend(results)
    
    # Filtrar duplicados
    seen = set()
    ipv_results = []
    for r in all_ipv:
        if r['id'] not in seen:
            seen.add(r['id'])
            ipv_results.append(r)
    
    print(f"Encontradas {len(ipv_results)} series")
    for i, r in enumerate(ipv_results[:5], 1):
        print(f"  {i}. {r['name'][:70]}")
    
    # IPC - Índice de Precios al Consumo
    print("\n📊 Buscando IPC (Índice de Precios al Consumo)...")
    ipc_queries = [
        "IPC índice precios al consumo general",
        "inflación índice general",
    ]
    
    all_ipc = []
    for query in ipc_queries:
        results = search_engine.search(query, top_k=5, score_threshold=0.4)
        all_ipc.extend(results)
    
    seen = set()
    ipc_results = []
    for r in all_ipc:
        if r['id'] not in seen and 'IPC' in r['name']:
            seen.add(r['id'])
            ipc_results.append(r)
    
    print(f"Encontradas {len(ipc_results)} series")
    for i, r in enumerate(ipc_results[:5], 1):
        print(f"  {i}. {r['name'][:70]}")
    
    # Salarios - Coste laboral o salarios
    print("\n💰 Buscando datos de salarios/coste laboral...")
    salary_queries = [
        "coste laboral total nacional",
        "salario bruto anual",
        "ganancia media anual",
    ]
    
    all_salary = []
    for query in salary_queries:
        results = search_engine.search(query, top_k=5, score_threshold=0.4)
        all_salary.extend(results)
    
    seen = set()
    salary_results = []
    for r in all_salary:
        if r['id'] not in seen:
            seen.add(r['id'])
            salary_results.append(r)
    
    print(f"Encontradas {len(salary_results)} series")
    for i, r in enumerate(salary_results[:5], 1):
        print(f"  {i}. {r['name'][:70]}")
    
    # PASO 2: Intentar obtener datos de las series más prometedoras
    print()
    print("=" * 80)
    print("PASO 2: Extracción de Datos (probando múltiples series)")
    print("=" * 80)
    
    async with INEClient() as client:
        # Obtener IPV
        print("\n🏠 Probando series de vivienda...")
        ipv_data = None
        ipv_name = ""
        
        for i, ipv in enumerate(ipv_results[:10], 1):
            try:
                print(f"  [{i}] {ipv['name'][:60]}...", end=" ")
                data = await client.get_series_data(ipv['id'], last_n=200)
                df = aggregator.parse_ine_data(data)
                
                if len(df) >= 20:
                    ipv_data = df
                    ipv_name = ipv['name']
                    print(f"✓ {len(df)} puntos ({df.index[0].year}-{df.index[-1].year})")
                    break
                else:
                    print(f"✗ Solo {len(df)} puntos")
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}")
        
        if ipv_data is None:
            print("\n  ⚠️  No se encontraron datos suficientes de vivienda")
            print("  El INE puede no tener series históricas largas del IPV indexadas")
            return
        
        # Obtener IPC
        print("\n📊 Probando series de IPC...")
        ipc_data = None
        ipc_name = ""
        
        for i, ipc in enumerate(ipc_results[:10], 1):
            try:
                print(f"  [{i}] {ipc['name'][:60]}...", end=" ")
                data = await client.get_series_data(ipc['id'], last_n=200)
                df = aggregator.parse_ine_data(data)
                
                if len(df) >= 20:
                    ipc_data = df
                    ipc_name = ipc['name']
                    print(f"✓ {len(df)} puntos ({df.index[0].year}-{df.index[-1].year})")
                    break
                else:
                    print(f"✗ Solo {len(df)} puntos")
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}")
        
        if ipc_data is None:
            print("\n  ⚠️  No se encontraron datos del IPC")
            return
        
        # Obtener salarios
        print("\n💰 Probando series de salarios...")
        salary_data = None
        salary_name = ""
        
        for i, salary in enumerate(salary_results[:10], 1):
            try:
                print(f"  [{i}] {salary['name'][:60]}...", end=" ")
                data = await client.get_series_data(salary['id'], last_n=200)
                df = aggregator.parse_ine_data(data)
                
                if len(df) >= 10:
                    salary_data = df
                    salary_name = salary['name']
                    print(f"✓ {len(df)} puntos ({df.index[0].year}-{df.index[-1].year})")
                    break
                else:
                    print(f"✗ Solo {len(df)} puntos")
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}")
        
        if salary_data is None:
            print("\n  ⚠️  No se encontraron datos de salarios")
            print("  Análisis parcial: solo IPV vs IPC")
            salary_data = None  # Marcar como None para análisis parcial
    
    # PASO 3: Análisis
    print()
    print("=" * 80)
    print("PASO 3: Análisis")
    print("=" * 80)
    
    print(f"\n📋 Series utilizadas:")
    print(f"  • Vivienda: {ipv_name[:70]}")
    print(f"  • IPC:      {ipc_name[:70]}")
    if salary_data is not None:
        print(f"  • Salarios: {salary_name[:70]}")
    else:
        print(f"  • Salarios: NO DISPONIBLE")
    
    # Alinear IPV e IPC
    ipv_aligned, ipc_aligned, freq = aggregator.align_series_frequencies(ipv_data, ipc_data)
    
    combined = pd.merge(
        ipv_aligned,
        ipc_aligned,
        left_index=True,
        right_index=True,
        suffixes=("_ipv", "_ipc"),
        how='inner'
    )
    
    if salary_data is not None:
        salary_resampled = pd.DataFrame({'value': salary_data['value']}, index=salary_data.index)
        salary_aligned = salary_resampled.resample(freq).mean().dropna()
        
        combined = pd.merge(
            combined,
            salary_aligned,
            left_index=True,
            right_index=True,
            how='inner'
        )
        combined.columns = ['ipv', 'ipc', 'salary']
    else:
        combined.columns = ['ipv', 'ipc']
    
    if len(combined) < 3:
        print(f"\n✗ Datos superpuestos insuficientes: {len(combined)} puntos")
        return
    
    print(f"\n✓ {len(combined)} puntos alineados")
    print(f"  Período: {combined.index[0].date()} → {combined.index[-1].date()}")
    print(f"  Frecuencia: {freq}")
    
    # Normalizar a base 100
    combined['ipv_norm'] = (combined['ipv'] / combined['ipv'].iloc[0]) * 100
    combined['ipc_norm'] = (combined['ipc'] / combined['ipc'].iloc[0]) * 100
    
    # Precio real (ajustado por inflación)
    combined['ipv_real'] = (combined['ipv'] / combined['ipc']) * 100
    
    if 'salary' in combined.columns:
        combined['salary_norm'] = (combined['salary'] / combined['salary'].iloc[0]) * 100
        combined['affordability'] = combined['ipv_norm'] / combined['salary_norm']
    
    # Resultados
    print()
    print("=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    
    print(f"\n{'Fecha':<12} {'IPV':>8} {'IPC':>8} {'IPV Real':>10}", end="")
    if 'salary' in combined.columns:
        print(f" {'Salario':>8} {'Acceso':>8}")
    else:
        print()
    print("-" * 60)
    
    step = max(1, len(combined) // 10)
    for idx in range(0, len(combined), step):
        row = combined.iloc[idx]
        date = combined.index[idx].strftime("%Y-%m")
        print(f"{date:<12} {row['ipv_norm']:>8.1f} {row['ipc_norm']:>8.1f} {row['ipv_real']:>10.1f}", end="")
        if 'salary' in combined.columns:
            print(f" {row['salary_norm']:>8.1f} {row['affordability']:>8.2f}")
        else:
            print()
    
    row = combined.iloc[-1]
    date = combined.index[-1].strftime("%Y-%m")
    print(f"{date:<12} {row['ipv_norm']:>8.1f} {row['ipc_norm']:>8.1f} {row['ipv_real']:>10.1f}", end="")
    if 'salary' in combined.columns:
        print(f" {row['salary_norm']:>8.1f} {row['affordability']:>8.2f}")
    else:
        print()
    
    # Análisis
    print()
    print("=" * 80)
    print("VEREDICTO")
    print("=" * 80)
    
    ipv_change = ((combined['ipv_norm'].iloc[-1] - 100) / 100) * 100
    ipc_change = ((combined['ipc_norm'].iloc[-1] - 100) / 100) * 100
    real_change = ((combined['ipv_real'].iloc[-1] - 100) / 100) * 100
    
    print(f"\nCambio desde {combined.index[0].year}:")
    print(f"  • Precio vivienda (nominal): {ipv_change:+.1f}%")
    print(f"  • Inflación acumulada (IPC): {ipc_change:+.1f}%")
    print(f"  • Precio vivienda (REAL):    {real_change:+.1f}%")
    
    if salary_data is not None:
        salary_change = ((combined['salary_norm'].iloc[-1] - 100) / 100) * 100
        print(f"  • Salarios:                  {salary_change:+.1f}%")
        print(f"\n  💡 Ratio accesibilidad actual: {combined['affordability'].iloc[-1]:.2f}")
        print(f"     (1.0 = equilibrio, >1 = peor accesibilidad)")
    
    # Veredicto final
    print()
    if real_change > 50:
        print("🔴 VEREDICTO: La vivienda está MUCHO MÁS CARA en términos reales")
    elif real_change > 20:
        print("🟠 VEREDICTO: La vivienda está SIGNIFICATIVAMENTE MÁS CARA")
    elif real_change > 0:
        print("🟡 VEREDICTO: La vivienda está MÁS CARA que antes")
    else:
        print("🟢 VEREDICTO: La vivienda está MÁS BARATA en términos reales")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
