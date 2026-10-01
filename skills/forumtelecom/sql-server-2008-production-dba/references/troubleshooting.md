# Runbook rápido de diagnóstico

## Servidor lento
Ordem:
1. confirmar janela/sintoma;
2. requests ativos;
3. waits;
4. blocking;
5. I/O por arquivo;
6. queries de CPU/reads/elapsed;
7. log/TempDB;
8. plano da consulta-alvo;
9. somente então propor mudança.

## Banco crescendo
Verificar:
- qual arquivo;
- growth fixo ou percentual;
- recovery model;
- DBCC SQLPERF(LOGSPACE);
- log backups;
- transações longas;
- histórico de crescimento se disponível.

## Aplicação não conecta
Verificar:
1. serviço da instância;
2. TCP habilitado;
3. listener/porta real;
4. Test-NetConnection;
5. firewall TCP;
6. SQL Browser/UDP 1434 se usa SERVIDOR\INSTANCIA;
7. autenticação;
8. login/database default;
9. ERRORLOG.

## Restore falha por espaço
Não repetir às cegas.
Executar FILELISTONLY, conferir Size, volumes e WITH MOVE.
Especial atenção ao volume de LOG.

## CPU alta
Não reduzir MAXDOP automaticamente.
Identificar requests e query stats; comparar planos e paralelismo real.

## PAGEIOLATCH alto
Não concluir imediatamente "disco ruim".
Correlacionar waits, reads, cache pressure, query plans e latência de arquivo.

## WRITELOG alto
Correlacionar transaction log, storage, frequência de commits, tamanho de transações e log backups.

## Blocking
Identificar blocker raiz. Não executar KILL automaticamente.
