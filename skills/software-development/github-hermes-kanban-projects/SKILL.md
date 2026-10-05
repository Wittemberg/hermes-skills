---
name: github-hermes-kanban-projects
description: "Use for Hermes Kanban and GitHub AI project planning. Use when creating or updating Kanban boards, project tasks or AI-planned work tracked on GitHub Projects via Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, kanban, github, roadmap, projects, ai-agents, sdlc]
    category: software-development
---

# Projetos de IA com Hermes Kanban e GitHub

Use este skill para estruturar vários projetos de desenvolvimento assistido por IA, mantendo o roadmap estratégico no GitHub e a execução durável dos agentes no Hermes Kanban.

## Regras permanentes

- Responda em português do Brasil, de forma direta, com comandos prontos e uma linha explicando cada comando.
- Separe os projetos em boards Hermes independentes; não misture filas de repositórios ou produtos diferentes no board `default`.
- Trate GitHub Projects, Issues, Milestones e PRs como fonte estratégica e de colaboração externa; trate Hermes Kanban como fila operacional, handoff entre agentes, dependências, bloqueios e histórico de execução.
- Não prometa sincronização automática entre GitHub Projects e Hermes Kanban sem verificar uma integração real; o vínculo padrão é por projeto local, repositório, issue, milestone, PR ou URL registrada no corpo/comentários da tarefa.
- Verifique o estado real com CLI antes de propor migração ou importação: boards, projetos Hermes, autenticação GitHub, repositórios e tarefas existentes.
- Preserve a rastreabilidade: cada tarefa operacional deve apontar para a issue, especificação, PR ou decisão GitHub correspondente quando existir.
- Modele roadmap como hierarquia: objetivo/épico → etapa → tarefa executável → revisão/PR; use dependências para impedir execução antes dos pré-requisitos.
- Use `review` para implementação aguardando validação, `blocked` para decisão ou pré-requisito externo e `request-changes` para correção técnica; não use `blocked` para rework comum.
- Antes de criar muitas tarefas, confirme nomes/URLs dos repositórios e o nível desejado de importação; não invente projetos, repositórios ou estados.
- Quando o roadmap vier do código, trate a lista de repositórios como allowlist fechada: valide cada repositório com `gh repo view` e leia apenas os nomes autorizados.
- Ao publicar o dashboard Hermes, reconha a unit/provedor Traefik, preserve o bind do backend apenas numa interface privada alcançável pelo proxy, configure OAuth antes de expor, e valide DNS, certificado confiável, redirect para login e endpoint de healthcheck separadamente. Para diagnóstico de conta Nous, use `hermes portal info` e `hermes_cli.nous_account.get_nous_portal_account_info(force_fresh=True)` pelo Python do virtualenv; não execute `hermes auth logout` apenas para identificar usuário, pois isso revoga a autenticação de inferência e o e-mail pode não ser retornado pelo Portal.
- Confirme o owner/repo canônico antes de clonar ou vincular um projeto; nomes de domínio ou aliases podem apontar para outro repositório, e a correção deve atualizar o Hermes Project e os cards sem apagar o checkout anterior até a nova origem ser validada.
- Faça o inventário antes de criar boards ou cards: clone em área de análise, registre HEAD/branch, arquivos de governança, documentação, workflows, commits recentes, issues e PRs; marque como `a validar` o que não tiver evidência.
- Trate repositório vazio como estado válido: crie apenas cards de definição de escopo e não derive arquitetura ou roadmap do nome do repositório.
- Para uma primeira importação, crie cards em `ready` sem assignee e sem iniciar o dispatcher; a revisão humana deve ocorrer antes de agentes executarem tarefas inferidas.
- Use `--project <slug>` com `--workspace worktree` para código, deixando o Hermes gerar worktrees isolados; não aponte vários cards para a mesma pasta primária com `worktree:<path>`, pois isso mistura branches e concorrência.
- Após qualquer criação ou alteração de board, projeto ou tarefa, releia a entidade com o comando apropriado e confirme IDs, board, vínculos e status.
- Ao testar um domínio do dashboard, separe três verificações: DNS apontando ao host, roteamento HTTP/Traefik chegando ao serviço e certificado TLS confiável; um certificado autoassinado prova apenas que houve resposta, não que o acesso público está pronto.
- Confirme os totais programaticamente por board e por status; não reporte uma contagem baseada apenas na saída visual parcial do terminal.

## Procedimento

1. Faça o inventário local:

   Para importar roadmap a partir de repositórios, valide primeiro a allowlist e só depois clone os repositórios para uma área de análise. Uma sequência mínima é:

   ```bash
   gh repo view <owner>/<repo> --json nameWithOwner,isPrivate,defaultBranchRef,url,description
   gh issue list --repo <owner>/<repo> --state all --limit 100
   gh pr list --repo <owner>/<repo> --state all --limit 100
   gh repo clone <owner>/<repo> /caminho/de/analise/<repo> -- --depth=50 --no-tags
   ```

   Registre o commit analisado e procure README, ROADMAP, documentos de estado, Docker/Compose/Stack, workflows, manifests, testes e TODOs. Se o clone não tiver commits, registre o repositório como vazio e pare a inferência técnica nesse projeto.

   Para uma importação inicial, gere primeiro um inventário por repositório e só então crie os boards, projetos e cards. Use `--idempotency-key` em criações que possam ser repetidas. Se o usuário corrigir um repositório depois da criação, valide o novo `gh repo view`, clone-o em um novo caminho, atualize o Hermes Project com `remove-folder`/`add-folder --primary`, registre a correção em comentário e só depois ajuste os cards; não deixe descrições antigas afirmarem que o repositório está vazio.

