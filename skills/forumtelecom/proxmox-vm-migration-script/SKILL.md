---
name: proxmox-vm-migration-script
description: "Migre VMs Proxmox com o script unificado. Use quando precisar mover, clonar ou migrar maquinas virtuais entre nos ou storages do Proxmox VE usando o script de migracao unificado."
version: 1.0.0
author: Wittemberg, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [proxmox, vm, migration, vzdump, qmrestore, rsync]
    related_skills: [proxmox-ops]
---

# Migração unificada de VMs Proxmox

Use `/root/migrar_vm_unificado.sh` para migrar VMs KVM entre os servidores Proxmox do Wittemberg. O script cria ou reutiliza um dump, transfere por rsync e restaura no storage do destino.

## When to Use / Quando usar

Use quando o usuário pedir para:

- migrar, mover ou copiar uma VM entre servidores Proxmox;
- restaurar uma VM em outro servidor usando o dump mais recente;
- enviar uma VM entre `awe-star-2`, `awe-star-bkp`, `awe-star-3` ou outro nó cadastrado no script.

Não use para:

- containers LXC;
- live migration em cluster;
- migração sem identificar origem, destino e VMID;
- apagar a VM original após a cópia sem uma confirmação separada e explícita.

## Regra obrigatória sobre backup

Antes de executar o script, pergunte sempre ao usuário qual modo deseja, mesmo que pareça óbvio:

1. `Com backup novo` — execução padrão, sem `--no-backup`; o script executa `vzdump --mode stop`, portanto a VM de origem será parada durante o backup.
2. `Usar --no-backup` — reutiliza o dump mais recente disponível; não garante que o dump represente o estado atual da VM.

Recomende `Com backup novo`. Nunca escolha `--no-backup` sozinho e nunca omita essa pergunta.

Depois da escolha, mostre o impacto e obtenha confirmação explícita antes da execução, pois o modo padrão interrompe a VM de origem.

## Localização e mapeamento atual

O script deve existir nos nós participantes em:

```text
/root/migrar_vm_unificado.sh
```

Mapeamentos conhecidos:

| ID | Servidor | IP | Porta SSH |
|---|---|---:|---:|
| `srv01` | não nomeado | `38.52.129.178` | `5822` |
| `srv02` | não nomeado | `204.157.108.210` | `5822` |
| `srv03` | não nomeado | `204.157.109.146` | `5822` |
| `srv04` | não nomeado | `38.211.129.114` | `5822` |
| `srv05` | `awe-star-2` | `177.136.234.203` | `5822` |
| `srv06` | `awe-star-bkp` | `141.11.72.2` | `5822` |
| `srv07` | `awe-star-3` | `185.135.159.226` | `5822` |
| `srv08` | `awe-star-3.2` | `177.136.235.99` | `5822` |
| `srv09` | `awe-star-4` | `177.136.235.98` | `5822` |

Atenção (out/2026): os aliases do ssh config local mudaram — `awe-star-3` hoje aponta para 177.136.235.99 (o antigo "3.2"); o IP legado 185.135.159.226 do antigo awe-star-3 está inacessível (porta 5822 recusada). O script no nó 177.136.235.99 foi corrigido: `SRC_BKP_STORAGE[srv07]=SSD_BACKUP` (antes apontava para `/mnt/backup-temp`, caminho obsoleto) e entrada `srv09` adicionada (`HOST=177.136.235.98`, `DUMP_DIR=/NVME_STORAGE/backup/dump`, `DEST_STORAGE=NVME_STORAGE`, zfspool `NVME_STORAGE/vmdata`, PVE 9.2, QEMU 11.0.3). Migração srv07→srv09 já executada com sucesso (VM 300 pfsense, dump de 1,6G, transferência a ~112 MB/s, restore como VMID 300). No awe-star-4 a `vmbr1` foi ativada (manual, sem IP) e a ISO do pfSense copiada para /var/lib/vz/template/iso/ para validar `qm showcmd`. Para trocar o VMID no destino: pare a VM do ID destino, `zfs rename` do zvol, `mv` do conf em /etc/pve/qemu-server/ e ajuste do disco no conf (padrão aplicado na conversão 400→401 do awe-star-4). Padrão de rede dos nodes AWE: `vmbr0` = WAN (IP do nó, gw 177.136.235.97, post-up `/sbin/iptables-restore /etc/iptables.rules` + pre-down save) e `vmbr1` = bridge interna sem IP onde o pfSense ancora a LAN — ao replicar em node novo, verifique se `/etc/iptables.rules` existe (no awe-star-4 não existia; gerado com `iptables-save`, validado com `iptables-restore --test`). Pertinências por nó preservadas: IP 10.10.2.253/24 (node .98) vs 10.10.2.1/24 comentado (node .99).

