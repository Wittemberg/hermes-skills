# Integração CCTV - Dahua & Intelbras

Este documento registra as idiossincrasias e "pegadinhas" da API HTTP CGI utilizada pelos equipamentos de CFTV da Dahua e Intelbras. Utilize estas regras ao implementar, debugar ou criar ferramentas de extração de vídeo.

## 1. Snapshots (Fotos Ao Vivo)
- **URL**: `/cgi-bin/snapshot.cgi?channel=1`
- **Indexação**: Os canais geralmente são 1-indexed (Câmera 1 = `channel=1`).
- **Limitação Crítica**: A API de snapshot da Dahua **NÃO SUPORTA** extração de imagens de datas passadas. Ela *apenas* captura uma foto do stream ao vivo no exato milissegundo em que a rota é chamada. Se o usuário pedir "uma foto de ontem às 14h", a requisição retornará a foto de **agora**. Para extrair imagens do passado, é obrigatório baixar o vídeo daquele minuto e extrair um frame via `ffmpeg`.

## 2. Download de Gravações (Vídeo)
- **URL Padrão**: `/cgi-bin/loadfile.cgi?action=startLoad&channel=1&startTime=YYYY-MM-DD%20HH:MM:SS&endTime=YYYY-MM-DD%20HH:MM:SS`
- **Formato do Arquivo**: O DVR não envia o vídeo em `.mp4`. O payload bruto que desce no HTTP 200 OK é um container proprietário **`.dav`**. Salvar esse arquivo como `.mp4` causará tela preta em players HTML5 (navegadores). É necessário converter com `ffmpeg` ou entregar o arquivo com a extensão original `.dav` para o usuário assistir no VLC/SmartPlayer.

### 2.1 Erros de Parâmetro (HTTP 400 Bad Request)
A API `loadfile.cgi` é extremamente frágil e retorna `400 Bad Request` para qualquer desvio milimétrico. Causas mapeadas:

1. **Inexistência de Gravação**: O erro 400 é o código padrão da Dahua para **"Arquivo não encontrado no HD"**. Se não houver gravação (ex: gravação por movimento que não ativou) ou se o LLM enviar o ano errado (ex: 2023 em vez de 2026), o DVR não retornará 404, retornará 400.
2. **URL Encode Agressivo**: O parser em `C` do firmware dos DVRs não sabe decodificar `%3A` de volta para dois-pontos (`:`). A data **NÃO PODE** ser submetida a `encodeURIComponent` completo. Deve-se substituir **apenas** o espaço por `%20` (Ex: `2026-09-11%2008:25:00`).
3. **Parâmetros Inexistentes**: Adicionar parâmetros que funcionam no RTSP ou no SDK, como `&subtype=0` na `loadfile.cgi`, faz a API abortar com HTTP 400 imediatamente.

### 2.2 Falso Positivo (HTTP 200 OK Vazio)
Em algumas versões de firmware ou em rotas inválidas, o DVR retorna código HTTP `200 OK` mas o payload é apenas um documento HTML minúsculo ou uma string `Error\r\n`. 
**Solução**: Toda ferramenta de download via `curl` deve checar o tamanho do arquivo no disco após o download. Se um vídeo de 5 minutos pesar apenas 11 KB, trata-se de um erro mascarado. Deve-se ler os primeiros bytes do arquivo para expor o erro real ao usuário.

## 3. Autenticação
O `curl` deve ser executado com a flag `--anyauth` (geralmente negociando `Digest`), pois a maioria dos equipamentos modernos desabilitou o Basic Auth em texto claro na porta HTTP.

## 4. Telemetria e Monitoramento de Saúde (Health Check)
A extração de telemetria em DVRs Dahua e Intelbras via CGI HTTP é inconsistente e altamente dependente da versão do firmware.

### 4.1 Timeouts e Latência
DVRs conectados remotamente (DDNS/IP) costumam apresentar alta latência (RTT > 1.5s) e perdas.
**Solução**: Ao utilizar `curl` para extrair dados CGI, configure um timeout elástico. Nunca use timeouts menores que 5 segundos (Exemplo ideal: `curl -m 8 --connect-timeout 4`).

### 4.2 Restrições em Endpoints Padrão (Série MHDX Intelbras)
Firmwares modernos (como a série MHDX 1000/3000 da Intelbras) "caparam" rotas HTTP que entregavam métricas. Se uma rota retornar `Error\r\nNot Implemented!` ou `Error\r\nBad Request!`, o equipamento bloqueou a consulta via HTTP e as métricas (como HD e Uptime) não estarão acessíveis.

### 4.3 Fallbacks (Rotas Secundárias em Cascata)
Para extrair informações, implemente as tentativas abaixo em ordem:

- **Uptime**:
  1. `/cgi-bin/global.cgi?action=getSystemInfo` (Padrão Dahua)
  2. `/cgi-bin/magicBox.cgi?action=getSystemInfo`
  3. `/cgi-bin/devSystem.cgi?action=getSystemInfo`
- **Armazenamento (Storage)**:
  1. `/cgi-bin/devStorage.cgi?action=factory.instance` (Procura por `State=Normal`)
  2. `/cgi-bin/storage.cgi?action=getDeviceAllInfo`
- **Canais (Total)**:
  - `/cgi-bin/configManager.cgi?action=getConfig&name=VideoInOptions` (Conta chaves lógicas).

### 4.4 Heurística Definitiva de Câmeras Ativas (Video Loss)
Na Dahua, a rota `/cgi-bin/videoStat.cgi?action=getLoss` retorna perfeitamente perdas de vídeo (`loss[0]=1`). 
Em DVRs Intelbras MHDX, essa rota costuma retornar `Not Implemented!`. 
Para contar **Câmeras Ativas**, utilize a heurística da rota **VideoIn**:
1. Execute `/cgi-bin/configManager.cgi?action=getConfig&name=VideoIn`
2. Esta rota exibe o tipo de sinal físico detectado no momento da chamada (ex: `table.VideoIn[N].AutoSignalType=CVI`).
3. **Regra**: Varra o output com expressões regulares. Se a chave `AutoSignalType` for omitida, vier vazia ou possuir valores como `UNKNOWN` ou `NONE`, a câmera física está **desconectada** daquele canal. O total de chaves com sinais válidos é o total de câmeras ativas reais.
