---
name: aitek-cftv-ops
description: Especialista em CFTV AiTek e Xiongmai/JFTech (DVR, NVR e câmera IP base Sofia/NetIP/XMeye). Use quando o pedido envolver NVR AiTek, SIGMA-N210, placa Xiongmai NBD88X16S, porta 34567 (NetIP/Sofia), RTSP na porta 554, cadastro de canal de vídeo, auditoria de HD ou extração de gravação no NVR.
metadata: { "hermes": { "emoji": "📹", "requires": { "anyBins": ["python3", "ffmpeg", "curl"] } } }
---

# AiTek / Xiongmai — Operações de CFTV via NetIP (Sofia) e RTSP

Especialista em gravadores de vídeo AiTek (linha SIGMA) e placas OEM Xiongmai (XM / Sofia / JFTech / XMeye).
Diferente dos equipamentos Intelbras/Dahua que usam CGI HTTP, a plataforma Xiongmai utiliza o protocolo binário **NetIP (Sofia)** na porta de mídia **34567**, além do streaming padrão **RTSP na porta 554** e interface web na porta **80**.

---

## 1. Regras de Operação e Segurança

- **Segurança de Rede:** O NVR deve ser acessado exclusivamente via rede privada (VPN WireGuard/LAN) pelo IP autorizado (ex.: `192.168.15.110`). Nunca expor as portas 80, 554 ou 34567 publicamente na internet.
- **Credenciais Seguras:** Nunca gravar credenciais em texto claro em relatórios ou logs públicos. Prefira ler das variáveis de ambiente:
  ```bash
  export NVR_HOST="192.168.15.110"
  export NVR_USER="hjsb"
  export NVR_PASS="sua_senha"
  ```
- **Sem Modificações Destrutivas:** Operações de leitura (status, canais, disco, relógio) são prioritárias. Nunca alterar configurações de rede ou formatar HD sem confirmação explícita do operador.

---

## 2. CLI Rápida (`scripts/aitek_dvr.py`)

A skill inclui um utilitário Python standalone para operar o protocolo Sofia (porta 34567):

### Informações de Hardware e Firmware
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py info \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS"
```
*Retorno esperado:* Hardware (`NBD88X16S-KL-V3`), versão do firmware (`V4.03.R11...`), data de build e serial number.

### Saúde e Espaço do Disco Rígido (HD)
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py storage \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS"
```
*Retorno esperado:* Lista de discos físicos, partições, capacidade total, espaço livre e porcentagem de uso.

### Status dos Canais Digitais
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py channels \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS"
```
*Retorno esperado:* Lista dos canais D01 a D10 com resolução máxima suportada (4K), status de conexão (`Offline`, `NoConfig` ou `Connected`) e IP/porta do alvo.

### Relógio do NVR
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py time \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS"
```
*Retorno esperado:* Timestamp atual do relógio interno do gravador (verificar drift temporal em relação ao servidor).

---

## 3. Extração de Vídeo e Snapshot (RTSP — Porta 554)

Para capturar um frame ou vídeo de um canal específico conectado:

### Capturar Snapshot de um Canal Ativo
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py snapshot \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS" --channel 1 -o /tmp/canal01.jpg
```

### Extração direta via FFmpeg / RTSP
```bash
ffmpeg -y -hide_banner -loglevel error -rtsp_transport tcp \
  -i "rtsp://$NVR_USER:$NVR_PASS@$NVR_HOST:554/cam/realmonitor?channel=1&subtype=0" \
  -vframes 1 -q:v 2 /tmp/snapshot.jpg
```
*Formato de fallback comum em firmwares XM:*
`rtsp://$NVR_USER:$NVR_PASS@$NVR_HOST:554/user=${NVR_USER}_password=${NVR_PASS}_channel=1_stream=0.sdp`

---

## 4. Busca de Gravações Históricas (Playback)

Para consultar o calendário de gravações do NVR por mês e ano:
```bash
python3 /root/.hermes/skills/nocagent/aitek-cftv-ops/scripts/aitek_dvr.py search \
  --host "$NVR_HOST" -u "$NVR_USER" -p "$NVR_PASS" --channel 0 --month 9 --year 2026
```
*(Código de retorno `Ret=119` significa ausência de arquivos gravados no período solicitado).*
