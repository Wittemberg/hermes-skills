---
name: sql-server-2008-production-dba
description: "DBA operacional e tuning para SQL Server 2008 e 2008 R2. Use quando houver lentidão, travamentos, manutenção, backup ou tuning em bases SQL Server 2008/2008 R2 em produção."
version: 1.0.0
author: Wittemberg, TecnoTeam, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [sql-server, sql-server-2008, dba, performance, tuning, windows-server, backup, restore]
    category: forumtelecom
    related_skills: [windows-server-ops, active-directory-ops]
---

# SQL Server 2008/2008 R2 — Production DBA

Especialista operacional em Microsoft SQL Server 2008 e 2008 R2 para preparação de servidores novos, configuração de instâncias, padronização de bancos, restores legados e diagnóstico/tuning fino em ambientes de produção com abordagem conservadora, mensurável e reversível.

## When to Use

Use esta skill quando for solicitado:
- Instalação, preparação e dimensionamento de servidor/instância SQL Server 2008 ou 2008 R2.
- Revisão de instâncias existentes (múltiplas instâncias, CPU, memória, TempDB, IFI, MAXDOP, portas).
- Diagnóstico de performance: CPU alta, lentidão, gargalos de I/O, waits (`PAGEIOLATCH`, `WRITELOG`), locks e bloqueios.
- Análise de consultas caras, missing indexes, fragmentação e manutenção de estatísticas.
- Padronização de novos bancos de dados (`model`, sizing inicial de MDF/LDF e autogrowth).
- Planejamento, validação e execução de restore de bases legadas (`RESTORE HEADERONLY`/`FILELISTONLY`, `WITH MOVE`).
- Análise de transações longas, estouro de transaction log (`LDF`), recovery models e rotinas de backup.
- Diagnóstico de rede: TCP/IP, portas estáticas vs dinâmicas, SQL Server Browser e regras de firewall.

## Não usar / Limitações

- Não aplicar receitas, parâmetros ou sintaxes de versões modernas do SQL Server (2014+) que não existam ou tenham comportamento divergente no 2008/2008 R2 (ex: `Buffer Pool Extension`, `Columnstore`, `In-Memory OLTP`, `Query Store`).
- Não atualizar Service Pack/CU, collation, compatibilidade ou credenciais de serviço sem etapa prévia de homologação.
- Não executar comandos destrutivos sem autorização explícita e plano de rollback.

## Regras operacionais obrigatórias

1. **Inspecionar antes de alterar:** Coletar métricas e configurações atuais antes de qualquer modificação.
2. **Uma mudança controlada por vez:** Isolar variáveis para validar a causalidade de cada ajuste.
3. **Comandos copiáveis e objetivos:** Fornecer blocos de comando prontos para copiar e colar, com explicação direta em uma linha.
4. **Validação imediata:** Após cada alteração, rodar comando de checagem do estado aplicado.
5. **Zero presunção:** Nunca presumir nomes de instância, portas, caminhos de disco, memória ou topologia de CPU.
6. **Não reiniciar sem necessidade comprovada:** Minimizar impacto operacional; avisar antes de qualquer restart de serviço.
7. **Proibido shrink rotineiro:** Não usar `SHRINKDATABASE`/`SHRINKFILE` como rotina de manutenção.
8. **Proibido Auto Close / Auto Shrink:** Garantir `AUTO_CLOSE OFF` e `AUTO_SHRINK OFF` em bancos de produção.
9. **Não limpar caches cegamente:** Evitar `DBCC FREEPROCCACHE` ou `DBCC DROPCLEANBUFFERS` globais em produção.
10. **Validação de Restore:** Sempre rodar `RESTORE HEADERONLY` e `RESTORE FILELISTONLY` antes de restaurar.

## Filosofia de tuning

Seguir rigorosamente o ciclo:
**Sintoma → Medição inicial (baseline) → Hipótese → Mudança mínima isolada → Medição pós-ajuste → Manter ou Reverter.**

---

# PARTE A — SERVIDOR NOVO & INFRAESTRUTURA

## 1. Inventário inicial do host

