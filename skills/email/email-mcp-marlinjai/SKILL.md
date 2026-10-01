---
name: email-mcp-marlinjai
description: "Setup e uso do email-mcp: Gmail e Outlook via OAuth."
version: 0.1.0
author: Wittemberg, Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [email, mcp, gmail, outlook, oauth]
    category: email
---

# email-mcp (@marlinjai/email-mcp)

Servidor MCP multi-provedor para Gmail, Outlook/Hotmail, iCloud e IMAP genérico. Usa Gmail API e Microsoft Graph quando disponíveis, com IMAP/SMTP como fallback. 33 ferramentas `email_*`.

## Quando usar

- Conectar contas de e-mail ao Hermes via MCP.
- Diagnosticar setup OAuth, contas que somem ou ferramentas que não aparecem.
- Não usar para: envio pontual por SMTP com senha de app (a skill `himalaya` resolve com menos superfície).

## Por que Graph importa no Hotmail

A Microsoft está removendo autenticação básica do Outlook.com, e contas pessoais frequentemente já têm **SMTP AUTH desabilitado sem opção de reativar**. Um MCP que só fale IMAP/SMTP com senha funciona no Gmail e falha no Hotmail. Este usa Graph para Outlook, contornando o bloqueio. Não ofereça senha de app do Outlook como solução durável.

## Instalação

```bash
npm install -g @marlinjai/email-mcp
```

Registre no Hermes sem editar YAML à mão:

```bash
hermes config set mcp_servers.email.command email-mcp
hermes config set mcp_servers.email.timeout 120
```

O gateway reconecta servidores MCP por conta própria, sem reiniciar o Hermes: confira com `hermes gateway status`, que lista o processo do servidor no cgroup do serviço. Antes de propor reinicialização, tente chamar uma ferramenta — `email_list_accounts` responder já prova que está ativo. Uma sessão interativa antiga, porém, mantém o toolset do momento em que iniciou.

## Setup de conta: exige navegador do usuário

```bash
npx -y -p @marlinjai/email-mcp@latest email-mcp-setup
```

O flag `-p` é obrigatório. Sem ele, o npx roda o bin homônimo do pacote (o servidor MCP) e o processo fica esperando protocolo no stdin — parece travamento.

O assistente é **interativo e exige TTY**; rodar com stdin redirecionado imprime o menu e encerra. O OAuth abre um servidor de callback em `localhost` com porta efêmera e tenta abrir o navegador via `xdg-open`, com timeout de 2 minutos.

**Em servidor headless isso não fecha sozinho.** O redirect aponta para `localhost` da máquina onde o assistente roda, então o navegador precisa alcançar aquele loopback. Caminhos válidos: executar o assistente na máquina do usuário e copiar o arquivo de credenciais, ou túnel SSH com encaminhamento da porta efêmera escolhida. Não prometa concluir OAuth sozinho num servidor remoto.

## Rodando o assistente por SSH com encaminhamento de porta

Funciona quando o servidor é headless mas o usuário tem navegador: o assistente roda no servidor dentro de `tmux`, e a porta efêmera do callback é encaminhada para a máquina do usuário.

1. `tmux new-session -d -s setup -x 200 -y 50 'email-mcp-setup'` — o assistente exige TTY; com stdin redirecionado ele imprime o menu e encerra.
2. Dirija com `tmux send-keys -t setup '<opcao>' Enter` e leia com `tmux capture-pane -t setup -p -J`. **Use sempre `-J`**: sem ele a URL de autorização vem quebrada em várias linhas e fica inutilizável.
3. Extraia a porta do próprio `redirect_uri` (`localhost%3A<porta>`) e confirme com `ss -tlnp | grep <porta>` antes de pedir o túnel.
4. O usuário abre `ssh -N -L <porta>:127.0.0.1:<porta> ...` com a **mesma porta nos dois lados** — o provedor valida o redirect exato — e visita a URL.
5. Após o código chegar, o assistente pede o nome da conta: envie `tmux send-keys -t setup '' Enter` para aceitar o padrão. Ele **não** prossegue sozinho.

No Windows, `ControlMaster` não existe no OpenSSH nativo: não ofereça `ssh -O forward`. Monte o comando completo antes, para caber no timeout de 2 minutos do callback.

### Ler os sinais corretamente

