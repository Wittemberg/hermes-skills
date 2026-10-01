---
name: manutencao-disco-alertas
description: "Limpeza de disco por cron e alertas WhatsApp no Hermes."
version: 1.0.0
---

# Manutencao de disco e alertas por cron

Script pronto neste servidor: `/root/.hermes/scripts/limpeza-disco.sh`
Job: "Limpeza e checagem de disco", diario 04:00, `deliver=whatsapp:<numero>`.
Log: `/var/log/limpeza-disco.log` (logrotate em `/etc/logrotate.d/limpeza-disco`).

## Padrao watchdog: silencio quando esta tudo bem

Com `no_agent=true` o stdout do script e entregue literalmente e **stdout
vazio nao envia mensagem nenhuma**. Use isso: o script imprime SO quando ha
problema. Mensagem diaria de "esta tudo ok" vira ruido e faz o alerta real
passar despercebido. Todo o historico vai para arquivo de log, nunca stdout.
Exit code diferente de zero ja gera alerta de erro automatico.

O alerta deve ser acionavel: alem do percentual, inclua os maiores
diretorios (`du -xhd1 / | sort -rh | head -5`) e o `docker system df`.
So dizer "disco cheio" obriga a abrir SSH para descobrir o resto.

## Ordem correta: limpar primeiro, medir depois

A medicao precisa refletir o disco ja limpo, senao o alerta dispara por lixo
que seria removido em seguida.

Use `set -uo pipefail` **sem `-e`**: falha numa etapa de limpeza nao pode
abortar a checagem de disco. E justamente quando a limpeza falha que o alerta
mais importa.

Trave contra execucao sobreposta com `flock -n`: um prune travado nao pode
acumular uma segunda instancia em cima.

## docker system prune: o que e seguro

- `docker system prune -a -f` remove imagens sem container, redes orfas e
  cache de build. **Nao toca volumes nomeados** (Postgres, Portainer, etc.).
- **Nunca** acrescente `--volumes` num script automatico: ai sim apaga dados.
- Efeito colateral real: imagens antigas somem, entao rollback local para a
  versao anterior passa a exigir download do registry de novo.
- Antes de rodar a primeira vez, mostre ao usuario o que sera removido:
  `docker image ls` + `docker system df` e confirme.

## Entrega de cron falha em silencio: SEMPRE teste

Um alerta nunca testado e um alerta que voce descobre quebrado no dia da
emergencia. O retorno de `action='create'` diz "success" mesmo quando a
entrega vai falhar. Dispare `action='run'` e confira `last_status` e
`last_delivery_error` em `action='list'`.

Para testar o caminho de alerta sem esperar o disco encher, rode o job real
com o limite temporariamente alto (ex.: 95%), confirme a entrega, e restaure.
Valide a restauracao com `diff` contra uma copia do original.

### Erro 1: `no delivery target resolved for deliver=whatsapp`

`deliver='whatsapp'` sozinho nao resolve destinatario. Use
`deliver='whatsapp:<numero>'`. Descubra o numero no log do gateway:

```bash
grep -oE 'session=agent:main:whatsapp:dm:[0-9]+' ~/.hermes/logs/gateway.log | sort -u
```

### Erro 2: `Cannot connect to host localhost:3000 [... ('::1', 3000)]`

A ponte WhatsApp escuta em **IPv4** (`127.0.0.1:3000`), mas o caminho de
entrega usa o nome `localhost`. Se o `/etc/hosts` nao tiver a linha
`127.0.0.1 localhost`, o nome resolve so para `::1` e a conexao e recusada.

```bash
getent ahosts localhost   # precisa listar 127.0.0.1, nao so ::1
```

Corrija no `/etc/hosts` (aditivo, conserta todo software do host que usa
`localhost`), **nao** editando `/usr/local/lib/hermes-agent/` — patch em
codigo instalado se perde no proximo upgrade. Faca backup do hosts antes.

Este servidor tinha `127.0.0.1 servidor` sem `localhost`: alguem substituiu
a linha padrao em vez de acrescentar um nome.

## Detalhes que ja custaram retrabalho

- `docker system df` em tabela tem colunas com espaco no nome ("Local
  Volumes", "Build Cache") e um "(25%)" solto que quebra parse posicional em
  awk. Use `--format '{{.Type}}: {{.Size}} ({{.Reclaimable}})'`.
- `apt-get autoremove` precisa de `DEBIAN_FRONTEND=noninteractive`, senao um
  prompt trava o cron.
- `/var/log` pertence ao grupo `syslog`: o logrotate recusa rotacionar sem a
  diretiva `su root syslog` no arquivo de config. Valide com
  `logrotate --debug /etc/logrotate.d/<arquivo>`.
- Skills built-in ficam em `/usr/local/lib/hermes-agent/skills/` e sao
  sobrescritas no upgrade. Conhecimento local vai em `~/.hermes/skills/`.
- A acao de remover job de cron e `action='remove'`, nao `'delete'`.
