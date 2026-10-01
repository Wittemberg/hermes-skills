---
name: tplink-omada-gateway-ops
description: "TP-Link Omada gateways ER605/TL-R605: acesso, config, VPN."
version: 0.1.0
author: Wittemberg, Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tp-link, omada, er605, roteador, vpn, firmware]
    category: forumtelecom
---

# TP-Link Omada gateway (ER605 / TL-R605)

Operação de gateways Omada em modo standalone e adotado: acesso, atualização de firmware, backup, VPN e roteamento. Cobre a linha ER605/TL-R605; outros modelos Omada compartilham a interface, mas exigem confirmação de firmware e recursos por modelo.

## Quando usar

- Acessar, auditar ou configurar um ER605/TL-R605 como borda.
- Atualizar firmware, salvar backup ou recuperar acesso.
- Configurar VPN (OpenVPN, IPsec), NAT, ACL ou multi-WAN.
- Não usar para: switches Omada, EAPs ou o Omada Controller em si.

## Identificação obrigatória antes de qualquer mudança

A versão de hardware determina o firmware; v1 e v2 têm kernels e imagens **incompatíveis**. Leia a etiqueta (`Ver 1.0`) ou `Status > System Status` na web UI. Confirme também o modo atual: standalone versus adotado por controller. Em modo adotado, a configuração local fica somente leitura e as mudanças são feitas no controller.

## Acesso

1. Endereço padrão de fábrica conforme a etiqueta do próprio equipamento. Já em produção, use o IP de gerência real.
2. Primeiro login exige definir credenciais próprias. Nunca deixar padrão em equipamento de borda.
3. Descoberta quando o IP é desconhecido: `terminal(command="ip neigh")` no mesmo segmento, varredura com `nmap -sn`, ou MAC da etiqueta comparado à tabela ARP. Um gateway sem rota conhecida pode exigir ligação direta a um LAN com IP estático no PC.
4. Sem HTTPS confiável na LAN, trate a sessão web como sensível: acesso por rede administrativa, nunca pela WAN.
5. Credenciais: consulte `cofre-hermes-ops`. Não digite senha em comando de terminal nem registre em arquivo de trabalho.

## Firmware

- Origem legítima: Omada Download Center do próprio fabricante, na página do modelo e da versão de hardware. Baixe o ZIP, extraia o `.bin` e confira o tamanho.
- Verifique a versão mínima exigida na release note antes de aplicar; saltos a partir de firmware muito antigo podem exigir etapa intermediária.
- Upload em `System Tools > Firmware Upgrade` (standalone). O equipamento reinicia e fica indisponível por alguns minutos: trate como janela.
- Faça backup da configuração antes (`System Tools > Backup & Restore`) e guarde fora do equipamento.
- Backup de firmware antigo geralmente **não** é restaurável em versão mais nova, e downgrade pode ser bloqueado. Não conte com rollback silencioso.
- Releases de segurança não detalham as falhas corrigidas; ausência de detalhe não significa risco baixo.

## VPN

- Recursos de OpenVPN nesta linha evoluíram por firmware (modos de autenticação e modo Full chegaram em versões mais recentes). Confirme os modos disponíveis na versão instalada antes de prometer topologia.
- Para dar acesso a uma LAN doméstica atrás de CGNAT ou IP dinâmico, prefira o **gateway como cliente** conectando a um servidor com IP público estável. Isso dispensa porta aberta e DDNS na ponta doméstica.
- Em servidor com OpenVPN, o cliente precisa de rota para a LAN remota (`iroute` no `client-config-dir`) e de rota de retorno no gateway. Sem os dois lados, o túnel sobe mas o tráfego para a LAN não passa.
- Sobreposição de sub-redes entre as pontas quebra o roteamento. Verifique antes de gerar certificados.
- O gateway não suporta WireGuard nesta linha. Não ofereça essa opção como se fosse nativa.

## Servidor OpenVPN em container LXC

OpenVPN exige o dispositivo `/dev/net/tun` dentro do container. Em LXC não privilegiado o nó costuma não existir, e criá-lo internamente falha mesmo com `CAP_MKNOD` aparente. A liberação é feita no **host Proxmox**, em `/etc/pve/lxc/<CTID>.conf`, e exige reiniciar o container — ação disruptiva que precisa de confirmação:

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

A presença de uma interface WireGuard ativa **não** comprova que TUN esteja disponível: são caminhos diferentes no kernel. Verifique com uma abertura real de `/dev/net/tun` via `ioctl` TUNSETIFF, não apenas com `ls`.

### easy-rsa 3: armadilhas que quebram o build

- `EASYRSA_REQ_CN` em `vars` faz `build-server-full` e `build-client-full` abortarem com "does not support setting an external commonName". Defina o CN apenas no `build-ca`, ou remova a variável antes de emitir certificados.
- Um `set -e` em bloco encadeado com redirecionamento para `/dev/null` esconde exatamente esse erro: rode os subcomandos separadamente e leia a saída.

### Valide o servidor com um cliente real

Subir `tun0` e ver `Initialization Sequence Completed` no **servidor** não prova que um cliente autentica. Teste com o próprio `.ovpn` apontando para `127.0.0.1`, em device separado:

```bash
openvpn --config teste.ovpn --dev tuntest --log teste.log --daemon
```

Com `ccd-exclusive`, um cliente sem arquivo correspondente em `client-config-dir` recebe `AUTH_FAILED` — sem erro de certificado, o que engana. Crie o arquivo com o **nome exato do CN** antes de testar. Sucesso real = IP do túnel na interface do cliente **e** o CN listado em `status.log` do servidor. Apague o `.ovpn` de teste depois: ele contém a chave privada do cliente.

## Armadilhas

- Aplicar imagem de v2 em hardware v1 corrompe o equipamento.
- Em modo adotado, mudanças locais são descartadas ou ignoradas; verifique o modo antes de investigar "configuração que não salva".
- ACL com destino `Me` afeta o acesso à própria interface de gerência: uma regra errada tranca o administrador para fora.
- Reset de fábrica apaga toda a configuração e é irreversível sem backup. Peça confirmação explícita.
- Alterar a rede LAN do gateway derruba a própria sessão de gerência. Planeje o novo endereço antes.

## Verificação

Após qualquer mudança, confirme com leitura, não por suposição: versão em `Status > System Status`, estado das WANs, tabela de rotas, e — havendo VPN — status do túnel em ambas as pontas mais um teste real de alcance a um host da LAN remota. Registre o que foi testado e o que não pôde ser testado.
