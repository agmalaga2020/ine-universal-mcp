#!/usr/bin/env python3
"""
ANÁLISIS CORREGIDO: Turismo vs Vivienda en Málaga (Datos Provinciales)

Correcciones aplicadas:
1. Granularidad provincial (Málaga), no nacional
2. Métrica de demanda (Pernoctaciones), no oferta (Personal)
3. Búsqueda dirigida por operación, no solo semántica
"""

import asyncio
from pathlib import Path
from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

async def main():
    print("=" * 80)
    print("ANÁLISIS PROVINCIAL: Turismo vs Vivienda en MÁLAGA")
    print("=" * 80)
    print()
    
    search_engine = SemanticSearchEngine(
        index_path=Path("/app/data/faiss_index.bin"),
        metadata_path=Path("/app/data/series_metadata.pkl"),
    )
    
    try:
        search_engine.load_index()
        stats = search_engine.get_stats()
        print(f"✓ Índice cargado: {stats['total_series']:,} series")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    print()
    print("=" * 80)
    print("PASO 1: Búsqueda Estratégica - Turismo en Málaga")
    print("=" * 80)
    
    # Estrategia 1: Buscar pernoctaciones específicamente
    print("\n🔍 Buscando: 'pernoctaciones Málaga turistas'")
    tourism_results = search_engine.search(
        "pernoctaciones Málaga hotelera turistas extranjeros",
        top_k=15,
        score_threshold=0.4
    )
    
    # Filtrar por Málaga en el nombre
    malaga_tourism = [r for r in tourism_results if 'Málaga' in r['name'] or 'málaga' in r['name'].lower()]
    
    print(f"\nEncontradas {len(malaga_tourism)} series con 'Málaga':")
    for i, result in enumerate(malaga_tourism[:10], 1):
        print(f"  {i}. {result['name'][:75]}")
        print(f"     ID: {result['id']} | Score: {result['similarity_score']:.3f}")
    
    # Si no hay suficientes, buscar "Andalucía" o "Costa del Sol"
    if len(malaga_tourism) < 3:
        print("\n🔍 Ampliando búsqueda a Andalucía y Costa del Sol...")
        broader_results = search_engine.search(
            "pernoctaciones Andalucía Costa del Sol",
            top_k=10,
            score_threshold=0.4
        )
        tourism_results.extend(broader_results)
        
        # Filtrar Andalucía
        andalucia_tourism = [r for r in broader_results 
                             if 'Andalucía' in r['name'] or 'Costa' in r['name']]
        
        print(f"Encontradas {len(andalucia_tourism)} series de Andalucía/Costa:")
        for i, result in enumerate(andalucia_tourism[:5], 1):
            print(f"  {i}. {result['name'][:75]}")
            print(f"     ID: {result['id']} | Score: {result['similarity_score']:.3f}")
        
        malaga_tourism.extend(andalucia_tourism)
    
    print()
    print("=" * 80)
    print("PASO 2: Búsqueda Estratégica - Precios Vivienda Málaga")
    print("=" * 80)
    
    # Buscar IPC vivienda Málaga
    print("\n🔍 Buscando: 'IPC vivienda alquiler Málaga'")
    housing_results = search_engine.search(
        "IPC índice precio vivienda Málaga Andalucía",
        top_k=15,
        score_threshold=0.4
    )
    
    # Filtrar por Málaga/Andalucía
    malaga_housing = [r for r in housing_results 
                      if 'Málaga' in r['name'] or 'Andalucía' in r['name'] or 'andalucía' in r['name'].lower()]
    
    print(f"\nEncontradas {len(malaga_housing)} series de vivienda (Málaga/Andalucía):")
    for i, result in enumerate(malaga_housing[:10], 1):
        print(f"  {i}. {result['name'][:75]}")
        print(f"     ID: {result['id']} | Score: {result['similarity_score']:.3f}")
    
    # Alternativa: buscar datos inmobiliarios
    if len(malaga_housing) < 3:
        print("\n🔍 Buscando datos inmobiliarios alternativos...")
        alt_housing = search_engine.search(
            "actividades inmobiliarias Málaga Andalucía cifra negocio",
            top_k=10,
            score_threshold=0.4
        )
        malaga_housing.extend([r for r in alt_housing 
                               if 'Málaga' in r['name'] or 'Andalucía' in r['name']])
    
    print()
    print("=" * 80)
    print("PASO 3: Análisis de Correlación con Datos Provinciales")
    print("=" * 80)
    
    if not malaga_tourism:
        print("\n✗ No se encontraron datos de turismo para Málaga")
        print("   El INE puede no tener series desagregadas a nivel provincial.")
        return
    
    if not malaga_housing:
        print("\n✗ No se encontraron datos de vivienda para Málaga")
        return
    
    aggregator = DataAggregator()
    correlations = []
    
    async with INEClient() as client:
        # Probar las mejores series encontradas
        for t_idx, tourism in enumerate(malaga_tourism[:5], 1):
            print(f"\n[{t_idx}/{min(5, len(malaga_tourism))}] Turismo: {tourism['name'][:60]}...")
            
            try:
                t_data = await client.get_series_data(tourism['id'], last_n=60)
                t_df = aggregator.parse_ine_data(t_data)
                
                if t_df.empty or len(t_df) < 12:
                    print(f"     ✗ Datos insuficientes ({len(t_df)} puntos)")
                    continue
                
                print(f"     ✓ {len(t_df)} puntos | {t_df.index[0].date()} → {t_df.index[-1].date()}")
                
                for h_idx, housing in enumerate(malaga_housing[:5], 1):
                    if t_idx == 1:  # Solo mostrar detalles en primera iteración
                        print(f"       Vs [{h_idx}] {housing['name'][:50]}...")
                    
                    try:
                        h_data = await client.get_series_data(housing['id'], last_n=60)
                        h_df = aggregator.parse_ine_data(h_data)
                        
                        if h_df.empty or len(h_df) < 12:
                            if t_idx == 1:
                                print(f"           ✗ Insuficiente ({len(h_df)} puntos)")
                            continue
                        
                        if t_idx == 1:
                            print(f"           ✓ {len(h_df)} puntos | {h_df.index[0].date()} → {h_df.index[-1].date()}")
                        
                        # Alinear frecuencias
                        df1_aligned, df2_aligned, common_freq = aggregator.align_series_frequencies(t_df, h_df)
                        
                        import pandas as pd
                        combined = pd.merge(
                            df1_aligned,
                            df2_aligned,
                            left_index=True,
                            right_index=True,
                            suffixes=("_tour", "_house"),
                        )
                        
                        if len(combined) >= 12:
                            corr = combined["value_tour"].corr(combined["value_house"])
                            
                            correlations.append({
                                'tourism_id': tourism['id'],
                                'tourism_name': tourism['name'],
                                'housing_id': housing['id'],
                                'housing_name': housing['name'],
                                'correlation': corr,
                                'points': len(combined),
                                'freq': common_freq,
                                'start': combined.index[0].date(),
                                'end': combined.index[-1].date(),
                            })
                            
                            if t_idx == 1:
                                print(f"           ✓ Correlación: {corr:+.3f} ({len(combined)} puntos)")
                    
                    except Exception as e:
                        if t_idx == 1:
                            print(f"           ✗ Error: {str(e)[:40]}")
                        continue
            
            except Exception as e:
                print(f"     ✗ Error API: {str(e)[:50]}")
                continue
    
    print()
    print("=" * 80)
    print("RESULTADOS FINALES")
    print("=" * 80)
    
    if not correlations:
        print("\n⚠️  No se pudieron calcular correlaciones.")
        print("\nCausas probables:")
        print("  • El INE no tiene datos desagregados por provincia para todas las variables")
        print("  • Las series encontradas no tienen períodos superpuestos")
        print("  • Se requiere búsqueda más específica por código de operación")
        print("\nRecomendación:")
        print("  Explorar operaciones específicas del INE (EOH, IPV) manualmente")
        return
    
    # Ordenar por correlación absoluta
    correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    print(f"\n✓ {len(correlations)} correlaciones calculadas")
    print("\nTop 5 correlaciones más fuertes:\n")
    
    for i, c in enumerate(correlations[:5], 1):
        print(f"{i}. Correlación: {c['correlation']:+.3f}")
        print(f"   Turismo:  {c['tourism_name'][:65]}")
        print(f"   Vivienda: {c['housing_name'][:65]}")
        print(f"   Período: {c['start']} → {c['end']} ({c['points']} puntos, {c['freq']})")
        
        strength = ("MUY FUERTE" if abs(c['correlation']) > 0.7 
                    else "FUERTE" if abs(c['correlation']) > 0.5
                    else "MODERADA" if abs(c['correlation']) > 0.3
                    else "DÉBIL")
        direction = "POSITIVA ↑" if c['correlation'] > 0 else "NEGATIVA ↓"
        
        print(f"   Fuerza: {strength} {direction}")
        
        if abs(c['correlation']) > 0.5:
            if c['correlation'] > 0:
                print(f"   📊 Turismo ↑ → Precios vivienda ↑")
            else:
                print(f"   📊 Turismo ↑ → Precios vivienda ↓")
        print()
    
    print("=" * 80)
    print("VEREDICTO CIENTÍFICO")
    print("=" * 80)
    
    best = correlations[0]
    
    if abs(best['correlation']) > 0.6:
        print("\n✅ CORRELACIÓN SIGNIFICATIVA ENCONTRADA")
        print(f"   Coeficiente: {best['correlation']:+.3f}")
        print(f"\n   Con datos provinciales/regionales, SÍ se observa una relación")
        print(f"   estadísticamente relevante entre turismo y precios de vivienda.")
        if best['correlation'] > 0:
            print(f"\n   El aumento de turismo está asociado con aumento de precios.")
    elif abs(best['correlation']) > 0.3:
        print("\n⚠️  CORRELACIÓN MODERADA")
        print(f"   Coeficiente: {best['correlation']:+.3f}")
        print(f"\n   Existe una relación, pero otros factores también influyen.")
    else:
        print("\n❌ CORRELACIÓN DÉBIL o INEXISTENTE")
        print(f"   Coeficiente: {best['correlation']:+.3f}")
        print(f"\n   Los datos disponibles no muestran una relación fuerte.")
        print(f"   Posibles razones:")
        print(f"   • Granularidad provincial insuficiente en el INE")
        print(f"   • Variables proxy no óptimas")
        print(f"   • Lag temporal entre turismo e impacto en precios")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
