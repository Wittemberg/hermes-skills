#!/usr/bin/env python3
import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

WMO_CODES = {
    0: 'Céu limpo',
    1: 'Predominantemente limpo',
    2: 'Parcialmente nublado',
    3: 'Encoberto',
    45: 'Nevoeiro',
    48: 'Nevoeiro com gelo',
    51: 'Chuvisco fraco',
    53: 'Chuvisco moderado',
    55: 'Chuvisco denso',
    61: 'Chuva fraca',
    63: 'Chuva moderada',
    65: 'Chuva forte',
    71: 'Queda de neve fraca',
    73: 'Queda de neve moderada',
    75: 'Queda de neve forte',
    80: 'Pancadas de chuva fracas',
    81: 'Pancadas de chuva moderadas',
    82: 'Pancadas de chuva violentas',
    95: 'Trovoada',
    96: 'Trovoada com granizo leve',
    99: 'Trovoada com granizo forte'
}

def get_api_key():
    key = os.environ.get('OPENWEATHER_API_KEY')
    if key:
        return key.strip()
    
    candidates = [
        os.path.expanduser('~/.hermes/.env'),
        os.path.expandvars(r'%LOCALAPPDATA%\hermes\.env'),
        os.path.expanduser('~/.bashrc'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('OPENWEATHER_API_KEY='):
                            return line.split('=', 1)[1].strip().strip('"').strip("'")
                        if line.startswith('export OPENWEATHER_API_KEY='):
                            return line.split('=', 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    return None

def fetch_open_meteo(city, forecast_mode=False):
    try:
        geo_url = f'https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=pt&format=json'
        req_geo = urllib.request.Request(geo_url, headers={'User-Agent': 'Hermes-Weather-Client/1.0'})
        with urllib.request.urlopen(req_geo, timeout=10) as r:
            geo_data = json.loads(r.read().decode('utf-8'))
            
        results = geo_data.get('results')
        if not results:
            print(f'Cidade "{city}" não encontrada via Open-Meteo.', file=sys.stderr)
            return False
            
        res = results[0]
        lat = res['latitude']
        lon = res['longitude']
        name = res.get('name', city)
        admin1 = res.get('admin1', '')
        country = res.get('country', '')
        tz = res.get('timezone', 'auto')
        
        weather_url = (
            f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}'
            f'&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,surface_pressure'
            f'&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum'
            f'&timezone={urllib.parse.quote(tz)}'
        )
        
        req_w = urllib.request.Request(weather_url, headers={'User-Agent': 'Hermes-Weather-Client/1.0'})
        with urllib.request.urlopen(req_w, timeout=10) as r:
            w_data = json.loads(r.read().decode('utf-8'))
            
        curr = w_data.get('current', {})
        code = curr.get('weather_code', 0)
        desc = WMO_CODES.get(code, f'Código WMO {code}')
        temp = curr.get('temperature_2m', 0)
        feels = curr.get('apparent_temperature', 0)
        hum = curr.get('relative_humidity_2m', 0)
        wind = curr.get('wind_speed_10m', 0)
        press = curr.get('surface_pressure', 0)
        precip = curr.get('precipitation', 0)
        
        daily = w_data.get('daily', {})
        max_today = daily.get('temperature_2m_max', [0])[0] if daily.get('temperature_2m_max') else 0
        min_today = daily.get('temperature_2m_min', [0])[0] if daily.get('temperature_2m_min') else 0
        
        loc_str = f'{name} ({admin1}), {country}' if admin1 else f'{name}, {country}'
        print('=' * 60)
        print(f' Previsão do Tempo: {loc_str} [Open-Meteo]')
        print('=' * 60)
        print(f' Condição:       {desc}')
        print(f' Temperatura:    {temp:.1f} °C (Sensação: {feels:.1f} °C)')
        print(f' Min / Max hoje: {min_today:.1f} °C / {max_today:.1f} °C')
        print(f' Umidade:        {hum}%')
        print(f' Vento:          {wind:.1f} km/h')
        print(f' Precipitação:   {precip} mm')
        print(f' Pressão:        {press:.0f} hPa')
        
        if forecast_mode and daily:
            print('-' * 60)
            print(' Previsão Diária (Próximos dias):')
            times = daily.get('time', [])
            maxs = daily.get('temperature_2m_max', [])
            mins = daily.get('temperature_2m_min', [])
            codes = daily.get('weather_code', [])
            sums = daily.get('precipitation_sum', [])
            for i in range(min(5, len(times))):
                d_desc = WMO_CODES.get(codes[i], 'Variável')
                print(f' • {times[i]}: {mins[i]:.1f}°C a {maxs[i]:.1f}°C | {d_desc:<22} | Chuva: {sums[i]} mm')
        
        print('=' * 60)
        return True
    except Exception as e:
        print(f'Erro na consulta Open-Meteo: {e}', file=sys.stderr)
        return False

def fetch_current(city, api_key):
    base_url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric',
        'lang': 'pt_br'
    }
    url = f'{base_url}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Hermes-Weather-Client/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            name = data.get('name', city)
            country = data.get('sys', {}).get('country', '')
            weather_desc = data.get('weather', [{}])[0].get('description', 'N/D').capitalize()
            main = data.get('main', {})
            temp = main.get('temp', 0)
            feels_like = main.get('feels_like', 0)
            temp_min = main.get('temp_min', 0)
            temp_max = main.get('temp_max', 0)
            humidity = main.get('humidity', 0)
            pressure = main.get('pressure', 0)
            wind_speed = data.get('wind', {}).get('speed', 0) * 3.6
            
            print('=' * 60)
            print(f' Previsão Atual: {name} - {country} [OpenWeatherMap]')
            print('=' * 60)
            print(f' Condição:       {weather_desc}')
            print(f' Temperatura:    {temp:.1f} °C (Sensação: {feels_like:.1f} °C)')
            print(f' Min / Max:      {temp_min:.1f} °C / {temp_max:.1f} °C')
            print(f' Umidade:        {humidity}%')
            print(f' Vento:          {wind_speed:.1f} km/h')
            print(f' Pressão:        {pressure} hPa')
            print('=' * 60)
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print('[Aviso OpenWeatherMap] Chave em ativação/propagação (HTTP 401). Consultando Open-Meteo como alternativa instantânea...', file=sys.stderr)
            clean_city = city.split(',')[0]
            return fetch_open_meteo(clean_city, forecast_mode=False)
        elif e.code == 404:
            print(f'Erro 404: Cidade "{city}" não encontrada no OpenWeatherMap.', file=sys.stderr)
            return False
        else:
            print(f'Erro HTTP {e.code}: {e.reason}', file=sys.stderr)
            return False
    except Exception as e:
        print(f'Erro na consulta: {e}', file=sys.stderr)
        return False

def fetch_forecast(city, api_key):
    base_url = 'https://api.openweathermap.org/data/2.5/forecast'
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric',
        'lang': 'pt_br'
    }
    url = f'{base_url}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Hermes-Weather-Client/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            city_name = data.get('city', {}).get('name', city)
            country = data.get('city', {}).get('country', '')
            entries = data.get('list', [])
            
            print('=' * 65)
            print(f' Previsão Estendida (5 dias): {city_name} - {country} [OpenWeatherMap]')
            print('=' * 65)
            print(f'{"Data/Hora":<18} | {"Clima":<20} | {"Temp":<8} | {"Chuva/Umid":<10}')
            print('-' * 65)
            
            for item in entries[:12]:
                dt_txt = item.get('dt_txt', '')
                desc = item.get('weather', [{}])[0].get('description', '').capitalize()
                temp = item.get('main', {}).get('temp', 0)
                humidity = item.get('main', {}).get('humidity', 0)
                print(f'{dt_txt:<18} | {desc[:20]:<20} | {temp:4.1f} °C  | {humidity}% umid')
            print('=' * 65)
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print('[Aviso OpenWeatherMap] Chave em ativação/propagação (HTTP 401). Consultando Open-Meteo como alternativa instantânea...', file=sys.stderr)
            clean_city = city.split(',')[0]
            return fetch_open_meteo(clean_city, forecast_mode=True)
        else:
            print(f'Erro HTTP {e.code}: {e.reason}', file=sys.stderr)
            return False
    except Exception as e:
        print(f'Erro na consulta: {e}', file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Consulta clima via OpenWeatherMap ou Open-Meteo')
    parser.add_argument('city', nargs='?', default='Sao Paulo,BR', help='Nome da cidade (ex: "Sao Paulo,BR" ou "Curitiba")')
    parser.add_argument('--forecast', action='store_true', help='Exibir previsão estendida de 5 dias')
    parser.add_argument('--key', help='Chave da API OpenWeatherMap')
    parser.add_argument('--open-meteo', action='store_true', help='Forçar consulta direta via Open-Meteo')
    
    args = parser.parse_args()
    
    if args.open_meteo:
        clean_city = args.city.split(',')[0]
        success = fetch_open_meteo(clean_city, forecast_mode=args.forecast)
        if not success:
            sys.exit(1)
        return
        
    api_key = args.key or get_api_key()
    if not api_key:
        print('Aviso: Chave OpenWeatherMap não encontrada. Utilizando Open-Meteo...', file=sys.stderr)
        clean_city = args.city.split(',')[0]
        success = fetch_open_meteo(clean_city, forecast_mode=args.forecast)
        if not success:
            sys.exit(1)
        return
        
    if args.forecast:
        success = fetch_forecast(args.city, api_key)
    else:
        success = fetch_current(args.city, api_key)
        
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
