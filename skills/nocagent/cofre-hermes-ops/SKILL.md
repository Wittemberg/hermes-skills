---
name: cofre-hermes-ops
description: Cofre de senhas multi-tenant do Hermes (equipamentos + pessoal). Use quando precisar da credencial de um equipamento para SSH/API, cadastrar equipamento no cofre, listar o que está cadastrado, consultar auditoria de acesso, ou operar o cofre pessoal. Gatilhos - cofre, senha do mikrotik, credencial do DVR, acessar o roteador, cadastrar equipamento, cofre-hermes.awecloudsolution.com.
metadata: { "hermes": { "emoji": "🔐", "requires": { "anyBins": ["cofre"] } } }
---

# Cofre Hermes — uso operacional

Cofre multi-tenant em `https://cofre-hermes.awecloudsolution.com`. Dois domínios:

- **Equipamentos** — cifrado no servidor. Você pode consumir estas credenciais sozinho para operar equipamentos.
- **Pessoal** — zero-knowledge, cifrado no navegador do usuário. **Você não tem acesso e não pode ter.** Se o usuário pedir uma senha pessoal, diga que ela só abre na interface web com a senha mestra dele.

## Regra central

**Nunca exiba uma senha de equipamento no chat sem o usuário pedir explicitamente.** Não é frescura: o chat vira histórico, log e às vezes tela compartilhada. Para operar, use os comandos que consomem a credencial sem imprimi-la.

```bash
# Rodar comando no equipamento — a senha vai do cofre direto ao ssh
cofre exec --tenant wit rb-matriz "/system resource print"

# Entregar a senha a um processo filho por variável de ambiente
cofre env --tenant wit rb-matriz --var SENHA -- ./script.sh
```

Se o usuário pedir a senha para digitar no Winbox ou no celular, aí sim mostre — ele pediu.

## Comandos

```bash
cofre list --tenant <slug>                      # lista equipamentos (nunca mostra senha)
cofre exec --tenant <slug> <nome> "<comando>"   # SSH usando a credencial do cofre
cofre env --tenant <slug> <nome> -- <programa>  # exporta a senha para um filho
cofre tenant-list                               # tenants existentes
cofre tenant-add "<Nome>" <slug>                # novo tenant
cofre user-add --tenant <slug> --email <email>  # novo usuário (senha pedida no prompt)
cofre init-db                                   # aplica/atualiza o schema
cofre gen-key                                   # gera master key nova (só provisionamento)
```

O equipamento pode ser referenciado por nome ou UUID.

## Tenant é obrigatório

Todo comando de dado exige `--tenant`. É intencional: o cofre isola clientes por chave criptográfica distinta, e não existe "listar tudo de todos". Se o usuário não disser qual, rode `cofre tenant-list` e pergunte.

## Cadastrar equipamento

Não faça pela CLI com a senha em argumento — ela ficaria no histórico do shell e em `/proc`. Peça para o usuário cadastrar pela interface web, ou use a API Python:

```bash
python3 -c "
from cofre.storage import Storage
from cofre.crypto import load_master_key
from cofre.app import _build_dsn
import getpass
s = Storage(_build_dsn(), load_master_key())
t = s.get_tenant_by_slug('wit')
s.create_equipment(t['id'], 'nome', 'MIKROTIK', '10.0.0.1', 22, 'admin', getpass.getpass())
s.close()
"
```

Tipos válidos: `MIKROTIK`, `DVR_INTELBRAS`, `PROXMOX`, `PFSENSE`, `OPNSENSE`, `SWITCH`, `SERVER`, `OTHER`.

## Toda leitura é auditada

`cofre exec` e `cofre env` gravam quem leu, quando, de onde e por quê em `audit_log`. Isso é feature, não efeito colateral: se uma credencial vazar, o log diz por onde saiu. Não tente contornar.

## Combina com as outras skills

- `mikrotik-ops` — pegue a credencial aqui, execute os comandos RouterOS de lá
- `intelbras-cftv-ops` — DVR cadastrado como `DVR_INTELBRAS`; use `cofre env` para não pôr a senha na URL do curl
- `proxmox-ops`, `pfsense-ops`, `opnsense-ops` — mesmo padrão

