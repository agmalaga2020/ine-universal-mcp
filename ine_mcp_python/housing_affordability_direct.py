#!/usr/bin/env python3
"""
ANÁLISIS DEFINITIVO: Accesibilidad a la Vivienda

Usando IDs conocidos del INE para asegurar que obtenemos las series correctas
"""

import asyncio
from ine_mcp.api.client import INEClient
from ine_mcp.tools.aggregation import DataAggregator
import pandas as pd

# IDs conocidos de series clave del INE
KNOWN_SERIES = {
    # IPC General (base 2021)
    'ipc_general_2021': 'IPC251856',  # IPC General. Nacional
    'ipc_general_2016': 'IPC186417',  # IPC General (base 2016)
    
    # IPV - Índice de Precios de Vivienda
    #'ipv_general': 'IPV931',  # IPV General
    
    # Otros que podemos probar
    'ipc_total': 'IPC306762',  # Otra serie IPC
}

async def main():
    print("=" * 80)
    print("ANÁLISIS: ¿Está la vivienda más cara que nunca? (Método Directo)")
    print("=" * 80)
    print()
    
    aggregator = DataAggregator()
    
    async with INEClient() as client:
        print("PASO 1: Extracción de Datos con IDs Conocidos")
        print("-" * 80)
        
        # Intentar obtener IPC
        print("\n📊 IPC (Índice de Precios al Consumo)...")
        ipc_data = None
        ipc_name = ""
        
        for key, series_id in KNOWN_SERIES.items():
            if 'ipc' not in key:
                continue
            
            try:
                print(f"  Probando {key} ({series_id})...", end=" ")
                data = await client.get_series_data(series_id, last_n=300)
                df = aggregator.parse_ine_data(data)
                
                if len(df) > 0:
                    ipc_data = df
                    ipc_name = key
                    print(f"✓ {len(df)} puntos ({df.index[0].year}-{df.index[-1].year})")
                    break
                else:
                    print("✗ Sin datos")
            except Exception as e:
                print(f"✗ {str(e)[:40]}")
        
        if ipc_data is None:
            print("\n⚠️  No se pudo obtener el IPC con IDs conocidos")
            print("Probando con búsqueda por operación...")
            
            # Intentar obtener operación del IPC (código 30138)
            try:
                print("\n  Explorando operación IPC (30138)...")
                series_list = await client.get_operation_series("30138")
                
                if series_list:
                    print(f"  Encontradas {len(series_list)} series en la operación IPC")
                    
                    # Buscar serie "General" o "Total"
                    for s in series_list[:20]:
                        name = s.get('Nombre', '')
                        if ('Nacional' in name or 'General' in name) and 'índice' in name.lower():
                            series_id = s.get('COD', s.get('Id'))
                            print(f"\n  Probando: {name[:60]}...", end=" ")
                            
                            try:
                                data = await client.get_series_data(series_id, last_n=300)
                                df = aggregator.parse_ine_data(data)
                                
                                if len(df) >= 20:
                                    ipc_data = df
                                    ipc_name = name
                                    print(f"✓ {len(df)} puntos")
                                    break
                            except:
                                print("✗")
                    
            except Exception as e:
                print(f"  ✗ Error explorando operación: {str(e)[:50]}")
        
        if ipc_data is None:
            print("\n❌ No se pudo obtener datos del IPC")
            print("El análisis no puede continuar sin datos de inflación")
            return
        
        # Intentar obtener IPV
        print("\n🏠 IPV (Índice de Precios de Vivienda)...")
        ipv_data = None
        ipv_name = ""
        
        # Probar con operación 30457 (IPV)
        try:
            print("  Explorando operación IPV (30457)...")
            series_list = await client.get_operation_series("30457")
            
            if series_list:
                print(f"  Encontradas {len(series_list)} series")
                
                # Buscar serie general/nacional
                for s in series_list[:20]:
                    name = s.get('Nombre', '')
                    if 'Nacional' in name or 'General' in name or 'Total' in name:
                        series_id = s.get('COD', s.get('Id'))
                        print(f"\n  Probando: {name[:60]}...", end=" ")
                        
                        try:
                            data = await client.get_series_data(series_id, last_n=300)
                            df = aggregator.parse_ine_data(data)
                            
                            if len(df) >= 10:
                                ipv_data = df
                                ipv_name = name
                                print(f"✓ {len(df)} puntos")
                                break
                        except:
                            print("✗")
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:50]}")
        
        if ipv_data is None:
            print("\n⚠️  No se pudo obtener IPV")
            print("Continuando solo con análisis de IPC")
        
        # Intentar obtener salarios
        print("\n💰 Salarios/Coste Laboral...")
        salary_data = None
        salary_name = ""
        
        # Probar con operaciones de salarios/EPA
        for op_code in ["30134", "30308"]:  # Encuesta Trimestral de Coste Laboral, EPA
            try:
                print(f"  Explorando operación {op_code}...")
                series_list = await client.get_operation_series(op_code)
                
                if series_list:
                    print(f"  Encontradas {len(series_list)} series")
                    
                    for s in series_list[:30]:
                        name = s.get('Nombre', '')
                        if ('coste' in name.lower() or 'salario' in name.lower()) and 'total' in name.lower():
                            series_id = s.get('COD', s.get('Id'))
                            print(f"\n  Probando: {name[:60]}...", end=" ")
                            
                            try:
                                data = await client.get_series_data(series_id, last_n=200)
                                df = aggregator.parse_ine_data(data)
                                
                                if len(df) >= 10:
                                    salary_data = df
                                    salary_name = name
                                    print(f"✓ {len(df)} puntos")
                                    break
                            except:
                                print("✗")
                    
                    if salary_data:
                        break
            except Exception as e:
                print(f"  ✗ Error: {str(e)[:40]}")
        
        if salary_data is None:
            print("\n⚠️  No se pudieron obtener datos de salarios")
    
    # ANÁLISIS
    print()
    print("=" * 80)
    print("ANÁLISIS")
    print("=" * 80)
    
    print(f"\n✓ Datos obtenidos:")
    print(f"  • IPC: {ipc_name}")
    print(f"    {len(ipc_data)} puntos: {ipc_data.index[0].date()} → {ipc_data.index[-1].date()}")
    
    if ipv_data is not None:
        print(f"  • IPV: {ipv_name}")
        print(f"    {len(ipv_data)} puntos: {ipv_data.index[0].date()} → {ipv_data.index[-1].date()}")
    
    if salary_data is not None:
        print(f"  • Salarios: {salary_name}")
        print(f"    {len(salary_data)} puntos: {salary_data.index[0].date()} → {salary_data.index[-1].date()}")
    
    # Análisis del IPC
    print()
    print("=" * 80)
    print("ANÁLISIS DEL IPC (Inflación Acumulada)")
    print("=" * 80)
    
    initial_ipc = ipc_data['value'].iloc[0]
    current_ipc = ipc_data['value'].iloc[-1]
    inflation = ((current_ipc / initial_ipc) - 1) * 100
    
    print(f"\nPeríodo: {ipc_data.index[0].year} - {ipc_data.index[-1].year}")
    print(f"IPC inicial: {initial_ipc:.2f}")
    print(f"IPC actual:  {current_ipc:.2f}")
    print(f"Inflación acumulada: {inflation:+.1f}%")
    
    # Si tenemos IPV
    if ipv_data is not None:
        print()
        print("=" * 80)
        print("ANÁLISIS IPV vs IPC")
        print("="* 80)
        
        # Alinear
        ipv_al, ipc_al, freq = aggregator.align_series_frequencies(ipv_data, ipc_data)
        combined = pd.merge(ipv_al, ipc_al, left_index=True, right_index=True, 
                           suffixes=('_ipv', '_ipc'), how='inner')
        
        if len(combined) >= 2:
            combined['ipv_real'] = (combined['value_ipv'] / combined['value_ipc']) * 100
            
            initial_real = combined['ipv_real'].iloc[0]
            current_real = combined['ipv_real'].iloc[-1]
            real_change = ((current_real / initial_real) - 1) * 100
            
            print(f"\n✓ {len(combined)} puntos superpuestos")
            print(f"Período: {combined.index[0].year} - {combined.index[-1].year}")
            print(f"\nPrecio vivienda (términos reales, ajustado por IPC):")
            print(f"  Cambio: {real_change:+.1f}%")
            
            if real_change > 30:
                print("\n🔴 La vivienda está MUCHO MÁS CARA en términos reales")
            elif real_change > 10:
                print("\n🟠 La vivienda está SIGNIFICATIVAMENTE MÁS CARA")
            elif real_change > 0:
                print("\n🟡 La vivienda ha subido por encima de la inflación")
            else:
                print("\n🟢 La vivienda ha subido menos que la inflación")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