2. Confira o estado Hermes e GitHub:

   ```bash
   hermes kanban boards list
   hermes kanban boards current
   hermes project list
   hermes kanban stats
   gh auth status
   ```

   Identifique boards, projetos, tarefas, autenticação e escopo antes de escrever qualquer estado.

3. Mapeie cada produto para um par isolado:

   ```text
   GitHub Project/Repository → Hermes Project → Hermes Board
   ```

   Use o slug do board em kebab-case e um nome legível separado. Aponte o Hermes Project para a pasta local primária do repositório quando ela existir.

4. Crie o board e o projeto local:

   ```bash
   hermes kanban boards create <slug> \
     --name "<Nome do projeto>" \
     --description "<escopo>"

   hermes project create "<Nome do projeto>" \
     --slug <slug> \
     --primary /caminho/absoluto/do/repositorio \
     --board <slug>
   ```

   Use `--switch` ou `--use` somente quando o projeto deve virar o contexto ativo da sessão.

5. Modele o roadmap em camadas.

   ```bash
   hermes kanban --board <slug> create "Épico: <nome>" \
     --body "Objetivo: ...\nGitHub: https://github.com/<owner>/<repo>/issues/<n>"

   hermes kanban --board <slug> create "Etapa: <nome>" \
     --parent <id-do-epico> \
     --body "Critérios: ...\nGitHub: <url>"
   ```

   Use `--parent` quando a tarefa já nasce dependente do épico; use `hermes kanban link <pai> <filho>` para dependências adicionadas depois.

6. Atribua cada tarefa a um perfil especializado apenas quando o perfil existir e o trabalho estiver suficientemente especificado. Para código, prefira `--workspace worktree`; para análise ou triagem, use `scratch` ou `dir:<caminho>` conforme a necessidade de persistência.

7. Relacione implementação e PR com contrato de conclusão quando o trabalho precisa publicar em um repositório:

   ```bash
   hermes kanban --board <slug> create "Implementar <feature>" \
     --project <projeto> \
     --assignee <perfil> \
     --workspace worktree \
     --completion-contract <OWNER/REPO>
   ```

   Use `local-only` para tarefas deliberadamente locais. Não marque como concluída uma tarefa de PR sem verificar a PR, o commit e os checks exigidos.

8. Opere o ciclo e registre evidências:

   ```bash
   hermes kanban --board <slug> list --sort status
   hermes kanban --board <slug> show <task-id>
   hermes kanban --board <slug> comment <task-id> "<evidência ou decisão>"
   hermes kanban --board <slug> stats
   ```

   Antes de afirmar que algo está pronto, confira a tarefa, comentários, eventos, PR e checks atuais.

9. Faça uma revisão periódica por projeto: compare roadmap do GitHub com tarefas Hermes, identifique itens sem vínculo, etapas atrasadas, cards bloqueados antigos e PRs sem tarefa. Atualize o board e o GitHub somente após confirmar a correspondência dos IDs e URLs.

## Armadilhas

- **Misturar quatro produtos no board `default`:** boards são a fronteira de isolamento; separar por projeto evita que workers, dependências e estatísticas se contaminem.
- **Prometer sincronização nativa com GitHub Projects:** o Kanban e o GitHub têm estados independentes; links explícitos preservam rastreabilidade sem criar uma integração inexistente.
- **Criar tarefas filhas sem critérios:** o dispatcher pode liberar uma tarefa bem ordenada, mas não consegue compensar uma especificação vaga; escreva resultado esperado e evidência de conclusão no corpo.
- **Usar apenas o título da issue como contexto:** decisões ficam em comentários, PRs e documentação; leia o contexto completo antes de decompor ou reescrever trabalho.
- **Usar `blocked` para defeito corrigível:** `request-changes` devolve o mesmo trabalho ao implementador e conserva a revisão; `blocked` deve representar decisão humana ou dependência externa.
- **Usar worktree sem repositório primário válido:** o worker não terá uma base Git confiável; valide a pasta local e o vínculo do Hermes Project antes de despachar código.
- **Marcar PR como concluída sem leitura final:** checks podem estar pendentes, falhos ou associados a outro commit; releia o estado remoto e a cabeça da PR no momento da conclusão.
- **Criar cards em massa sem idempotência:** automações repetidas duplicam o roadmap; use `--idempotency-key` quando a criação puder ser reexecutada.
- **Tratar um hostname como nome canônico do repositório:** o domínio do produto pode estar hospedado em outro owner/repo; valide `nameWithOwner`, branch e URL com `gh repo view` antes de concluir que um checkout vazio representa o projeto.
- **Confundir resposta TLS com publicação pronta:** um `curl -k` ou certificado autoassinado pode ocultar falha de ACME; teste primeiro com validação normal e reporte separadamente DNS, HTTP e confiança do certificado.

## Referências

- Para a matriz de responsabilidades, convenção de boards e receitas de comandos, consulte `references/github-kanban-mapping.md`.