Cópia do pfSense para novo ambiente (padrão validado out/2026, awe-star-4): o `qmrestore` randomiza os MACs, mas o IP WAN/LAN vêm idênticos — reconfigurar ANTES de expor a WAN. Fluxo: (1) bootar a cópia com AMBAS as NICs na vmbr1 (isolada, sem conflito de ARP) + IPs temporários 192.168.168.250 e 192.168.169.250 no host; (2) acessar via túnel SSH do Hermes→node→pfSense (pfSense escuta na 5822; console via menu opção 8); (3) editar `/conf/config.xml` com `sed -i ''` (BSD) — IPs, hostname, VIPs, sub-rede LAN; máscara fica em `<subnet>N</subnet>` (28 = /28); (4) `rm -f /tmp/config.cache` e `reboot` (evitar `/etc/rc.reload_all` inline: tcsh rejeita `&>` — usar `reboot` para aplicar limpo); (5) revalidar banner/IPS, devolver net0 para vmbr0, `qm start`. Chave de acesso: a `KW_Kronic` já está autorizada no authorizedkeys do admin (fingerprint 5C7LTks6uEhBWwXn+9vuii00G+u8iKNohkcpezrnKqM) — SSH direto sem senha na 5822. Novo host: `pfsense-awe-star4` = 177.136.235.105:5822 (hostname pfSense4.awecloudsulution.cloud, LAN 192.168.169.1/24, VIPs .102/.106/.107/.108). Backups: /root/backups/pfsense-awe-star3/ (config original 20261005 e config-node4-adaptado-20261005).

Recursos aplicados no pfSense4 (out/2026): cert LE **firewallstar4.awecloudsolution.com** (o nome correto do node 4 — firewallstar3 = node 3/producao .103; SEMPRE consultar os registros na Route53 zona awecloudsolution.com ANTES de emitir cert para dominio AWE, o usuario ja mantem os A records la: firewallstar3->.103, firewallstar4->.105) via DNS-01 Route53 (conta 403052873442, certbot no Hermes) + VIP .102 (AWE-PWBi, VM 401 = 192.168.169.5 via DHCP) + NAT 8933->169.5:3389 + outbound NAT .5->.102 + WebGUI https://firewallstar4.awecloudsolution.com:8181. Licoes criticas pfSense 2.9: (1) `cert_import()` so preenche o array por referencia — o chamador precisa anexar em `$config['cert'][]`, senao o `ssl-certref` fica orfao e o boot regenera cert self-signed fallback; (2) funcoes de runtime (`interfaces_vip_configure`, etc.) nao ficam disponiveis via PHP CLI — para aplicar sem GUI, gravar config e rebootar; (3) trocar bloco `<cert>` in place (mesma refid) sobrevive a reboot; (4) tcsh rejeita `2>&1` e `&>` inline — redirecionar so stdout; (5) heredoc via pexpect corrompe arquivos — transferir via `fetch` HTTP com server temporario no vmbr1 (IP 192.168.169.250) e validar MD5; (6) apos VIP novo na WAN, o gateway upstream (.97) mantem ARP do IP antigo — o pfSense deve originar trafego com source = VIP (`ping -S VIP gw`) para renovar o cache; (7) `ssl-certref` apontado a mao exige `/etc/rc.restart_webgui`; (8) **DNS rebind**: ao expor a WebGUI (ou outro servico com Host check) por FQDN que resolve para IP da propria WAN, o pfSense bloqueia com "Potential DNS Rebind attack detected" — adicionar o FQDN em `$config['system']['webgui']['althostnames']` (separado por espaco se varios) + `/etc/rc.restart_webgui`. Fazer isso SEMPRE junto com a emissao/instalacao do cert + exposicao por hostname, nao depois do primeiro erro do usuario; (9) **reserva DHCP** por PHP CLI: criar entrada em `$config['dhcpd']['lan']['staticmap'][]` (campos mac/ipaddr/hostname/descr minimos) + `write_config()` + `services_dhcpd_configure()` (requer services.inc — o script `/etc/rc.restart_dhcpd` NAO existe no 2.9); validar no `/var/dhcpd/etc/dhcpd.conf` gerado (bloco `hardware ethernet ... fixed-address`). Reserva aplicada: SRV-PW-Bi (AWE-PWBi, MAC bc:24:11:2b:d1:c5) = 192.168.169.5.

