---
name: claude-code-apipromax
description: "Use when configuring Claude Code with APIProMax."
version: 0.2.0
author: Wittemberg (Wittemberg), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Claude-Code, APIProMax, Anthropic, CLI]
    related_skills: [claude-code, generic-openai-compatible-cli-providers]
---

# Claude Code CLI com APIProMax

## Quando usar

Configurar ou diagnosticar Claude Code CLI com o gateway APIProMax usando protocolo Anthropic-compatible. Não aplicar esta configuração ao provider do Hermes nem a clientes OpenAI-compatible.

## Pré-requisitos

- Verificar instalação usando `terminal(command='command -v claude; claude --version; claude --help')`.
- Obter a chave APIProMax de armazenamento protegido ou variável de ambiente autorizada. Quando já existir uma chave APIProMax no settings.json, preservá-la. Não substituir silenciosamente por outra credencial.
- Nunca imprimir a chave, incluí-la em argumentos de comandos, histórico, exemplos reais, logs ou nesta skill.
- Nunca pedir a chave pelo chat. Se indisponível, orientar inserção local segura ou usar mecanismo de credenciais disponível.

## Configuração essencial

Arquivo global: `~/.claude/settings.json`.
Mesclar os campos abaixo preservando opções não relacionadas. O texto `<chave APIProMax>` é somente um marcador: nunca gravá-lo como credencial real.

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.apipromax.com.br",
    "ANTHROPIC_API_KEY": "<chave APIProMax>",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-fable-5"
  },
  "model": "claude-opus-5"
}
```

## SIMPLE MODE: regra crítica

Para esta configuração, definir `CLAUDE_CODE_SIMPLE=1` no ambiente do shell antes de iniciar o Claude Code. NÃO colocar essa variável no bloco `env` de `~/.claude/settings.json`: no ambiente relatado pelo usuário, ela pode ser ignorada nesse local.

```bash
export CLAUDE_CODE_SIMPLE=1
```

Para root, persistir o export em `/root/.bashrc` e `/root/.profile`, com backup prévio de cada arquivo, preservando o restante do conteúdo e evitando exports duplicados. Conferir o fluxo de inicialização do shell: uma configuração depois de um `return` pode não ser executada. Alterar os arquivos não atualiza shells já abertos; aplicar o export também no shell em que será executado `claude`.

## Procedimento

1. Ler a configuração local com Python pelo `terminal`, exibindo somente nomes de campos, valores não secretos e booleanos de presença das credenciais. Inspecionar também a presença de `ANTHROPIC_AUTH_TOKEN` no ambiente herdado e configurações locais do projeto, sem revelar seu valor.
2. Antes de qualquer alteração, copiar o settings.json existente para `settings.json.bak-<timestamp>` no mesmo diretório. Usar timestamp calculado por ferramenta, evitar sobrescrever backups e aplicar modo 600 ao backup. Se o arquivo não existir, registrar esse fato e criar o diretório necessário.
3. Mesclar os campos da configuração essencial. Usar `ANTHROPIC_API_KEY`, nunca `ANTHROPIC_AUTH_TOKEN`. Remover o campo conflitante do settings.json dentro do escopo autorizado; não alterar outros logins ou arquivos sem verificar seu uso.
4. Garantir que nenhum token de autenticação seja herdado pelo processo de teste. Se houver export persistente em perfil de shell, localizar e propor correção com backup. Não mascarar um conflito usando somente um ambiente temporário e depois afirmar que o comando normal funciona.
5. Aplicar `chmod 600 ~/.claude/settings.json` via `terminal`. Manter segredos apenas em arquivos protegidos; não usar `read_file` para despejar arquivos com chave.
6. Configurar SIMPLE no shell conforme a regra crítica acima; se estiver no env do settings.json, remover somente essa entrada na edição autorizada e com backup. Validar JSON, modelo, aliases, URL, ausência de AUTH_TOKEN e permissões com leitura redigida. Conferir separadamente `echo "$CLAUDE_CODE_SIMPLE"` no shell de execução: deve retornar `1`. Verificar também a persistência em um novo shell apropriado. Informar os caminhos dos backups.
7. Executar os testes abaixo com timeout limitado. Não trocar modelos nem comprar créditos automaticamente se o gateway recusar a solicitação.

## Validação

1. No shell com `CLAUDE_CODE_SIMPLE=1`, executar `claude --model claude-opus-5 -p "Responda apenas API_OK." --output-format text --no-session-persistence`, em diretório confiável e com timeout limitado. Verificar resposta `API_OK` e exit code 0; não confundir saída esperada com resultado observado.
2. Iniciar `claude` sem `-p` em sessão tmux dedicada, conforme a skill `claude-code`. Capturar a tela e ler qualquer diálogo antes de responder; não aprovar permissões às cegas.
3. Enviar `Responda apenas OK` no modo interativo e capturar a resposta. A abertura da interface não comprova autenticação: exigir resposta real do modelo.
4. Encerrar apenas a sessão de teste usando `/exit`. Não encerrar sessões do usuário.
5. Relatar separadamente configuração gravada, teste print e teste interativo. Só declarar integração funcional se ambos responderem.

## Armadilhas e diagnóstico

- Manter `CLAUDE_CODE_SIMPLE=1` no ambiente do shell, não no env do settings.json: é requisito desta configuração APIProMax para modo interativo, informado pelo usuário. Sem ele, `claude -p` pode funcionar enquanto `claude` retorna `401 Invalid token`; não tratar sucesso no print como validação do interativo.
- Se print funcionar e interativo retornar 401, verificar primeiro `echo "$CLAUDE_CODE_SIMPLE"`. Se vazio, aplicar `export CLAUDE_CODE_SIMPLE=1` e repetir o teste; não começar trocando chave, modelo, BASE_URL ou credenciais OAuth.
- O usuário relatou falhas de debug em `source=verify_api_key`, `source=generate_session_title` e `source=repl_main_thread` sem SIMPLE. São pistas do ambiente relatado, não prova de causa única para todo 401.
- O diálogo `Accessing workspace` / `Yes, I trust this folder` é confirmação de confiança no diretório, não erro de API. Só confirmar para diretório efetivamente confiável e dentro do escopo autorizado.
- A interface SIMPLE pode parecer parada inicialmente. Digitar uma mensagem e pressionar Enter antes de diagnosticar travamento; exigir resposta real para validar.
- Não configurar API_KEY e AUTH_TOKEN simultaneamente. Não converter a chave para bearer token por tentativa.
- Manter BASE_URL exatamente como acima, sem `/v1`; não copiar automaticamente o base_url OpenAI-compatible do Hermes. O protocolo Anthropic usa a rota Messages, normalmente `/v1/messages` acrescentada pelo cliente.
- Os modelos opus-5, sonnet-5 e fable-5 são identificadores do gateway fornecidos pelo usuário; disponibilidade depende da chave e do catálogo. Não alegar que são nomes oficiais ou que todos foram testados.
- HTTP 403 contendo `用户额度不足` e saldo zero indica recusa por cota/saldo informada pelo gateway. Reportar o bloqueio e solicitar ajuste de saldo/cota pelo usuário; não afirmar que o teste passou, nem trocar autenticação para AUTH_TOKEN.
- HTTP 401 requer conferir URL, chave, conflitos de ambiente e SIMPLE. Não concluir causa única sem evidência.
- HTML com HTTP 200 na raiz do gateway não valida a API. Uma chamada HTTP direta bem-sucedida também não substitui testes reais do CLI.
- Não registrar chaves reais em skills ou exemplos. Backups também contêm segredos e exigem modo 600.

## Ambiente validado informado pelo usuário

O usuário informou validação em Ubuntu 24.04, Claude Code 2.1.278, APIProMax e modelo `claude-opus-5`: com SIMPLE exportado no shell, `claude` abriu o modo interativo e respondeu normalmente. AUTH_TOKEN causou conflito e não resolveu o interativo; preservar API_KEY, sem configurar ambos simultaneamente.

Esse registro é evidência fornecida pelo usuário, não teste executado automaticamente ao editar esta skill nem garantia para outras versões. Em novas configurações, repetir os testes print e interativo.

## Segurança adicional

Se uma chave tiver sido exposta publicamente, em conversa ou em logs, recomendar revogação e geração de uma nova chave. Nos relatórios, representar credenciais apenas como `[CONFIGURADA]`, nunca mostrar o valor completo.

## Critério de conclusão

Configuração e backup protegidos, campos exatos conferidos, ausência de autenticação conflitante, resposta real em print e interativo. Se houver bloqueio de saldo, rede ou credencial, entregar a configuração salva e indicar explicitamente quais testes falharam ou ficaram pendentes.