Executar no PowerShell para mapear hardware, sistema e serviços SQL:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, TotalVisibleMemorySize
Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory, NumberOfProcessors, NumberOfLogicalProcessors
Get-CimInstance Win32_Processor | Select-Object DeviceID, Name, NumberOfCores, NumberOfLogicalProcessors
Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, AllocationUnitSize, Size, SizeRemaining | Format-Table -AutoSize
Get-CimInstance Win32_Service | Where-Object {$_.Name -match 'MSSQL|SQLAgent|SQLBrowser'} | Select-Object Name, State, StartMode, StartName | Format-Table -AutoSize
```

## 2. Layout de armazenamento

Padronização recomendada de volumes (NTFS com Allocation Unit de 64 KB):
- `D:\MSSQL\Data\<INSTANCIA>\` — Arquivos de dados (`.mdf`, `.ndf`)
- `L:\MSSQL\Log\<INSTANCIA>\` — Arquivos de log de transação (`.ldf`)
- `T:\MSSQL\TempDB\<INSTANCIA>\` — TempDB (dados e log)
- `Z:\MSSQL\Backup\<INSTANCIA>\` — Backups locais / staging

## 3. Configuração de memória

Verificar configuração atual:
```sql
SELECT name, value, value_in_use FROM sys.configurations WHERE name IN ('min server memory (MB)','max server memory (MB)');
```

Calcular limite (deixar 4–8 GB livres para SO e processos externos; dividir entre instâncias se houver mais de uma):
```sql
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'max server memory (MB)', <VALOR_EM_MB>;
RECONFIGURE;
```

## 4. Paralelismo (MAXDOP & Cost Threshold)

Configurar limites para evitar contenção de CPU e waits `CXPACKET` excessivos:
```sql
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'max degree of parallelism', 4; -- Ajustar conforme sockets/NUMA (ref: 4 a 8)
RECONFIGURE;
EXEC sp_configure 'cost threshold for parallelism', 50; -- Default 5 é excessivamente baixo
RECONFIGURE;
```

## 5. Optimize for Ad hoc Workloads

Reduzir consumo de memória do plan cache por queries de execução única:
```sql
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'optimize for ad hoc workloads', 1;
RECONFIGURE;
```

## 6. Dimensionamento do TempDB

Consultar layout atual:
```sql
SELECT name, type_desc, physical_name, size/128.0 AS SizeMB, growth, is_percent_growth FROM tempdb.sys.database_files;
```

Diretrizes:
- 1 data file por núcleo de CPU até 4 ou 8 arquivos (tamanhos idênticos).
- Crescimento fixo em MB (ex: 512 MB ou 1024 MB), nunca percentual.
- Exemplo validado: 4 data files x 4096 MB + 1 log file x 4096 MB com crescimento de 512 MB.

## 7. Instant File Initialization (IFI)

Conceder o privilégio `Perform volume maintenance tasks` (`SeManageVolumePrivilege`) à conta de serviço do Database Engine para evitar zero-initialization em arquivos de dados (`MDF`/`NDF`).
*Nota: Requer reinicialização do serviço para entrar em vigor.*

## 8. Padronização de novos bancos (`CREATE DATABASE`)

Não confiar exclusivamente no `model` para parâmetros de crescimento no 2008 R2. Especificar explicitamente:
```sql
CREATE DATABASE [<BANCO>]
ON PRIMARY
(
    NAME = N'<BANCO>',
    FILENAME = N'D:\MSSQL\Data\<INSTANCIA>\<BANCO>.mdf',
    SIZE = 256MB,
    FILEGROWTH = 256MB
)
LOG ON
(
    NAME = N'<BANCO>_log',
    FILENAME = N'L:\MSSQL\Log\<INSTANCIA>\<BANCO>_log.ldf',
    SIZE = 128MB,
    FILEGROWTH = 128MB
);
```

## 9. Rede, Firewall e Portas

Identificar portas e processos ativos:
```powershell
Get-CimInstance Win32_Service | Where-Object {$_.Name -match '^MSSQL\$'} | Select-Object Name, ProcessId, State
Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
```
- Usar portas TCP estáticas para instâncias nomeadas.
- SQL Browser: UDP 1434 (necessário se conexões usarem `SERVIDOR\INSTANCIA`).

---

# PARTE B — RESTORE E MIGRAÇÃO

## 10. Inspeção prévia do backup

Nunca restaurar sem inspecionar o arquivo `.bak`:
```sql
RESTORE HEADERONLY FROM DISK = N'<CAMINHO_DO_BAK>';
RESTORE FILELISTONLY FROM DISK = N'<CAMINHO_DO_BAK>';
```
- Validar versão de origem, nomes lógicos e espaço em disco para cada arquivo com `WITH MOVE`.

## 11. Validação pós-restore

Inspecionar propriedades herdadas do banco de origem:
```sql
SELECT name, compatibility_level, collation_name, recovery_model_desc, page_verify_option_desc,
       is_auto_close_on, is_auto_shrink_on, is_auto_create_stats_on, is_auto_update_stats_on
