#!/usr/bin/env python3
"""
Análisis mejorado: Turismo vs Precios de Alquiler
"""

import asyncio
import json
from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator
from pathlib import Path

async def main():
    print("=" * 80)
    print("ANÁLISIS REAL: Turismo vs Precios de Vivienda en España")
    print("=" * 80)
    print()
    
    # Initialize
    search_engine = SemanticSearchEngine(
        index_path=Path("/app/data/faiss_index.bin"),
        metadata_path=Path("/app/data/series_metadata.pkl"),
    )
    
    try:
        search_engine.load_index()
        stats = search_engine.get_stats()
        print(f"✓ Índice semántico cargado: {stats['total_series']:,} series disponibles")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    print()
    print("=" * 80)
    print("PASO 1: Búsqueda Semántica - Turismo Internacional")
    print("=" * 80)
    
    tourism_queries = [
        "viajeros pernoctaciones hoteles turísticos",
        "entrada turistas extranjeros España",
        "ocupación hotelera turismo",
    ]
    
    all_tourism = []
    for query in tourism_queries:
        results = search_engine.search(query, top_k=3, score_threshold=0.5)
        all_tourism.extend(results)
    
    # Deduplicate by ID
    seen_ids = set()
    unique_tourism = []
    for r in all_tourism:
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_tourism.append(r)
    
    print(f"\nEncontradas {len(unique_tourism)} series únicas relacionadas con turismo:")
    for i, result in enumerate(unique_tourism[:10], 1):
        print(f"  {i}. {result['name'][:70]}...")
        print(f"      ID: {result['id']} | Score: {result['similarity_score']:.3f}")
    
    print()
    print("=" * 80)
    print("PASO 2: Búsqueda Semántica - Precios de Vivienda/Alquiler")
    print("=" * 80)
    
    housing_queries = [
        "índice precio vivienda alquiler",
        "coste renta vivienda",
        "precio alquileres inmobiliario",
    ]
    
    all_housing = []
    for query in housing_queries:
        results = search_engine.search(query, top_k=3, score_threshold=0.5)
        all_housing.extend(results)
    
    # Deduplicate
    seen_ids = set()
    unique_housing = []
    for r in all_housing:
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_housing.append(r)
    
    print(f"\nEncontradas {len(unique_housing)} series únicas de precios de vivienda:")
    for i, result in enumerate(unique_housing[:10], 1):
        print(f"  {i}. {result['name'][:70]}...")
        print(f"      ID: {result['id']} | Score: {result['similarity_score']:.3f}")
    
    # Now try to fetch and correlate
    if not unique_tourism or not unique_housing:
        print("\n✗ No se encontraron datos suficientes")
        return
    
    print()
    print("=" * 80)
    print("PASO 3: Extracción y Análisis de Datos")
    print("=" * 80)
    
    aggregator = DataAggregator()
    successful_correlations = []
    
    async with INEClient() as client:
        # Try top 3 tourism series
        for t_idx, tourism in enumerate(unique_tourism[:3]):
            print(f"\n--- Probando serie de turismo {t_idx+1}: {tourism['name'][:50]}...")
            
            try:
                t_data = await client.get_series_data(tourism['id'], last_n=60)
                t_df = aggregator.parse_ine_data(t_data)
                
                if t_df.empty or len(t_df) < 12:
                    print(f"    ✗ Datos insuficientes ({len(t_df)} puntos)")
                    continue
                
                print(f"    ✓ {len(t_df)} puntos | {t_df.index[0].date()} a {t_df.index[-1].date()}")
                
                # Try top 3 housing series
                for h_idx, housing in enumerate(unique_housing[:3]):
                    if t_idx == 0:  # Only print housing details once
                        print(f"      Comparando con: {housing['name'][:50]}...")
                    
                    try:
                        h_data = await client.get_series_data(housing['id'], last_n=60)
                        h_df = aggregator.parse_ine_data(h_data)
                        
                        if h_df.empty or len(h_df) < 12:
                            if t_idx == 0:
                                print(f"        ✗ Datos insuficientes ({len(h_df)} puntos)")
                            continue
                        
                        if t_idx == 0:
                            print(f"        ✓ {len(h_df)} puntos | {h_df.index[0].date()} a {h_df.index[-1].date()}")
                        
                        # Align and correlate
                        df1_aligned, df2_aligned, common_freq = aggregator.align_series_frequencies(t_df, h_df)
                        
                        import pandas as pd
                        combined = pd.merge(
                            df1_aligned,
                            df2_aligned,
                            left_index=True,
                            right_index=True,
                            suffixes=("_tourism", "_housing"),
                        )
                        
                        if len(combined) >= 12:
                            correlation = combined["value_tourism"].corr(combined["value_housing"])
                            
                            successful_correlations.append({
                                'tourism_id': tourism['id'],
                                'tourism_name': tourism['name'],
                                'housing_id': housing['id'],
                                'housing_name': housing['name'],
                                'correlation': correlation,
                                'points': len(combined),
                                'freq': common_freq,
                                'date_start': combined.index[0].date(),
                                'date_end': combined.index[-1].date(),
                            })
                            
                            if t_idx == 0:
                                print(f"          ✓ Correlación: {correlation:.3f} ({len(combined)} puntos superpuestos)")
                        
                    except Exception as e:
                        if t_idx == 0:
                            print(f"        ✗ Error: {str(e)[:50]}")
                        continue
                
            except Exception as e:
                print(f"    ✗ Error obteniendo datos de turismo: {str(e)[:50]}")
                continue
    
    print()
    print("=" * 80)
    print("RESULTADOS FINALES")
    print("=" * 80)
    
    if not successful_correlations:
        print("\n✗ No se pudieron calcular correlaciones con los datos disponibles")
        print("\nPosibles causas:")
        print("  • Las series no tienen fechas superpuestas")
        print("  • Los datos no están disponibles en el INE")
        print("  • Se requieren series diferentes")
        return
    
    # Sort by absolute correlation
    successful_correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    print(f"\n✓ Se encontraron {len(successful_correlations)} correlaciones válidas")
    print("\nTop 5 correlaciones más fuertes:\n")
    
    for i, corr in enumerate(successful_correlations[:5], 1):
        print(f"{i}. Correlación: {corr['correlation']:.3f}")
        print(f"   Turismo: {corr['tourism_name'][:60]}")
        print(f"   Vivienda: {corr['housing_name'][:60]}")
        print(f"   Datos: {corr['points']} puntos desde {corr['date_start']} a {corr['date_end']}")
        
        if abs(corr['correlation']) > 0.7:
            strength = "MUY FUERTE"
        elif abs(corr['correlation']) > 0.5:
            strength = "FUERTE"
        elif abs(corr['correlation']) > 0.3:
            strength = "MODERADA"
        else:
            strength = "DÉBIL"
        
        direction = "POSITIVA" if corr['correlation'] > 0 else "NEGATIVA"
        
        print(f"   Interpretación: Correlación {strength} {direction}")
        
        if abs(corr['correlation']) > 0.5:
            if corr['correlation'] > 0:
                print(f"   📊 Cuando el turismo ↑ los precios de vivienda tienden a ↑")
            else:
                print(f"   📊 Cuando el turismo ↑ los precios de vivienda tienden a ↓")
        print()
    
    print("=" * 80)
    print("CONCLUSIÓN")
    print("=" * 80)
    
    best = successful_correlations[0]
    if abs(best['correlation']) > 0.5:
        print("\n✅ SÍ existe una relación estadística significativa entre turismo")
        print("   y precios de vivienda en los datos del INE.")
        if best['correlation'] > 0:
            print("\n   Cuando aumenta la actividad turística, los precios de vivienda")
            print("   tienden a aumentar también.")
        print()
    else:
        print("\n⚠️  La correlación encontrada es relativamente débil.")
        print("   Esto podría indicar que otros factores tienen más impacto")
        print("   en los precios de vivienda que el turismo solo.")
        print()

if __name__ == "__main__":
    asyncio.run(main())
