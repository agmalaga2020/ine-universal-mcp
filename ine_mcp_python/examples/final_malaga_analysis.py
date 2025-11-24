#!/usr/bin/env python3
"""
ANÁLISIS DEFINITIVO: Turismo vs Vivienda en Málaga
Usando códigos de operación específicos del INE
"""

import asyncio
from ine_mcp.api.client import INEClient
from ine_mcp.tools.aggregation import DataAggregator

async def main():
    print("=" * 80)
    print("ANÁLISIS FINAL: Turismo vs Vivienda (Málaga/Andalucía)")
    print("=" * 80)
    print()
    
    aggregator = DataAggregator()
    
    async with INEClient() as client:
        # Paso 1: Explorar Encuesta de Ocupación Hotelera (código 30235)
        print("PASO 1: Explorando Encuesta de Ocupación Hotelera (EOH)")
        print("-" * 80)
        
        try:
            eoh_series = await client.get_operation_series("30235")
            print(f"✓ {len(eoh_series)} series encontradas en EOH")
            
            # Filtrar por Málaga y pernoctaciones
            malaga_pernoctaciones = []
            andalucia_pernoctaciones = []
            
            for s in eoh_series:
                name = s.get('Nombre', '')
                if 'Málaga' in name and 'pernoctaciones' in name.lower():
                    malaga_pernoctaciones.append(s)
                elif 'Andalucía' in name and 'pernoctaciones' in name.lower():
                    andalucia_pernoctaciones.append(s)
            
            print(f"\nSeries de pernoctaciones en Málaga: {len(malaga_pernoctaciones)}")
            for s in malaga_pernoctaciones[:5]:
                print(f"  • {s.get('Nombre', '')[:70]}")
                print(f"    ID: {s.get('COD', s.get('Id', 'N/A'))}")
            
            print(f"\nSeries de pernoctaciones en Andalucía: {len(andalucia_pernoctaciones)}")
            for s in andalucia_pernoctaciones[:3]:
                print(f"  • {s.get('Nombre', '')[:70]}")
                print(f"    ID: {s.get('COD', s.get('Id', 'N/A'))}")
            
        except Exception as e:
            print(f"✗ Error en EOH: {e}")
            malaga_pernoctaciones = []
            andalucia_pernoctaciones = []
        
        # Paso 2: Explorar Índice de Precios de la Vivienda (código 30457)
        print()
        print("PASO 2: Explorando Índice de Precios de la Vivienda (IPV)")
        print("-" * 80)
        
        try:
            ipv_series = await client.get_operation_series("30457")
            print(f"✓ {len(ipv_series)} series encontradas en IPV")
            
            # Filtrar por Málaga
            malaga_ipv = []
            andalucia_ipv = []
            
            for s in ipv_series:
                name = s.get('Nombre', '')
                if 'Málaga' in name:
                    malaga_ipv.append(s)
                elif 'Andalucía' in name:
                    andalucia_ipv.append(s)
            
            print(f"\nSeries de IPV en Málaga: {len(malaga_ipv)}")
            for s in malaga_ipv[:10]:
                print(f"  • {s.get('Nombre', '')[:70]}")
                print(f"    ID: {s.get('COD', s.get('Id', 'N/A'))}")
            
            print(f"\nSeries de IPV en Andalucía: {len(andalucia_ipv)}")
            for s in andalucia_ipv[:5]:
                print(f"  • {s.get('Nombre', '')[:70]}")
                print(f"    ID: {s.get('COD', s.get('Id', 'N/A'))}")
            
        except Exception as e:
            print(f"✗ Error en IPV: {e}")
            malaga_ipv = []
            andalucia_ipv = []
        
        # Paso 3: Análisis de correlación
        print()
        print("=" * 80)
        print("PASO 3: Análisis de Correlación")
        print("=" * 80)
        
        tourism_series = malaga_pernoctaciones if malaga_pernoctaciones else andalucia_pernoctaciones
        housing_series = malaga_ipv if malaga_ipv else andalucia_ipv
        
        if not tourism_series:
            print("\n✗ No hay datos de turismo disponibles")
            return
        
        if not housing_series:
            print("\n✗ No hay datos de vivienda disponibles")
            return
        
        correlations = []
        
        for t_idx, tourism in enumerate(tourism_series[:3], 1):
            print(f"\n[{t_idx}] Turismo: {tourism.get('Nombre', '')[:60]}...")
            t_id = tourism.get('COD', tourism.get('Id'))
            
            try:
                t_data = await client.get_series_data(t_id, last_n=60)
                t_df = aggregator.parse_ine_data(t_data)
                
                if t_df.empty or len(t_df) < 12:
                    print(f"    ✗ Insuficiente ({len(t_df)} puntos)")
                    continue
                
                print(f"    ✓ {len(t_df)} puntos | {t_df.index[0].date()} → {t_df.index[-1].date()}")
                
                for h_idx, housing in enumerate(housing_series[:3], 1):
                    if t_idx == 1:
                        print(f"      Vs [{h_idx}] {housing.get('Nombre', '')[:50]}...")
                    
                    h_id = housing.get('COD', housing.get('Id'))
                    
                    try:
                        h_data = await client.get_series_data(h_id, last_n=60)
                        h_df = aggregator.parse_ine_data(h_data)
                        
                        if h_df.empty or len(h_df) < 12:
                            if t_idx == 1:
                                print(f"          ✗ Insuficiente ({len(h_df)} puntos)")
                            continue
                        
                        if t_idx == 1:
                            print(f"          ✓ {len(h_df)} puntos | {h_df.index[0].date()} → {h_df.index[-1].date()}")
                        
                        df1_al, df2_al, freq = aggregator.align_series_frequencies(t_df, h_df)
                        
                        import pandas as pd
                        combined = pd.merge(df1_al, df2_al, left_index=True, right_index=True, suffixes=("_t", "_h"))
                        
                        if len(combined) >= 12:
                            corr = combined["value_t"].corr(combined["value_h"])
                            
                            correlations.append({
                                'tourism': tourism.get('Nombre', ''),
                                'housing': housing.get('Nombre', ''),
                                'correlation': corr,
                                'points': len(combined),
                                'freq': freq,
                                'start': combined.index[0].date(),
                                'end': combined.index[-1].date(),
                            })
                            
                            if t_idx == 1:
                                print(f"            ✓ r = {corr:+.3f} ({len(combined)} puntos)")
                    
                    except Exception as e:
                        if t_idx == 1:
                            print(f"          ✗ {str(e)[:40]}")
            
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
        
        print()
        print("=" * 80)
        print("RESULTADOS FINALES")
        print("=" * 80)
        
        if not correlations:
            print("\n❌ No se pudieron calcular correlaciones")
            return
        
        correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        print(f"\n✓ {len(correlations)} correlaciones calculadas\n")
        
        for i, c in enumerate(correlations[:5], 1):
            print(f"{i}. Correlación: {c['correlation']:+.3f}")
            print(f"   Turismo:  {c['tourism'][:60]}")
            print(f"   Vivienda: {c['housing'][:60]}")
            print(f"   Período: {c['start']} → {c['end']} ({c['points']} pts, {c['freq']})")
            
            strength = ("★★★ MUY FUERTE" if abs(c['correlation']) > 0.7
                       else "★★ FUERTE" if abs(c['correlation']) > 0.5
                       else "★ MODERADA" if abs(c['correlation']) > 0.3
                       else "DÉBIL")
            
            print(f"   {strength}")
            
            if abs(c['correlation']) > 0.5:
                if c['correlation'] > 0:
                    print(f"   📈 Turismo ↑ → Precios ↑")
                else:
                    print(f"   📉 Turismo ↑ → Precios ↓")
            print()
        
        print("=" * 80)
        print("VEREDICTO")
        print("=" * 80)
        
        best = correlations[0]
        
        if abs(best['correlation']) > 0.6:
            print(f"\n✅ CORRELACIÓN SIGNIFICATIVA: {best['correlation']:+.3f}")
            print("\n   Con datos provinciales/regionales del INE, se confirma")
            print("   una relación estadísticamente relevante.")
        elif abs(best['correlation']) > 0.3:
            print(f"\n⚠️  CORRELACIÓN MODERADA: {best['correlation']:+.3f}")
            print("\n   Existe relación, pero otros factores también influyen.")
        else:
            print(f"\n❌ CORRELACIÓN DÉBIL: {best['correlation']:+.3f}")
            print("\n   Los datos disponibles no muestran señal clara.")
        print()

if __name__ == "__main__":
    asyncio.run(main())