- `channel N: open failed: Connection refused` no cliente SSH **depois** da autorização é esperado: o servidor de callback fecha assim que recebe o código, e o navegador tenta buscar favicon ou recarregar. Não é falha.
- A mesma mensagem **antes** de autorizar significa que o processo morreu: confirme com `ss -tlnp | grep <porta>` e reinicie.
- Um `tmux kill-server` ou a queda da sessão mata o assistente e a porta junto. Verifique `tmux ls` antes de mandar o usuário abrir o túnel.
- Página de erro renderizada pelo próprio callback prova que o túnel funcionou; a causa está nos parâmetros `error` da URL, não na rede.
- Contas já salvas sobrevivem à queda do assistente: cheque `email_list_accounts` antes de refazer tudo.
- Em `email_list_accounts`, `connected:false` é apenas sessão ociosa. Só `email_test_account` diz se a conta autentica.

## Credenciais e privacidade

- Ficam em `~/.email-mcp`, cifradas em AES-256-GCM com chave derivada da máquina (`/etc/machine-id` + usuário). **Não são portáteis entre máquinas** a menos que `EMAIL_MCP_KEY` seja definida com o mesmo valor nos dois lados.
- Defina `EMAIL_MCP_KEY` **antes** do primeiro setup se pretende migrar a config depois.
- Por padrão o pacote usa **client IDs OAuth do próprio autor**. Para ter ciclo de token independente, registre app próprio e exporte `EMAIL_MCP_GMAIL_CLIENT_ID`/`EMAIL_MCP_GMAIL_CLIENT_SECRET` ou `EMAIL_MCP_OUTLOOK_CLIENT_ID` — tanto no setup quanto no ambiente do servidor, pois a renovação usa as mesmas variáveis.
- O escopo Gmail "Full" inclui **exclusão permanente**, ignorando a Lixeira. Prefira "Restricted" quando apagar de vez não for requisito.
- O Hermes filtra o ambiente de subprocessos MCP: variáveis como `EMAIL_MCP_KEY` precisam ser declaradas no bloco `env` do servidor na config.

## Verificação sem conta configurada

Handshake direto por stdio confirma que o binário responde e lista ferramentas:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' '{"jsonrpc":"2.0","method":"notifications/initialized"}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | timeout 30 email-mcp
```

Esperado: `serverInfo` com nome e versão, depois a lista de ferramentas. Isso **não** prova que alguma conta autentica — só `email_list_accounts` e `email_test_account`, já dentro de uma sessão, provam isso.

## Regras de bloqueio permanentes

`email_create_block_rule` cria regra no lado do servidor (Outlook exige escopo `MailboxSettings.ReadWrite`; iCloud/IMAP genérico não suportam). Uma regra por chamada — ferramentas locais não aceitam lote em `tool_call`.

- Prefira `senderDomain` ao domínio de envio real (`mail.market.shein.com`), não ao domínio da marca: promocional quase sempre sai de subdomínio próprio, e bloquear `shein.com` inteiro derrubaria e-mail transacional de pedido.
- Prefira `moveToJunk` a `delete`: o usuário consegue revisar, e regra mal calibrada não destrói mensagem.
- Nunca crie regra para banco, escola, energia, fisco ou plataforma de código sem pedido explícito, mesmo que o volume pareça ruído.
- `email_list_block_rules` devolve também regras pré-existentes do usuário com `value` vazio; não as confunda com regras suas nem as apague.

## Armadilhas

- **`query` no `email_search` não filtra por palavra-chave no Outlook/Graph.** Buscar `query:"hotmart"` devolve a pasta inteira, sem erro algum — o resultado *parece* legítimo e leva a conclusões falsas sobre quantos e-mails casam. Traga as mensagens e filtre em Python por remetente e assunto; conte sempre o que realmente casou antes de relatar número ao usuário.
- `email_list_folders` pode devolver uma página alfabética incompleta. Não conclua que Lixo Eletrônico ou Itens Excluídos não existem só porque não apareceram.
- Resultados de busca estouram o contexto com facilidade (~75 KB para 60 mensagens). Processe o arquivo de spillover com `execute_code` em vez de reimprimir.
- Ferramentas ausentes após configurar: sessão antiga. Abra uma nova.
- `email_add_account` cobre apenas IMAP e iCloud; Gmail e Outlook exigem o assistente.
- Projeto jovem, de autor individual, com acesso total à caixa postal. Trate como terceiro não auditado: revogue o acesso em `myaccount.google.com/permissions` ou `account.live.com/consent/Manage` se desconfiar.
- Operações em lote apagam ou movem centenas de mensagens numa chamada. Confirme antes de executar exclusão em massa.