Trate o próprio script como fonte de verdade. Releia os arrays `HOST`, `PORT`, `DUMP_DIR`, `DEST_STORAGE`, `SRC_BKP_STORAGE` e `SRC_FALLBACK_DUMP` antes de cada migração.

## Pré-requisitos

No nó de origem:

- `/root/migrar_vm_unificado.sh` executável;
- `/root/KP_Kronic.pem` com modo `600`;
- `vzdump` e `rsync` instalados;
- VMID existente e configuração legível;
- storage de backup ativo e espaço suficiente;
- acesso SSH ao destino pela porta cadastrada.

No destino:

- storage de restore ativo e com espaço suficiente;
- diretório de dump existente e gravável;
- VMID livre ou espaço para o próximo ID retornado pelo cluster;
- nenhum firewall bloqueando SSH/rsync.

## Procedimento

### 1. Descobrir origem, destino e VMID

Se qualquer um estiver ausente, pergunte ao usuário. Converta os nomes amigáveis para os IDs `srvNN` do script.

Critério: `VMID`, `FROM` e `TO` conhecidos e diferentes.

### 2. Inspeção somente leitura

No servidor de origem, execute pelo `terminal`:

```bash
clear
hostname
bash -n /root/migrar_vm_unificado.sh
qm status <VMID>
qm config <VMID>
pvesm status
df -hT
stat -c '%A %a %U:%G %s %n' /root/migrar_vm_unificado.sh /root/KP_Kronic.pem
```

Leia também o script atual antes de confiar nos mapeamentos. No destino, valide:

```bash
clear
hostname
hostname -f
getent hosts "$(hostname)"
pveversion -v
/usr/bin/kvm --version 2>&1 || qemu-system-x86_64 --version
pvesm status
qm status <VMID> 2>&1 || true
df -hT
```

Execute também `pveversion -v` e a consulta da versão do QEMU na origem. Compare `machine:`, `cpu:`, BIOS/UEFI, controladoras e dispositivos da VM com o suporte do destino. Se o destino for mais antigo que a origem ou não reconhecer o tipo de máquina salvo (por exemplo `pc-i440fx-X.Y+pveN`), pare antes do restore/start e proponha atualização do destino ou alteração explícita para um tipo compatível, sempre com backup da configuração. Nunca altere automaticamente o tipo de máquina ou CPU, pois isso pode mudar hardware apresentado ao guest.

O hostname do nó não pode resolver primeiro para `127.0.0.1`. O padrão esperado é `127.0.0.1 localhost.localdomain localhost` e `<IP_DO_NO> <FQDN> <HOSTNAME>`. Um `/etc/hosts` incorreto pode permitir que a VM inicie, mas quebrar o console noVNC/VNC proxy com `failed to create socket: Invalid argument`.

Critério: VM existe na origem; storages estão ativos; origem e destino têm espaço suficiente; versões e hardware virtual são compatíveis; `hostname -f` retorna o FQDN do nó e `getent hosts "$(hostname)"` retorna o IP real do nó, não loopback.

### 3. Perguntar obrigatoriamente sobre `--no-backup`

Use uma pergunta de escolha única:

- `Com backup novo` — recomendado;
- `Usar --no-backup` — reutilizar dump existente.

Se escolher `--no-backup`, descubra e apresente o dump que será reutilizado, incluindo data, tamanho e caminho. Se não existir dump compatível, pare e informe.

### 4. Confirmar impacto

