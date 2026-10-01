---
name: intelbras-cftv-ops
description: Especialista em CFTV Intelbras e Dahua (DVR, NVR e câmera IP). Use quando o pedido envolver DVR, NVR, câmera, CFTV, snapshot, gravação, .dav, MHDX, NVD, VIP, iSIC, SIM Next, canal offline, video loss, HD do DVR, ou acesso via CGI/HTTP e RTSP em gravador Intelbras/Dahua. Diagnostica, extrai foto/vídeo e audita saúde do equipamento.
metadata: { "hermes": { "emoji": "📹", "requires": { "anyBins": ["curl", "ffmpeg"] } } }
---

# Intelbras / Dahua — Operações de CFTV via CGI

Especialista nas linhas MHDX, NVD, MHDV e VIP da Intelbras (OEM Dahua) e nos equipamentos Dahua originais. O diagnóstico HTTP nesses aparelhos usa rotas CGI (`/cgi-bin/...`), normalmente na porta 80 ou 8080, com autenticação Digest (às vezes Basic).

Detalhes finos da API, pegadinhas de firmware e rotas de fallback: `references/cgi-api-dahua.md`. Leia antes de montar qualquer extração de mídia ou telemetria.

## Regras de operação

- Sempre `--anyauth` no curl: a maioria dos firmwares modernos desativou Basic em texto claro e só negocia Digest.
- Timeout elástico: DVR remoto via DDNS tem RTT alto. Nunca abaixo de 5s — use `-m 8 --connect-timeout 4`.
- Comece por leitura. Nada de reboot, formatação de HD, troca de senha ou alteração de gravação sem confirmação explícita do operador.
- Credencial nunca em texto no histórico: prefira variável de ambiente (`$DVR_USER`, `$DVR_PASS`) ou `--netrc`.
- Se um endpoint responder `Error\r\nNot Implemented!`, o firmware capou a rota — não insista, vá para o fallback da referência.

## Diagnóstico rápido

Nome/modelo do equipamento:
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 8 --connect-timeout 4 "http://<IP>/cgi-bin/magicBox.cgi?action=getMachineName"
```

Nomes dos canais (descobre qual câmera é qual número):
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 8 "http://<IP>/cgi-bin/devVideoInput.cgi?action=getChannelTitle"
```

Saúde do HD / armazenamento (procure `State=Normal`):
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 8 "http://<IP>/cgi-bin/devStorage.cgi?action=factory.instance"
```

Uptime e info de sistema:
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 8 "http://<IP>/cgi-bin/global.cgi?action=getSystemInfo"
```

Câmeras fisicamente ativas (heurística de sinal, ver §4.4 da referência):
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 8 "http://<IP>/cgi-bin/configManager.cgi?action=getConfig&name=VideoIn" | grep AutoSignalType
```

## Snapshot ao vivo

Snapshot é SEMPRE do instante atual — não existe snapshot do passado nesta API.
```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 10 "http://<IP>/cgi-bin/snapshot.cgi?channel=1" -o /tmp/cam01.jpg
file /tmp/cam01.jpg   # confirma que veio JPEG e não uma página de erro
```
Canais são 1-indexed. Se o arquivo vier com poucos KB e `file` disser HTML/texto, é erro mascarado — leia o conteúdo.

## Gravação (vídeo do passado)

```bash
curl -sg --anyauth -u "$DVR_USER:$DVR_PASS" -m 300 \
  "http://<IP>/cgi-bin/loadfile.cgi?action=startLoad&channel=1&startTime=2026-09-11%2008:25:00&endTime=2026-09-11%2008:30:00" \
  -o /tmp/cam01.dav
ls -lh /tmp/cam01.dav   # 11 KB em 5 min de vídeo = erro mascarado, não vídeo
ffmpeg -i /tmp/cam01.dav -c copy /tmp/cam01.mp4   # converte o container proprietário para MP4
```
Na data, troque APENAS o espaço por `%20` — nunca `%3A` nos dois-pontos, o parser do firmware não decodifica. Não acrescente `&subtype=0`: derruba a chamada com HTTP 400. Um 400 quase sempre significa "não há gravação nesse intervalo", não erro de sintaxe.

Frame de um momento passado: baixe o minuto em `.dav` e extraia com `ffmpeg -ss 00:00:12 -i arquivo.dav -frames:v 1 foto.jpg`.

## RTSP (stream ao vivo)

```
rtsp://usuario:senha@<IP>:554/cam/realmonitor?channel=1&subtype=0
```
`subtype=0` é o stream principal, `subtype=1` o secundário (mais leve, bom para link ruim).

## Troubleshooting comum

- Câmera IP "offline" no NVR: senha ONVIF errada, IP em conflito, ou codec não suportado (H.265 em NVR antigo).
- Sem gravação: HD em `Unformatted` ou `Error` — confira o endpoint de storage antes de culpar a câmera.
- Acesso externo: Intelbras SIM Next e iSIC usam a porta de serviço 37777/TCP, não a HTTP. O port forward precisa contemplar a 37777.
- Canal com imagem preta mas online: quase sempre `AutoSignalType` divergente (CVI/TVI/AHD) ou cabo/fonte da câmera analógica.