FROM sys.databases WHERE name = N'<BANCO>';
```

Corrigir opções inadequadas:
```sql
ALTER DATABASE [<BANCO>] SET AUTO_CLOSE OFF;
ALTER DATABASE [<BANCO>] SET AUTO_SHRINK OFF;
ALTER DATABASE [<BANCO>] SET PAGE_VERIFY CHECKSUM;
ALTER DATABASE [<BANCO>] SET AUTO_CREATE_STATISTICS ON;
ALTER DATABASE [<BANCO>] SET AUTO_UPDATE_STATISTICS ON;
```

---

# PARTE C — DIAGNÓSTICO E TUNING EM PRODUÇÃO

## 12. Snapshot de sessões e requests ativos

Identificar o que está executando agora, tempos de CPU/elapsed e bloqueios:
```sql
SELECT r.session_id, r.status, r.command, r.cpu_time, r.total_elapsed_time,
       r.reads, r.writes, r.logical_reads, r.blocking_session_id,
       r.wait_type, r.wait_time, DB_NAME(r.database_id) AS database_name,
       s.host_name, s.program_name, s.login_name, t.text
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.session_id <> @@SPID
ORDER BY r.total_elapsed_time DESC;
```

## 13. Análise de Wait Statistics

Levantar os principais gargalos acumulados na instância:
```sql
SELECT TOP 30 wait_type, waiting_tasks_count, wait_time_ms, signal_wait_time_ms,
       CAST(100.0 * wait_time_ms / NULLIF(SUM(wait_time_ms) OVER(),0) AS decimal(6,2)) AS pct
FROM sys.dm_os_wait_stats
WHERE wait_time_ms > 0
ORDER BY wait_time_ms DESC;
```

## 14. Latência de I/O por arquivo

Descobrir arquivos com maior tempo de resposta em leitura e escrita:
```sql
SELECT DB_NAME(vfs.database_id) AS database_name, mf.name, mf.type_desc, mf.physical_name,
       vfs.num_of_reads, vfs.io_stall_read_ms,
       CASE WHEN vfs.num_of_reads = 0 THEN 0 ELSE vfs.io_stall_read_ms / vfs.num_of_reads END AS avg_read_ms,
       vfs.num_of_writes, vfs.io_stall_write_ms,
       CASE WHEN vfs.num_of_writes = 0 THEN 0 ELSE vfs.io_stall_write_ms / vfs.num_of_writes END AS avg_write_ms
FROM sys.dm_io_virtual_file_stats(NULL,NULL) vfs
JOIN sys.master_files mf ON vfs.database_id = mf.database_id AND vfs.file_id = mf.file_id
ORDER BY (vfs.io_stall_read_ms + vfs.io_stall_write_ms) DESC;
```

## 15. Top Queries por consumo de CPU / Reads

Identificar consultas com maior impacto acumulado no cache:
```sql
SELECT TOP 25 qs.execution_count, qs.total_worker_time,
       qs.total_worker_time / NULLIF(qs.execution_count,0) AS avg_cpu,
       qs.total_logical_reads, qs.total_logical_reads / NULLIF(qs.execution_count,0) AS avg_reads,
       qs.total_elapsed_time, qs.total_elapsed_time / NULLIF(qs.execution_count,0) AS avg_elapsed,
       SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
       ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text) ELSE qs.statement_end_offset END - qs.statement_start_offset)/2)+1) AS statement_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.total_worker_time DESC;
```

## 16. Monitoramento de Transaction Log

Consultar espaço utilizado no Log:
```sql
DBCC SQLPERF(LOGSPACE);
```

---

## Arquivos de Referência

- [validated-baseline.md](references/validated-baseline.md) — Exemplo validado em ambiente real com 2 instâncias, 20 vCPUs e 160 GB RAM.
- [troubleshooting.md](references/troubleshooting.md) — Runbook rápido para lentidão, CPU alta, crescimento de log, falhas de conexão e bloqueios.
