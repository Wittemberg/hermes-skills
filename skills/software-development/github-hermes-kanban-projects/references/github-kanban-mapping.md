# Mapeamento GitHub ↔ Hermes Kanban

## Responsabilidade por sistema

| Necessidade | Sistema recomendado |
|---|---|
| Visão estratégica, releases e prioridades | GitHub Projects/Milestones |
| Requisitos, bugs e discussão pública | GitHub Issues |
| Código, branches, revisão e CI | GitHub Repository/PR |
| Execução de agentes, handoffs e retries | Hermes Kanban |
| Dependências entre etapas | Hermes Kanban links |
| Decisões de execução e bloqueios | Comentários da tarefa Hermes e issue/PR relacionada |

## Convenção para quatro projetos

```text
<produto-a> → board <produto-a> → Hermes Project <Produto A> → repo local A
<produto-b> → board <produto-b> → Hermes Project <Produto B> → repo local B
<produto-c> → board <produto-c> → Hermes Project <Produto C> → repo local C
<produto-d> → board <produto-d> → Hermes Project <Produto D> → repo local D
```

Não crie vínculos entre boards: a separação é intencional. Para dependência entre produtos, registre URLs e IDs nos corpos/comentários e trate a coordenação como decisão explícita.

## Hierarquia de tarefas

```text
Objetivo do produto
└── Épico ou versão
    └── Etapa técnica
        └── Tarefa executável
            └── Revisão/PR
```

Uma tarefa deve conter: resultado esperado, critérios de aceite, link GitHub relacionado, perfil responsável quando definido e artefato/check que comprova a conclusão.

## Dashboard Hermes remoto

Antes de publicar, confirme os args e labels de um serviço funcional do Traefik, valide DNS público e proteja o dashboard com OAuth. Se o dashboard Hermes já roda no host, mantenha o listener privado e encaminhe pelo proxy; não exponha a porta interna diretamente. Teste a rota pública sem desabilitar validação TLS: um certificado autoassinado não prova emissão ACME. O aceite mínimo é certificado confiável para o hostname, `/api/health` saudável, `/` redirecionando ao provedor OAuth, API privada respondendo `401` sem sessão e serviço persistente após reinício.

Para identificar a conta Nous vinculada à inferência, consulte `hermes portal info` e, se necessário, `get_nous_portal_account_info(force_fresh=True)` usando o Python do virtualenv do Hermes. A resposta pode informar organização/identificador sem email; não prometa que o token revela o endereço de login. O OAuth do dashboard é um registro separado do login de inferência. Não use `hermes auth logout` como etapa de descoberta de identidade, pois isso desconecta a inferência.

## Ciclo operacional

```text
triage → todo → ready → running → review → done
                          │          └→ request-changes → running
                          └→ blocked (decisão/pré-requisito externo)
```

`todo` aguarda especificação ou dependências; `ready` está liberada para execução; `review` aguarda validação independente.

## Receita de auditoria

```bash
for board in <produto-a> <produto-b> <produto-c> <produto-d>; do
  hermes kanban --board "$board" stats
  hermes kanban --board "$board" list --status blocked --json
  hermes kanban --board "$board" list --status review --json
done
```

Depois compare os IDs/URLs encontrados com `gh issue list`, `gh pr list` e o GitHub Project correspondente. Não declare cobertura completa sem conferir todos os boards e estados.