Para backup novo, informe que `vzdump --mode stop` desligará/parará a VM durante a criação do dump. Obtenha confirmação explícita para executar a migração.

Para `--no-backup`, informe a data do dump e que alterações posteriores não estarão incluídas. Obtenha confirmação explícita.

### 5. Executar no nó de origem

Backup novo:

```bash
/root/migrar_vm_unificado.sh <VMID> --from <srvORIGEM> --to <srvDESTINO>
```

Reutilizando dump:

```bash
/root/migrar_vm_unificado.sh <VMID> --from <srvORIGEM> --to <srvDESTINO> --no-backup
```

Use timeout amplo. Não execute o script no destino: ele deve rodar no nó que contém a VM ou o dump de origem.

### 6. Verificar o resultado

Não confie apenas na mensagem final do script. No destino, execute:

```bash
clear
qm list
qm status <VMID_DESTINO>
qm config <VMID_DESTINO>
pvesm list <STORAGE_DESTINO> --vmid <VMID_DESTINO>
```

Confirme também:

- arquivo transferido no diretório de dump do destino;
- discos no storage esperado;
- interfaces, bridges, VLAN tags e MACs adequados ao destino;
- VM permanece desligada, salvo se o usuário tiver autorizado iniciar;
- origem não foi removida.

Antes de liberar a inicialização, rode no destino:

```bash
qm showcmd <VMID_DESTINO> --pretty >/dev/null
```

Se o usuário iniciar e a interface mostrar erro, diferencie as tarefas antes de concluir que o start falhou:

```bash
qm status <VMID_DESTINO> --verbose
pvesh get /nodes/$(hostname)/tasks --vmid <VMID_DESTINO> --limit 10 --source all --output-format json
journalctl --since "30 minutes ago" --no-pager -u pvedaemon -u qmeventd
```

`qmstart ... status OK` com `vncproxy ... failed to create socket: Invalid argument` significa que a VM iniciou e o defeito está no console/proxy, normalmente hostname ou `/etc/hosts`; não é evidência de incompatibilidade da VM. Corrija a resolução do hostname com backup do `/etc/hosts`, confirme `hostname -f`/`getent hosts` e teste novamente o endpoint VNC sem expor ticket ou certificado nos logs.

Se o VMID original já existir no destino, o script usa `/cluster/nextid`; capture e reporte o VMID realmente restaurado.

Critério: VM restaurada, configuração legível e volumes presentes no storage correto.

## Segurança

- Nunca execute `qm destroy`, remova dump ou apague a VM original como parte automática da migração.
- Nunca inicie a VM restaurada sem autorização quando houver risco de conflito de IP/MAC/serviço com a origem.
- Nunca exponha, imprima ou registre o conteúdo de `/root/KP_Kronic.pem`.
- A chave pode ser copiada entre servidores autorizados quando necessária; preserve proprietário `root:root`, modo `600` e valide somente o fingerprint.
- Faça backup timestampado do script antes de alterá-lo.
- Use `bash -n` e compare SHA-256 em todos os nós após atualizar o script.

## Armadilhas conhecidas

- `awe-star-bkp` usa o filesystem raiz para `/var/lib/vz/dump`; confirme espaço livre antes de receber ou criar dumps. Em uma verificação anterior havia apenas cerca de 5,9 GB livres, mas sempre meça novamente.
- `--no-backup` escolhe o dump mais recente encontrado, não necessariamente um dump validado pelo usuário.
- O modo padrão usa `vzdump --mode stop`; não é live migration.
- `StrictHostKeyChecking=no` está configurado no script legado; valide o destino por hostname/IP antes da execução.
- O script restaura com `--unique 0`, preservando identificadores de rede; não ligue origem e destino simultaneamente sem revisar conflitos.
- Se o storage configurado falhar, o script tenta o diretório fallback; confirme que esse caminho realmente pertence a um filesystem com espaço.

## Relatório final

Informe de forma objetiva:

- VMID de origem e VMID restaurado;
- origem e destino;
- modo escolhido: backup novo ou `--no-backup`;
- dump usado, tamanho e data;
- storage de destino;
- estado final da VM nos dois nós;
- validações realizadas;
- qualquer pendência antes de iniciar a VM restaurada.
