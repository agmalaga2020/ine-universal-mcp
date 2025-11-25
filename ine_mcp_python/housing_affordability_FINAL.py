#!/usr/bin/env python3
"""
RESPUESTA DEFINITIVA: ¿Está la vivienda más cara que nunca en España?

Usando tablas reales del INE:
- Tabla 24051: IPV (Índice de Precios de Vivienda)
- Tabla 50902: IPC General
- Análisis histórico completo
"""

import asyncio
from ine_mcp.api.client import INEClient
from ine_mcp.tools.aggregation import DataAggregator
import pandas as pd
import json

async def main():
    print("=" * 80)
    print("¿ESTÁ LA VIVIENDA MÁS CARA QUE NUNCA EN ESPAÑA?")
    print("Análisis con datos oficiales del INE")
    print("=" * 80)
    print()
    
    aggregator = DataAggregator()
    
    async with INEClient() as client:
        # PASO 1: Obtener IPV completo (máximo disponible)
        print("PASO 1: Obteniendo Índice de Precios de Vivienda (IPV)")
        print("-" * 80)
        
        try:
            # Obtener todos los datos disponibles del IPV
            ipv_raw = await client._request("GET", "/DATOS_TABLA/24051", params={"nult": 500})
            
            if isinstance(ipv_raw, dict) and "Data" in ipv_raw:
                ipv_data_list = ipv_raw["Data"]
            elif isinstance(ipv_raw, list):
                ipv_data_list = ipv_raw
            else:
                print(f"✗ Formato inesperado: {type(ipv_raw)}")
                return
            
            # Convertir a DataFrame
            ipv_df = pd.DataFrame(ipv_data_list)
            ipv_df['date'] = pd.to_datetime(ipv_df['Fecha'], unit='ms')
            ipv_df = ipv_df.set_index('date').sort_index()
            ipv_df = ipv_df[['Valor']].rename(columns={'Valor': 'ipv'})
            
            print(f"✓ IPV obtenido: {len(ipv_df)} datos")
            print(f"  Período: {ipv_df.index[0].date()} → {ipv_df.index[-1].date()}")
            print(f"  IPV actual: {ipv_df['ipv'].iloc[-1]:.2f}")
            print(f"  IPV inicial: {ipv_df['ipv'].iloc[0]:.2f}")
            
        except Exception as e:
            print(f"✗ Error obteniendo IPV: {e}")
            return
        
        # PASO 2: Obtener IPC
        print()
        print("PASO 2: Obteniendo IPC General")
        print("-" * 80)
        
        try:
            ipc_raw = await client._request("GET", "/DATOS_TABLA/50902", params={"nult": 500})
            
            if isinstance(ipc_raw, dict) and "Data" in ipc_raw:
                ipc_data_list = ipc_raw["Data"]
            elif isinstance(ipc_raw, list):
                ipc_data_list = ipc_raw
            else:
                print("✗ Formato inesperado")
                ipc_df = None
        
            if ipc_data_list:
                ipc_df = pd.DataFrame(ipc_data_list)
                ipc_df['date'] = pd.to_datetime(ipc_df['Fecha'], unit='ms')
                ipc_df = ipc_df.set_index('date').sort_index()
                ipc_df = ipc_df[['Valor']].rename(columns={'Valor': 'ipc'})
                
                print(f"✓ IPC obtenido: {len(ipc_df)} datos")
                print(f"  Período: {ipc_df.index[0].date()} → {ipc_df.index[-1].date()}")
            else:
                ipc_df = None
                print("⚠️  No se pudo obtener IPC")
        
        except Exception as e:
            print(f"⚠️  Error obteniendo IPC: {e}")
            ipc_df = None
    
    # PASO 3: Análisis del IPV
    print()
    print("=" * 80)
    print("ANÁLISIS DEL ÍNDICE DE PRECIOS DE VIVIENDA")
    print("=" * 80)
    
    # Valores clave
    ipv_actual = ipv_df['ipv'].iloc[-1]
    ipv_inicial = ipv_df['ipv'].iloc[0]
    ipv_max = ipv_df['ipv'].max()
    ipv_min = ipv_df['ipv'].min()
    
    fecha_max = ipv_df['ipv'].idxmax()
    fecha_min = ipv_df['ipv'].idxmin()
    fecha_actual = ipv_df.index[-1]
    
    print(f"\n📊 Estadísticas del IPV:")
    print(f"  • Valor actual ({fecha_actual.strftime('%Y-%m')}): {ipv_actual:.2f}")
    print(f"  • Máximo histórico ({fecha_max.strftime('%Y-%m')}): {ipv_max:.2f}")
    print(f"  • Mínimo histórico ({fecha_min.strftime('%Y-%m')}): {ipv_min:.2f}")
    print(f"  • Valor inicial ({ipv_df.index[0].strftime('%Y-%m')}): {ipv_inicial:.2f}")
    
    # ¿Está en máximos?
    distancia_al_maximo = ((ipv_actual - ipv_max) / ipv_max) * 100
    
    print(f"\n🎯 Posición actual:")
    print(f"  • Distancia al máximo histórico: {distancia_al_maximo:+.1f}%")
    
    if ipv_actual >= ipv_max * 0.99:  # Dentro del 1% del máximo
        print(f"  • ⚠️  ESTÁ EN MÁXIMOS HISTÓRICOS")
        en_maximos = True
    elif ipv_actual >= ipv_max * 0.95:
        print(f"  • ⚠️  Muy cerca del máximo histórico")
        en_maximos = False
    else:
        print(f"  • ℹ️  Por debajo del máximo histórico")
        en_maximos = False
    
    # Cambios por período
    print(f"\n📈 Evolución:")
    
    # Cambio total
    cambio_total = ((ipv_actual - ipv_inicial) / ipv_inicial) * 100
    print(f"  • Desde {ipv_df.index[0].year}: {cambio_total:+.1f}%")
    
    # Últimos 5 años
    if len(ipv_df) >= 60:
        ipv_5y_ago = ipv_df['ipv'].iloc[-60]
        cambio_5y = ((ipv_actual - ipv_5y_ago) / ipv_5y_ago) * 100
        print(f"  • Últimos 5 años: {cambio_5y:+.1f}%")
    
    # Último año
    if len(ipv_df) >= 12:
        ipv_1y_ago = ipv_df['ipv'].iloc[-12]
        cambio_1y = ((ipv_actual - ipv_1y_ago) / ipv_1y_ago) * 100
        print(f"  • Último año: {cambio_1y:+.1f}%")
    
    # PASO 4: Ajuste por inflación (si tenemos IPC)
    if ipc_df is not None:
        print()
        print("=" * 80)
        print("ANÁLISIS AJUSTADO POR INFLACIÓN")
        print("=" * 80)
        
        # Alinear IPV e IPC
        ipv_aligned, ipc_aligned, freq = aggregator.align_series_frequencies(
            ipv_df, ipc_df
        )
        
        combined = pd.merge(
            ipv_aligned,
            ipc_aligned,
            left_index=True,
            right_index=True,
            how='inner'
        )
        
        if len(combined) >= 2:
            # Calcular IPV real (ajustado por IPC)
            combined['ipv_real'] = (combined['ipv'] / combined['ipc']) * 100
            
            ipv_real_actual = combined['ipv_real'].iloc[-1]
            ipv_real_inicial = combined['ipv_real'].iloc[0]
            ipv_real_max = combined['ipv_real'].max()
            
            fecha_max_real = combined['ipv_real'].idxmax()
            
            print(f"\n📊 IPV en términos reales (ajustado por inflación):")
            print(f"  • IPV real actual: {ipv_real_actual:.2f}")
            print(f"  • IPV real máximo ({fecha_max_real.strftime('%Y-%m')}): {ipv_real_max:.2f}")
            
            cambio_real = ((ipv_real_actual - ipv_real_inicial) / ipv_real_inicial) * 100
            print(f"  • Cambio real desde inicio: {cambio_real:+.1f}%")
            
            distancia_max_real = ((ipv_real_actual - ipv_real_max) / ipv_real_max) * 100
            print(f"  • Distancia al máximo real: {distancia_max_real:+.1f}%")
    
    # PASO 5: VEREDICTO FINAL
    print()
    print("=" * 80)
    print("VEREDICTO FINAL")
    print("=" * 80)
    print()
    
    if en_maximos:
        print("🔴 SÍ, LA VIVIENDA ESTÁ EN MÁXIMOS HISTÓRICOS")
        print()
        print(f"   El IPV actual ({ipv_actual:.2f}) está prácticamente en el")
        print(f"   nivel más alto jamás registrado ({ipv_max:.2f}).")
        print()
        print(f"   Desde el inicio de la serie ({ipv_df.index[0].year}),")
        print(f"   los precios han subido un {cambio_total:.1f}%.")
        
    elif distancia_al_maximo > -5:
        print("🟠 LA VIVIENDA ESTÁ MUY CARA")
        print()
        print(f"   El IPV actual ({ipv_actual:.2f}) está muy cerca del")
        print(f"   máximo histórico ({ipv_max:.2f}), a solo un {abs(distancia_al_maximo):.1f}%.")
        
    elif cambio_total > 50:
        print("🟡 LA VIVIENDA HA SUBIDO SIGNIFICATIVAMENTE")
        print()
        print(f"   Aunque no está en máximos, ha subido un {cambio_total:.1f}%")
        print(f"   desde {ipv_df.index[0].year}.")
        
    else:
        print("🟢 LA VIVIENDA NO ESTÁ EN MÁXIMOS HISTÓRICOS")
        print()
        print(f"   El IPV está {abs(distancia_al_maximo):.1f}% por debajo del máximo.")
    
    if ipc_df is not None and len(combined) >= 2:
        print()
        print("💡 En términos reales (ajustado por inflación):")
        if cambio_real > 20:
            print(f"   La vivienda ha subido un {cambio_real:.1f}% MÁS que la inflación.")
        elif cambio_real > 0:
            print(f"   La vivienda ha subido ligeramente más que la inflación ({cambio_real:+.1f}%).")
        elif cambio_real > -20:
            print(f"   La vivienda ha subido menos que la inflación ({cambio_real:+.1f}%).")
        else:
            print(f"   La vivienda es MÁS BARATA en términos reales ({cambio_real:+.1f}%).")
    
    print()
    print("=" * 80)
    print(f"Fuente: Instituto Nacional de Estadística (INE)")
    print(f"Última actualización: {fecha_actual.strftime('%B %Y')}")
    print("=" * 80)
    print()

if __name__ == "__main__":
    asyncio.run(main())
