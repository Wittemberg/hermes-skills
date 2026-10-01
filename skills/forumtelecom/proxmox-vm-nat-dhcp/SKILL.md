---
name: proxmox-vm-nat-dhcp
description: Configure NAT e DHCP interno em nós Proxmox VE.
version: 1.1.0
author: TecnoTeam, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [proxmox, networking, dhcp, dnsmasq, iptables, nat, dnat]
    related_skills: [proxmox-ops]
---

# Proxmox VM NAT + DHCP

Configure uma bridge privada para VMs, DHCP com dnsmasq, roteamento IPv4, NAT de saída e DNAT opcional sem alterar a bridge pública existente. Trabalhe em camadas e valide cada uma antes de avançar.

## When to Use / Quando usar

Use quando VMs no Proxmox precisam:

- receber IPv4 privado automaticamente;
- compartilhar a Internet do nó;
- usar uma bridge interna, como `vmbr1`;
- receber redirecionamentos TCP/UDP individuais.

Não use sem adaptar quando:

- as VMs receberão IP público roteado;
- Proxmox SDN ou firewall já gerencia NAT;
- nftables, firewalld ou outro gerenciador é dono das regras;
- uplink, rota de gestão ou sub-rede privada ainda são desconhecidos.

## Regras de segurança

1. Comece somente com leitura e preserve a conectividade de gestão.
2. Nunca use `iptables -F`, `iptables -t nat -F` ou substitua `/etc/network/interfaces` às cegas.
3. Faça backup timestampado antes de editar rede, sysctl, dnsmasq ou persistência de firewall.
4. Adicione uma bridge privada; nunca reaproveite a bridge pública.
5. Verifique o backend real (`iptables-nft`, legacy ou nftables nativo) e quem gerencia as regras.
6. Não adicione regra equivalente já existente; use `iptables -C` para testar idempotência.
7. Não remova regra por número sem reler a chain imediatamente antes. Prefira exclusão pela regra exata.
8. Não persista regras antes de validar DHCP, Internet e contadores.
9. DNAT exige IP fixo ou reserva DHCP e serviço escutando na VM.
10. Não reinicie o serviço de rede inteiro por SSH. Prefira `ifup <bridge>` para bridge nova e use `ifreload -c` antes de qualquer reload.
11. Antes de uma mudança disruptiva, mostre impacto e obtenha confirmação explícita.

## Variáveis obrigatórias

Descubra ou obtenha aprovação para todos os valores; nunca presuma nomes, IPs ou portas.

```text
WAN_BRIDGE=vmbr0
LAN_BRIDGE=vmbr1
LAN_CIDR=10.10.10.0/24
LAN_GATEWAY=10.10.10.1
DHCP_START=10.10.10.100
DHCP_END=10.10.10.200
DNS1=1.1.1.1
DNS2=8.8.8.8
```

## Procedimento

### 1. Inventário somente leitura

Use `read_file` para `/etc/network/interfaces` e arquivos em `/etc/network/interfaces.d/`. Execute pelo `terminal`:

```bash
hostnamectl
pveversion -v
ip -br link
ip -br addr
ip route
ip rule
ip route get 1.1.1.1
bridge link

iptables --version 2>/dev/null || true
update-alternatives --display iptables 2>/dev/null || true
nft --version 2>/dev/null || true

sysctl net.ipv4.ip_forward
systemctl is-active pve-firewall 2>/dev/null || true
systemctl is-active nftables 2>/dev/null || true
systemctl is-active firewalld 2>/dev/null || true

iptables-save 2>/dev/null || true
nft list ruleset 2>/dev/null || true
ss -lntup
```

Confirme:

- bridge/IP/gateway públicos e NIC física;
- interface de saída mostrada por `ip route get 1.1.1.1`;
- sub-rede RFC1918 sem sobreposição com `ip route`, VPNs, VLANs ou cluster;
- gerenciador efetivo do firewall;
- ausência de serviço conflitante nas portas 53/67 e nas portas públicas de DNAT.

Critério: uplink, rota de gestão, backend de firewall e sub-rede privada livre estão identificados.

### 2. Backup

Crie um diretório próprio e copie apenas os arquivos existentes:

```bash
TS=$(date +%Y%m%d-%H%M%S)
BK="/root/backups/proxmox-vm-nat-dhcp/$TS"
mkdir -p "$BK"
cp -a /etc/network/interfaces "$BK/interfaces"
cp -a /etc/network/interfaces.d "$BK/interfaces.d" 2>/dev/null || true
cp -a /etc/sysctl.d "$BK/sysctl.d"
cp -a /etc/dnsmasq.conf /etc/dnsmasq.d "$BK/" 2>/dev/null || true
iptables-save > "$BK/iptables-save.txt" 2>/dev/null || true
nft list ruleset > "$BK/nft-ruleset.txt" 2>/dev/null || true
printf '%s\n' "$BK"
```

