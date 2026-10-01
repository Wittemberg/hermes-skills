---
name: wittemberg-development
description: Use when coding for Wittemberg. Apply project standards.
version: 0.1.0
author: Wittemberg, Hermes Agent
---

# Desenvolvimento conforme a biblioteca Wittemberg

## Quando usar
Use em implementação, revisão, planejamento, início ou realinhamento de projetos de software do usuário. Não aplicar este processo a conversa casual ou tarefas alheias a desenvolvimento. Não capturar uma implementação clara como brainstorm obrigatório.

## Fonte e escopo
Biblioteca canônica local: `/root/.hermes/libraries/harness-skills`, checkout de `Wittemberg/harness-skills`, revisão `9dbc93d105de52d855f7e0cdd4671aa97c3c8352`. Biblioteca instalada apenas no perfil default. Preserve originais e proveniência. Não cadastrar a raiz como diretório de skills: a descoberta recursiva ativaria snapshots upstream não selecionados. Referências abaixo são relativas à biblioteca, não à pasta deste skill.

## Procedimento
1. Leia as instruções do projeto, README, manifestos, estado Git e arquivos afetados antes de editar. Leia `AGENTS.md` da biblioteca, `docs/compatibilidade.md` e a seção pertinente de `docs/manual.md` com `read_file`. Regras do ambiente e autorização atual prevalecem sobre os originais importados.
2. Determine resultado observável, escopo e critérios de aceite. Reuse decisões existentes; pergunte somente por lacunas que mudem implementação ou compatibilidade. Preserve contratos e comportamentos aprovados.
3. Correção pequena: implemente diretamente e verifique, sem gerar documentação desnecessária. Mudança relevante: continue a mudança OpenSpec existente ou crie uma mudança delimitada quando a integração estiver disponível. Confirme CLI/versão antes de alegar integração. Se ausente, use requisitos/tarefas Markdown e declare a limitação, sem instalar ferramentas globais implicitamente.
4. Projeto novo: leia `skills/iniciar-projeto/SKILL.md` e `standards/wittemberg/checklists/NEW-PROJECT.md`. Escolha stack por requisitos. Boilerplate somente em destino novo e compatível; inicialize/renomeie antes de anexar a biblioteca. Nunca sobrescreva projeto existente com template.
5. Aplique a baseline lendo `standards/wittemberg/README.md` e somente os padrões da área afetada. UI: zoom 100%, responsividade, teclado, feedback, overflow e tokens existentes. Backend: persistência após reinício, segurança, isolamento de tenant e tratamento de falhas. Daemons locais: recuperação de conexões e distinção entre falhas de rede, hardware e aplicação. Identifique consumidores antes de modificar componentes compartilhados.
6. Mantenha uma fonte canônica por finalidade: PRD opcional para visão de produto; TRD/ADR para decisões técnicas globais; OpenSpec para requisitos e tarefas da mudança. Não duplicar execução em SDD, issues e OpenSpec. Estado curto de retomada referencia a mudança ativa; reutilize o arquivo do projeto ou proponha `docs/estado.md` quando necessário.
7. Execute testes, lint/build e verificações adequados. Separe falhas preexistentes e bloqueios de ambiente. Arquive mudanças somente com evidência; não confunda validação estrutural com produto funcionando nem arquivamento com deploy.
8. Entregue alterações, resultados reais, limitações e próximo passo. Não modificar consumidores não relacionados, publicar ou implantar sem autorização pertinente.

## Consulta especializada e adaptações obrigatórias
- Exploração explicitamente pedida: `skills/brainstorm/SKILL.md` e referências. Pesquisa e APIs de leitura são permitidas; efeitos externos dependem da autorização. Marque desconhecido como não determinado; não invente premissas para encerrar discussão. Pedido explícito de salvar já autoriza documentação no escopo.
- PRD: `skills/escrever-prd/SKILL.md` e templates. Na baseline OpenSpec, priorize visão estratégica; PRD por feature somente quando o projeto já adotar essa convenção. Não presumir skills SDD ausentes, expansão automática de `$ARGUMENTS` ou mudanças automáticas de status. Preserve IDs e valide dependências/ciclos quando utilizados.
- TRD/ADR: `skills/escrever-trd/SKILL.md` e templates. Carregue contexto explicitamente. Revalide fatos externos voláteis e registre fonte, data e versão; não basta citar nome da ferramenta. Decisão aprovada não torna premissas inferidas fatos confirmados. Supersessão pode atualizar status e vínculo do ADR anterior, mantendo seu texto histórico.
- Seleção de ferramentas: `skills/selecionar-recursos/SKILL.md`, `docs/curadoria.md` e ficha pertinente em `catalog/sources/`. Consulte fatos atuais; catálogo não comprova instalação, preço, manutenção ou segurança. Escolher não autoriza instalar, conectar contas ou transmitir dados.
- Criação de skills Hermes: use `skill_manage` e autoria nativa. `skills/skill-creator/` fica como referência passiva Codex; não executar seus geradores como instaladores Hermes nem escrever em `.codex` sem pedido específico.

## Limites da revisão
O núcleo curado, documentação, padrões e scripts locais foram revisados. Upstream permanece material passivo: preservação por hash não equivale a auditoria integral ou autorização de execução. Os validadores não cobrem todas as entradas de inventário, duplicatas de caminho normalizado ou links em templates. Atualizações remotas não devem substituir silenciosamente o snapshot.

## Verificação da biblioteca
Use `terminal` com cwd na biblioteca e `PYTHONDONTWRITEBYTECODE=1`:
- `python3 scripts/validate.py`
- `python3 -m unittest discover -s tests -v`
Confira `git status --porcelain` para preservar originais. Para atualização autorizada, revise diferenças e proveniência antes de adotar nova revisão. Instalação deste adaptador não instala OpenSpec, MCPs, hooks, runtimes ou dependências mencionadas nas fontes.
