---
name: proxmox-storage-and-migration
description: Use when preparing Proxmox storage or VM migrations.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [proxmox, storage, lvmthin, backup, vzdump, migration]
    related_skills: [proxmox-ops, proxmox-vm-migration-script]
---

# Proxmox storage e migração

Skill de classe para operações que combinam diagnóstico de storage Proxmox, preparação de espaço temporário e migração de VMs KVM.

## Ordem obrigatória

1. Identifique o nó correto antes de alterar qualquer coisa.
2. Faça diagnóstico somente leitura do host, LVM, storages, VMs e discos.
3. Prefira um thin LV temporário para backups quando o thin-pool tem capacidade física disponível.
4. Só considere reduzir/reconstruir um thin-pool depois de esgotar a alternativa de staging e preservar metadata/configurações.
5. Valide o dump e o destino antes do restore.
6. Restaure a VM desligada e valide o resultado externamente.

## Pós-reboot, limpeza e reaproveitamento de storage ZFS

Quando a missão incluir remover cargas, limpar logs, reaproveitar discos e reservar um dataset, use esta ordem para não confundir configuração ausente com dados apagados:

1. Confirme o pós-reboot com `uptime`, `uname -r` e `pveversion`; inventarie `qm list`, `pct list` e `pvesm status`.
2. Para cada storage afetado, confronte `pvesm list <storage>` e `/etc/pve/storage.cfg` com o conteúdo físico no caminho configurado (`find <path> -xdev ...`), além de `zfs list -t all`/snapshots. Remover VMs/configuração ou storage não implica que os dumps foram apagados. Verifique a cópia externa na AWS antes de destruir arquivos locais; não considere upload completo apenas porque o usuário o descreveu como em andamento/concluído sem uma evidência acessível do destino. Obtenha autorização explícita para exclusão dos dados remanescentes.
3. Na limpeza ordinária, quantifique `journalctl --disk-usage` e `du -xhd2 /var/log /var/cache/apt/archives` antes/depois. Preserve logs atuais e aplique retenção, por exemplo `journalctl --rotate --vacuum-time=30d`, e limpe só o cache baixado com `apt-get clean`; não trunque ou remova `/var/log` em massa. Relate o espaço realmente liberado, mesmo quando vacuum remove 0 B.
4. Antes de escrever num NVMe, correlacione serial/modelo por `lsblk`, `/dev/disk/by-id`, `zpool status -P`, `findmnt` e `wipefs -n`; confirme que o alvo está vazio, sem partições/mounts/assinaturas e não pertence a pool/LVM. Revalide o serial imediatamente antes de alterar. SMART e temperatura orientam o risco de um resilver.
5. Para espelhar um pool de disco único sem descartar datasets, use `zpool attach <pool> <membro-existente> /dev/disk/by-id/<disco-alvo>` — não recrie o pool e não use `zpool add`, que adiciona outro vdev em vez de espelhar o atual. Use ID persistente, não `nvme0n1`/`nvme1n1` volátil. Valide com `zpool status -P`; diferencie “mirror configurado/resilver em progresso” de “resilver concluído”, confirme erros zero antes de declarar redundância íntegra e evite reboot/carga desnecessária durante a reconstrução.
6. Para `/LOCAL_BKP` com capacidade reservada/limitada no pool, prefira um dataset ZFS dedicado: confirme dataset e mountpoint ausentes e espaço livre; então `zfs create -o mountpoint=/LOCAL_BKP -o quota=1T -o reservation=1T <pool>/LOCAL_BKP`. Quota limita o uso e reservation retira esse espaço da disponibilidade dos demais datasets; valide `findmnt -T /LOCAL_BKP`, `zfs get mountpoint,quota,reservation <dataset>`, `zfs list` e `df -hT`. Isso não cadastra por si só storage no Proxmox; só edite `storage.cfg` se solicitado.
7. Revalide dados preservados, backups locais, mountpoints, estado/resilver ZFS, storages cadastrados e VMs/CTs. Relate resíduos/backups remanescentes, storages vazios e upload AWS não verificado; não os chame de apagados/limpos quando só a configuração foi removida.

## Diagnóstico do nó correto

Execute no host que realmente contém as VMs:

```bash
clear
hostname
pvs
vgs
lvs -a -o lv_name,vg_name,lv_size,pool_lv,data_percent,metadata_percent,lv_attr
pvesm status
cat /etc/pve/storage.cfg
qm list
for vm in $(qm list | awk 'NR>1 {print $1}'); do
  echo "===== VM $vm ====="
  qm config "$vm" | grep -E '^(ide|sata|scsi|virtio|efidisk|tpmstate)'
done
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
```

Confirme `hostname`, VMIDs, storage ativo, espaço físico e caminho real do disco antes de prosseguir. Não deduza o nó pelo nome ou pelo IP de outro host.

## Staging temporário em LVM-thin

Quando `/var/lib/vz` estiver cheio e `local-lvm` tiver margem física, crie um thin LV temporário. Dimensione o volume virtual (`-V <TAMANHO>`) de acordo com a capacidade total do thin-pool e o tamanho das VMs (por exemplo, 100G em pools de ~130G ou 400G em pools de ~800G):