Critério: o caminho de backup foi exibido e contém a configuração anterior.

### 3. Bridge privada

Edite `/etc/network/interfaces` com `patch`, preservando tudo que já existe. Adicione uma única stanza adaptada:

```text
auto vmbr1
iface vmbr1 inet static
        address 10.10.10.1/24
        bridge-ports none
        bridge-stp off
        bridge-fd 0
```

Valide antes de ativar:

```bash
ifquery --check vmbr1
ifreload -c
```

Se a bridge for nova e não estiver ativa:

```bash
ifup vmbr1
ip -br addr show vmbr1
ip route show 10.10.10.0/24
```

`UNKNOWN` em bridge sem porta física pode ser normal.

Critério: a bridge possui o gateway privado e a rota conectada existe; rota default e IP de gestão continuam intactos.

### 4. Encaminhamento IPv4

Crie `/etc/sysctl.d/99-vm-routing.conf` com `write_file`:

```text
net.ipv4.ip_forward=1
```

Aplique somente esse arquivo e valide:

```bash
sysctl -p /etc/sysctl.d/99-vm-routing.conf
sysctl net.ipv4.ip_forward
```

Critério: retorno exato `net.ipv4.ip_forward = 1`.

### 5. DHCP com dnsmasq

Antes de instalar, confira se já existe servidor DHCP/DNS no nó. Se necessário:

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y dnsmasq
```

Crie `/etc/dnsmasq.d/proxmox-vmbr1.conf` com valores reais:

```text
# DHCP somente; evita disputar a porta DNS 53 do nó.
port=0
interface=vmbr1
bind-dynamic

dhcp-range=10.10.10.100,10.10.10.200,255.255.255.0,12h
dhcp-option=option:router,10.10.10.1
dhcp-option=option:dns-server,1.1.1.1,8.8.8.8
```

Se dnsmasq também deve fornecer DNS local, não use `port=0`; primeiro prove que a porta 53 está livre e configure upstreams explicitamente.

Valide antes do restart:

```bash
dnsmasq --test
systemctl restart dnsmasq
systemctl enable dnsmasq
systemctl is-active dnsmasq
journalctl -u dnsmasq -n 50 --no-pager
ss -lunp | grep -E ':(67)([[:space:]]|$)' || true
```

Critério: teste de sintaxe aprovado, serviço ativo e DHCP vinculado à bridge privada.

### 6. NAT de saída com iptables

Só siga se o inventário provar que iptables é o mecanismo correto. Use a interface de saída real de `ip route get`, que pode não ser a bridge esperada.

```bash
iptables -t nat -C POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE 2>/dev/null || \
iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE

iptables -C FORWARD -i vmbr1 -o vmbr0 -s 10.10.10.0/24 -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -i vmbr1 -o vmbr0 -s 10.10.10.0/24 -j ACCEPT

iptables -C FORWARD -i vmbr0 -o vmbr1 -d 10.10.10.0/24 \
  -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -i vmbr0 -o vmbr1 -d 10.10.10.0/24 \
  -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
```

Releia a chain e confirme que nenhuma regra `DROP`/`REJECT` anterior impede as regras adicionadas. Se impedir, não mude a ordem às cegas: identifique o dono da chain e proponha a inserção exata.

```bash
iptables -t nat -L POSTROUTING -n -v --line-numbers
iptables -L FORWARD -n -v --line-numbers
iptables-save -t nat
```

Critério: uma única regra MASQUERADE equivalente e caminho FORWARD efetivo.

### 7. Teste da VM

Conecte a NIC VirtIO da VM à bridge privada. Para diagnóstico inicial, não habilite uma nova opção de firewall na NIC até DHCP/NAT funcionar.

Na VM Linux:

```bash
ip -br addr
ip route
ping -c 4 10.10.10.1
ping -c 4 1.1.1.1
getent ahostsv4 google.com
```

No host:

```bash
readlink -f /var/lib/misc/dnsmasq.leases
cat /var/lib/misc/dnsmasq.leases 2>/dev/null || true
iptables -t nat -L POSTROUTING -n -v --line-numbers
iptables -L FORWARD -n -v --line-numbers
```

Critério: lease recebido, gateway/IP externo/DNS funcionam e os contadores aumentam.

### 8. Persistência

Instale somente depois dos testes. A instalação pode tentar salvar o estado atual; use modo não interativo e salve explicitamente após revisar:

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
netfilter-persistent save
systemctl is-enabled netfilter-persistent
iptables-save > /etc/iptables/rules.v4
```

Não misture esta persistência com regras equivalentes em `post-up`, Proxmox firewall, nftables nativo ou outro gerenciador.

