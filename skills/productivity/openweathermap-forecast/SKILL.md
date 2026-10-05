---
name: openweathermap-forecast
description: "Consulta clima e previsão do tempo via OpenWeatherMap. Use quando o usuario pedir clima atual, previsão, temperatura ou alertas meteorológicos de uma cidade."
version: 0.1.0
author: Wittemberg, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [weather, clima, openweathermap, forecast]
---

# OpenWeatherMap Forecast Skill

Consulta condições meteorológicas atuais e previsões para cidades brasileiras e globais através da API OpenWeatherMap.

## When to Use
- O usuário solicitar a previsão do tempo, clima atual ou condições meteorológicas de qualquer cidade.
- Consultas de temperatura, sensação térmica, umidade, vento ou chuva.
- Não use para: consultas meteorológicas sem chave de API (para isso, use a API Open-Meteo ou wttr.in).

## Prerequisites
- Chave de API do OpenWeatherMap salva em `OPENWEATHER_API_KEY` no ambiente ou no `.env` do Hermes.
- Conectividade de saída HTTPS para `api.openweathermap.org`.
- **Nota de Ativação:** Novas chaves OpenWeatherMap podem levar de 10 minutos a 2 horas para propagação nos servidores da API (retornando erro 401 antes da ativação completa).

## How to Run
Executar o script auxiliar da skill:

`terminal(command="python scripts/weather.py 'Sao Paulo'")`

Ou para previsão de 5 dias:

`terminal(command="python scripts/weather.py 'Sao Paulo' --forecast")`

Ou diretamente via curl:

`terminal(command="curl -s 'https://api.openweathermap.org/data/2.5/weather?q=Sao%20Paulo,BR&units=metric&lang=pt_br&appid=$OPENWEATHER_API_KEY'")`

## Quick Reference
- Clima atual (CLI): `python scripts/weather.py "<Cidade>"`
- Previsão estendida (CLI): `python scripts/weather.py "<Cidade>" --forecast`
- Formato JSON via curl: `curl -s 'https://api.openweathermap.org/data/2.5/weather?q=<Cidade>&units=metric&lang=pt_br&appid='$OPENWEATHER_API_KEY`

## Procedure
1. Identificar a cidade ou localização solicitada pelo senhor.
2. Executar o script `scripts/weather.py` passando o nome da cidade.
3. Avaliar o resultado retornado:
   - Sucesso (200): Apresentar temperatura, umidade, vento e condições gerais formatadas.
   - Erro 401: Informar que a chave está em período de propagação pelo OpenWeatherMap.
   - Erro 404: Verificar a grafia da cidade e tentar com o código do país (ex: `Nome,BR`).

## Pitfalls
- **Erro 401 pós-criação:** Chaves recém-geradas falham com 401 durante a ativação inicial. Basta aguardar alguns minutos.
- **Unidades métricas:** Sempre passe `units=metric` nas requisições HTTP para receber valores em Celsius e km/h.
- **Codificação de nomes:** Nomes compostos devem ser passados entre aspas no script ou com `%20` no curl.

## Verification
Executar `python scripts/weather.py "Sao Paulo"` e confirmar recebimento do bloco formatado de clima.