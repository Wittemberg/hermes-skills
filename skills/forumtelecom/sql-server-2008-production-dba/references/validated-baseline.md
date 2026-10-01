# Baseline validado — exemplo real

Este arquivo registra um exemplo validado durante a construção da skill. Ele serve como referência operacional, NÃO como valores universais.

## Host
- Windows Server 2016 Datacenter
- 160 GB RAM
- 20 vCPUs
- 2 sockets x 10 cores
- SQL Server 2008 R2 Enterprise x64
- duas instâncias: OASIS e NUCLEO

## Volumes
- C: Windows/system databases
- D: DATA, NTFS 64 KB
- L: LOG, NTFS 64 KB
- T: TEMPDB, NTFS 64 KB
- Z: BACKUP, NTFS 64 KB

## Instâncias
OASIS:
- max server memory 71680 MB
- MAXDOP 4
- cost threshold 50
- optimize for ad hoc workloads 1
- TCP 10401
- Data D:\MSSQL\Data\OASIS
- Log L:\MSSQL\Log\OASIS
- TempDB T:\MSSQL\TempDB\OASIS
- Backup Z:\MSSQL\Backup\OASIS

NUCLEO:
- max server memory 71680 MB
- MAXDOP 4
- cost threshold 50
- optimize for ad hoc workloads 1
- TCP 10601
- caminhos equivalentes em NUCLEO

## TempDB por instância
- 4 data files x 4096 MB
- 1 log x 4096 MB
- crescimento 512 MB
- dados de tamanho igual

## Model
- FULL
- CHECKSUM
- compatibility 100
- AUTO_CLOSE OFF
- AUTO_SHRINK OFF
- AUTO_CREATE_STATS ON
- AUTO_UPDATE_STATS ON
- RCSI OFF
- Snapshot Isolation OFF

O teste com CREATE DATABASE simples demonstrou:
- MDF 256 MB, mas growth 1 MB
- LDF 64 MB, growth 10%

Conclusão operacional: no SQL Server 2008 R2, não confiar no model para padronizar todas as propriedades físicas de arquivo. Especificar SIZE/FILEGROWTH no CREATE DATABASE ou corrigir explicitamente após restore.

## Rede
- SQL Browser: UDP 1434
- firewall: TCP 10401/10601 + UDP 1434
- portas dinâmicas desabilitadas
- ListenOnAllIPs habilitado

## Segurança
- Mixed Mode
- sa ativo no ambiente de referência, mas a skill NÃO deve assumir que isso é desejável em outros ambientes.
- IFI concedido à identidade do Database Engine.