Critério: regras persistidas uma vez, no mecanismo responsável pelo host.

## DNAT / Port forwarding

Primeiro registre o mapeamento assim:

```text
PROTOCOLO PUBLIC_IP:PORTA_EXTERNA -> VM_IP:PORTA_INTERNA
```

Pré-cheques:

```bash
ss -lntup
iptables -t nat -L PREROUTING -n -v --line-numbers
iptables -L FORWARD -n -v --line-numbers
```

Garanta IP estável da VM e ausência de conflito com serviço local. Para TCP:

```bash
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 53389 \
  -j DNAT --to-destination 10.10.10.118:3389 2>/dev/null || \
iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 53389 \
  -j DNAT --to-destination 10.10.10.118:3389

iptables -C FORWARD -i vmbr0 -o vmbr1 -p tcp -d 10.10.10.118 --dport 3389 \
  -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -i vmbr0 -o vmbr1 -p tcp -d 10.10.10.118 --dport 3389 \
  -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
```

Para UDP, use regras separadas com `-p udp`. Restringir origem com `-s <CIDR_CONFIAVEL>` é preferível sempre que possível.

Teste de uma rede realmente externa e acompanhe:

```bash
iptables -t nat -L PREROUTING -n -v --line-numbers
iptables -L FORWARD -n -v --line-numbers
```

Se o contador DNAT subir mas a conexão falhar, valide serviço na VM, firewall do guest, FORWARD e rota de retorno. Se o contador ficar zerado, valide IP público, protocolo, porta, upstream e interface de entrada.

Hairpin NAT para clientes da própria LAN não está incluído; só implemente após confirmar essa necessidade e a topologia DNS.

## Reserva DHCP

Leia a lease e obtenha o MAC real. Prefira IP reservado fora do pool dinâmico:

```text
dhcp-host=AA:BB:CC:DD:EE:FF,10.10.10.50
```

Valide e recarregue:

```bash
dnsmasq --test
systemctl restart dnsmasq
systemctl is-active dnsmasq
```

Critério: a VM renova sempre o mesmo endereço e ele não colide com o pool.

## Limpeza de regra errada ou duplicada

Nunca limpe chains inteiras. Leia `iptables-save`, reproduza a regra exata com `-D` no lugar de `-A`, remova uma ocorrência por vez e releia após cada lote. Como isso altera o firewall ativo, obtenha confirmação explícita antes de executar.

Exemplo de remoção exata:

```bash
iptables -t nat -D PREROUTING -i vmbr0 -p tcp --dport 43389 \
  -j DNAT --to-destination 10.10.10.113:3389
```

Só execute `netfilter-persistent save` depois da validação final.

## Verificação consolidada

```bash
echo '===== ENDERECOS E ROTAS ====='
ip -br addr
ip route
ip route get 1.1.1.1

echo '===== FORWARD ====='
sysctl net.ipv4.ip_forward

echo '===== DNSMASQ ====='
systemctl is-active dnsmasq
journalctl -u dnsmasq -n 20 --no-pager
cat /var/lib/misc/dnsmasq.leases 2>/dev/null || true

echo '===== NAT ====='
iptables -t nat -L PREROUTING -n -v --line-numbers
iptables -t nat -L POSTROUTING -n -v --line-numbers

echo '===== FILTER/FORWARD ====='
iptables -L FORWARD -n -v --line-numbers
```

Sucesso exige:

1. gestão pública e rota default preservadas;
2. bridge privada com gateway e rota conectada;
3. forwarding IPv4 ativo;
4. dnsmasq ativo e lease entregue;
5. VM alcança gateway, Internet por IP e DNS;
6. contadores MASQUERADE/FORWARD aumentam;
7. cada porta externa aponta para um único destino estável;
8. contadores DNAT aumentam em teste externo;
9. regras persistem no mecanismo correto.

Não reinicie o nó apenas para testar persistência em produção. Compare o arquivo persistido com o estado ativo e agende reboot controlado quando apropriado.

## Armadilhas

- `vmbr1` em estado `UNKNOWN` sem porta física não indica falha por si só.
- `iptables` pode ser frontend nft; não misture com regras nftables administradas separadamente.
- Proxmox firewall pode bloquear FORWARD mesmo com regras aparentes; inspecione chains e configuração do Datacenter/nó/VM.
- Uma regra `-A` após um `DROP` nunca será atingida.
- DNAT para lease dinâmica quebra quando o IP muda.
- Testar o IP público a partir da mesma LAN pode exigir hairpin NAT ou split DNS.
- `port=0` torna dnsmasq servidor DHCP apenas; os clientes usam os DNS informados na opção 6.
- O nome da interface de saída deve vir da rota real, não de convenção.