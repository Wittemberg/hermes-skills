# Hermes Skills Pack

Coleção de skills especializadas para **Hermes Agent** focadas em infraestrutura, redes (ISP/MSP), telecomunicações, virtualização, DevOps, automação e desenvolvimento.

---

## 📦 Categorias de Skills

### 🌐 Redes e Telecom (ISP / Datacenter)
- **MikroTik RouterOS** (`mikrotik-ops`): BGP, OSPF, VLANs, VRF, Firewall, WireGuard, EoIP, QoS e automação CLI.
- **pfSense / OPNsense** (`pfsense-ops`, `opnsense-ops`): Regras de firewall, NAT, OpenVPN, CARP/HA, multi-WAN.
- **Cisco & Huawei** (`cisco-ops`, `cisco-catalyst-switch-ops`, `huawei-ne-ops`, `huawei-s67xx-switch-ops`): Roteadores de borda/core, switches L2/L3.
- **OLTs GPON / EPON** (`olt-huawei-ops`, `olt-fiberhome-ops`, `olt-intelbras-epon-ops`, `olt-zte-c300-ops`, `olt-vsol-ops`): Provisionamento e diagnóstico de ONUs/ONTs.
- **Wireless & Outros** (`ubiquiti-airmax-ops`, `mimosa-wireless-ops`, `tplink-omada-gateway-ops`, `datacom-dmos-ops`, `trendnet-switch-ops`).

### 🖥️ Virtualização e Servidores
- **Proxmox VE** (`proxmox-ops`, `proxmox-storage-and-migration`, `proxmox-vm-migration-script`, `proxmox-vm-nat-dhcp`): Cluster, storage ZFS/Ceph, migração e rede.
- **VMware / Hyper-V** (`vmware-ops`, `hyper-v-ops`): Gestão vSphere/ESXi e hypervisor Windows.
- **Windows Server & AD** (`active-directory-ops`, `windows-server-ssh-hermes`): Active Directory, GPO, DNS, SSH seguro.
- **Samba & NFS** (`samba-file-sharing-ops`): Compartilhamentos corporativos em rede/VPN.
- **SQL Server** (`sql-server-2008-production-dba`): Manutenção, backup, tuning e integridade.

### 🐳 Containers, DevOps & Cloud
- **Docker & Swarm** (`docker-ops`, `swarm-traefik-app-deploy`, `portainer-api-stacks`): Deploy de stacks, Traefik proxy reverso, Portainer API.
- **AWS** (`aws-compute`, `aws-networking`, `aws-storage`, `aws-security`, `aws-cdk`, `amazon-bedrock`, etc.): Suite completa de operações AWS.

### 📊 Monitoramento, Segurança & CFTV
- **Zabbix** (`zabbix-ops`): Monitoramento de redes e servidores, templates, triggers e SNMP.
- **CFTV IP** (`intelbras-cftv-ops`, `aitek-cftv-ops`): NVR, DVR, RTSP e streams.
- **Cofre & Segurança** (`secret-storage-design`, `cofre-hermes-ops`): Boas práticas e cofre de senhas.

---

## 🚀 Como Utilizar em Outro Hermes Agent

### Método 1: Clonar direto na pasta de skills do Hermes

No host do novo Hermes (Linux / Mac / Windows Subsystem):
```bash
# Clonar o repositório
git clone https://github.com/Wittemberg/hermes-skills.git /tmp/hermes-skills

# Copiar as skills para a pasta de runtime do Hermes
# Linux / macOS:
cp -r /tmp/hermes-skills/skills/* ~/.hermes/skills/

# Windows (Git Bash):
# cp -r /tmp/hermes-skills/skills/* ~/AppData/Local/hermes/skills/
```

### Método 2: Instalação seletiva
Você pode copiar apenas a categoria ou skill desejada para o seu diretório de skills:
```bash
# Exemplo: Apenas skills de MikroTik e Proxmox
cp -r /tmp/hermes-skills/skills/forumtelecom/mikrotik-ops ~/.hermes/skills/forumtelecom/
cp -r /tmp/hermes-skills/skills/forumtelecom/proxmox-ops ~/.hermes/skills/forumtelecom/
```

---

## 📄 Licença
MIT License - sinta-se livre para usar e adaptar no seu Hermes Agent.