```bash
lvcreate -V 100G -T pve/data -n backup-temp
mkfs.ext4 -L BACKUP-TEMP /dev/pve/backup-temp
mkdir -p /mnt/backup-temp
echo "/dev/mapper/pve-backup--temp /mnt/backup-temp ext4 defaults 0 2" >> /etc/fstab
mount /mnt/backup-temp
pvesm add dir backup-temp --path /mnt/backup-temp --content backup --is_mountpoint 1
pvesm status
df -hT /mnt/backup-temp
lvs pve/data -o lv_name,lv_size,data_percent,metadata_percent
```

Antes da criação, salve `pvesm status`, `/etc/pve/storage.cfg`, `vgs` e `lvs` em diretório timestampado. O thin LV não reserva todo o espaço físico imediatamente; acompanhe `data_percent` e o filesystem durante os backups. Fixar o ponto de montagem no `/etc/fstab` e registrar com `--is_mountpoint 1` no Proxmox impede que backups gravem silenciosamente na partição raiz `/` caso o filesystem seja desmontado ou após reinicialização.

Não use o filesystem `local` quase cheio para `vzdump` quando houver staging dedicado. Não remova `backup-temp` enquanto houver backup único nele.

## Backup e seleção de dump

Depois de validar `pvesm status`, `df` e `lvs`, gere os backups no staging:

```bash
vzdump <VMID> --storage backup-temp --mode stop --compress zstd
```

Para uma migração com `--no-backup`, apresente antes data, caminho, tamanho e hash do dump reutilizado. Não trate apenas o nome do arquivo como validação; confirme que o VMID corresponde ao pedido.

## Ajuste do script de migração

Antes de editar `/root/migrar_vm_unificado.sh`, faça cópia timestampada e leia os arrays `HOST`, `PORT`, `DUMP_DIR`, `DEST_STORAGE`, `SRC_BKP_STORAGE` e `SRC_FALLBACK_DUMP`.

Para o nó de backup `srv06`, quando o staging estiver em `/mnt/backup-temp`, o mapeamento deve ser:

```bash
DUMP_DIR[srv06]="/mnt/backup-temp/dump"
SRC_BKP_STORAGE[srv06]="backup-temp"
SRC_FALLBACK_DUMP[srv06]="/mnt/backup-temp/dump"
```

Valide com:

```bash
bash -n /root/migrar_vm_unificado.sh
sha256sum /root/migrar_vm_unificado.sh
```

Se distribuir o script a outros nós, compare SHA-256 depois da cópia. Preserve a chave SSH em modo `600` e valide apenas o fingerprint.

## Migração com dump existente

Valide origem, destino, VMID livre, storage de restore e compatibilidade de máquina/QEMU. Execute no nó de origem ou no nó que contém o dump:

```bash
/root/migrar_vm_unificado.sh <VMID> --from srv06 --to srv07 --no-backup
```

O script transfere o dump por `rsync` e restaura no storage configurado do destino. Não execute o script no destino.

Depois valide no destino:

```bash
qm status <VMID>
qm config <VMID>
pvesm list local-lvm --vmid <VMID>
lvs -o lv_name,lv_size,lv_attr,data_percent,metadata_percent | grep "vm-<VMID>"
qm showcmd <VMID> --pretty >/dev/null
```

A VM restaurada deve permanecer desligada até autorização explícita, especialmente porque o script usa `--unique 0` e preserva MAC/identificadores de rede.

## Thin-pool: quando reduzir

Não use `lvreduce` comum em thin-pool: o LVM pode recusar a operação porque os blocos alocados não são necessariamente lineares. Não remova/recrie o pool enquanto os discos das VMs forem a única cópia.

Se a redução for indispensável, preserve `vgcfgbackup`, configurações das VMs e metadata; mantenha as VMs paradas; valide `thin_check`; use uma ferramenta de `thin_shrink` compatível com a versão instalada; e confirme que o novo limite comporta todos os blocos mapeados. O staging temporário é geralmente mais simples e menos arriscado quando há capacidade no próprio thin-pool.

## Pitfalls

- Leia `hostname`, `storage.cfg` e `qm list` no mesmo diagnóstico; isso evita operar no Proxmox errado.
- Separe capacidade lógica do thin LV de espaço físico do pool; o filesystem pode parecer livre enquanto `data_percent` cresce durante o backup.
- Não assuma que `--no-backup` representa o estado atual da VM; ele reutiliza um dump anterior.
- Não inicie a VM restaurada automaticamente; conflito de MAC/IP/serviço pode ocorrer.
- Verifique o hash do dump na origem e no destino quando a transferência for longa ou crítica.
- Não conclua pelo retorno do script sozinho; leia novamente `qm status`, `qm config`, storage e volume no destino.
- Sempre registre o ponto de montagem do staging temporário no `/etc/fstab` e use `--is_mountpoint 1` no Proxmox para evitar gravação acidental na partição raiz `/` se o volume for desmontado ou após reboot.