## Diagnóstico

| Sintoma | Causa provável |
|---|---|
| `COFRE_MASTER_KEY ausente` | Variável não exportada; dentro do container ela vem do secret |
| `Falha ao decifrar` | Master key trocada, ou linha movida entre tenants no banco |
| `equipamento não encontrado` | Tenant errado — confira com `cofre tenant-list` |
| Login recusa código correto | Relógio do celular dessincronizado |
| Conta travada | 5 falhas = 15 min. Ver `docs/OPERACAO.md` |
| Site responde `404 page not found` | Label `traefik.docker.network` junto de provider Swarm — ver abaixo |

Documentação completa: `/root/src/cofre-hermes/docs/` (INSTALACAO, SEGURANCA, TRD, OPERACAO).

## Deploy e infraestrutura

A stack é gerenciada pelo Portainer (stack id 5). Para aplicar mudança no
`deploy/stack.yml`, use a API do Portainer, não `docker stack deploy` — quem
subir pela CLI faz o Portainer perder o controle da stack de novo.

```bash
# Atualizar a stack preservando as variáveis já configuradas
PT_TOKEN=$(tr -d '\r\n' < /root/token.io)
curl -s -X PUT "https://<portainer>/api/stacks/5?endpointId=1" \
  -H "X-API-Key: $PT_TOKEN" -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,pathlib,urllib.request,os;print(json.dumps({"StackFileContent":pathlib.Path("deploy/stack.yml").read_text(),"Env":[],"Prune":True,"PullImage":True}))')"
```

### Armadilhas já pagas

1. **`traefik.docker.network` com `--providers.swarm=true`** faz o Traefik
   descartar o router **em silêncio**: serviço `1/1`, app respondendo 200 em
   `127.0.0.1:8787`, site devolvendo `404 page not found`, **nada no log do
   Traefik**. Use só `traefik.swarm.network`. Diagnóstico rápido:
   `curl -H "Host: <dominio>" http://127.0.0.1/` devolvendo 301 prova que o
   Traefik conhece o host e o problema está no roteamento HTTPS.
2. **Stack criada por `docker stack deploy` fica "limitada" no Portainer.**
   Só é editável se o próprio Portainer a criou. Migrar exige `docker stack rm`
   + `POST /api/stacks/create/swarm/string` (HTTP 409 se ainda existir no Swarm).
   Secrets e banco não são tocados.
3. **`${VAR}` não expande em CHAVES de label**, só em valores. Validar sempre
   com `docker stack config -c deploy/stack.yml`, que mostra o texto expandido.
4. **Container sai com exit 2 no boot**: falta a master key. O app recusa subir
   sem chave em vez de subir inseguro — comportamento correto, não bug.
5. **Imagem privada no GHCR**: exige `docker login ghcr.io` no nó e
   `--with-registry-auth` no deploy, senão a task não baixa a imagem.

## Bugs de costura entre camadas (classe recorrente)

Três bugs seguidos vieram do mesmo lugar: template e rota construídos em
paralelo, com nomes de campo divergentes, nunca exercitados juntos.

- `name="senha"` no HTML contra `request.form["password"]` na rota: a senha
  chegava vazia e a senha correta era rejeitada com "Credenciais inválidas".
- Campo TOTP `required` no login travava o primeiro acesso no navegador, antes
  do POST, e o usuário nunca chegava à tela de cadastro do segundo fator.
- O salt do cofre pessoal só existia dentro dos itens: criar o cofre exigia um
  item, criar o item exigia o cofre. Impasse. Resolvido com `users.vault_salt`
  + `POST /pessoal/criar-cofre`.

Defesa que ficou no repo, e que deve ser mantida:

- `tests/test_contratos_ui.py` — lê os `name=` dos templates e os
  `request.form[...]` do `app.py` e falha se divergirem.
- `tests/test_jornada.py` — percorre o caminho real do usuário **extraindo os
  campos do HTML servido**, em vez de montar o POST com os nomes que a rota
  espera. Só ele pegaria o impasse do salt.

Ao mexer em formulário ou rota, rode os dois. Teste que monta o POST à mão
testa a rota contra ela mesma e não prova nada sobre a tela.
