
import sys
import csv
import json
import argparse
from datetime import datetime


def system_config(cfg): 
    out = []

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!!! System config !!!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    out.append("hostname " + cfg['system']['hostname'])
    out.append("ip domain-name " + cfg['system']['domain'])

    if cfg['system']['domain_lookup'] == False:
        out.append("no ip domain lookup")
    
    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!!!!!!! Auth !!!!!!!!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    out.append("line vty 0 15\n  login local")
    out.append("  transport input ssh")

    out.append("line con 0")
    out.append("  login local")
    if cfg['system']['logging_sync'] == True :
        out.append("  logging sync")
    if cfg['system']['cons_timeout'] == False:
        out.append("  exec timeout 0 0")
    out.append("exit\n!")

    if cfg['system']['password_encryption'] == True:
        out.append("service password encryption")

    out.append("banner login # " + cfg['system']['banner_login'] + "#")
    out.append('username admin priv 15 secret ' + cfg['system']['admin_password'])

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!! Services config !!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    if cfg['system']['ssh_enable'] == True:
        out.append("crypto key generate rsa general-keys modulus " + cfg['system']['rsa_modulus'] + "\n!")
        out.append("ip ssh version 2\nip ssh auth retries " + cfg['system']['ssh_retries'] + "\nip ssh time-out " + cfg['system']['ssh_timeout'])   

    if cfg['system']['https_server'] == True:
        out.append("ip http secure-server")
    else:
        out.append("no ip http secure-server")

    if cfg['system']['ip_routing'] == True:
        out.append("ip routing")

    if cfg['system']['ipv6_routing'] == True:
        out.append("ipv6 unicast-routing")
    
    out.append("spanning-tree mode " + cfg['system']['stp_mode'] + '\n'
        "spanning-tree vlan 1-4094 priority " + cfg['system']['stp_priority'] + '\n'
        "spanning-tree port type edge " + cfg['system']['stp_edge'])

    out.append('\n')

    return out

def vlan_config(cfg, vlan_file):
    out = []

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!!!! Vlan config !!!!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    with open(vlan_file, 'r') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',')

        for row in reader:
            out.append("vlan " + row['id'])
            out.append("  name "  + row['name'])
            out.append("  state " + row['state'])

    out.append("  exit\n")
    return out 

def svi_config(cfg, svi_file):
    out = []

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!!!! SVI config !!!!!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    with open(svi_file, 'r') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',')

        for row in reader:
            out.append("interface vlan " + row['id'])
            out.append("  description " + row['description'])
            out.append("  ip address " + row['ipv4_addr'] + ' ' + row['ipv4_subn'])
            
            if not row['ipv6_local']:
                out.append("  ipv6 address autoconfig")
            else: 
                out.append("  ipv6 address " + row['ipv6_local'] + ' link-local')
            out.append("  ipv6 address " + row['ipv6_global'])


            if row['hsrp_ipv4']:
                out.append("  standby " + row['id'] + " ip " + row['hsrp_ipv4'])
                if row['hsrp_primary'] == "TRUE":
                    out.append("  standby " + row['id'] + " priority 50")
                    out.append("  standby " + row['id'] + " preempt")
                else: 
                    out.append("  standby " + row['id'] + " priority 150")
            if row['dhcp_relay']:
                out.append("  ip helper address " + row['dhcp_relay'])
            out.append("  no shutdown\n!")
    out.append('exit\n')
    return out

def matrix_config(cfg, matrix_file):
    out = []

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!! Connectivity matrix !!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    with open(matrix_file, 'r') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',')

        port_channels_configured = []

        for row in reader:
            # interface config
            out.append("interface " + row['From Port Number'])
            out.append("  description " + row['To Device Name'] + " " + row['To Port Number'])
            out.append("  switchport")
            if row['Access / Trunk'] == 'access':
                out.append("  switchport mode access\n  switchport access vlan " + row['Vlans'])
            if row['Access / Trunk'] == 'trunk':
                out.append("  switchport mode trunk")
                out.append("  switchport trunk allowed vlan " + row['Vlans'])
            if row['Port Channel'] != '':
                out.append(f"  channel-group {row['Port Channel'].lower().replace('po','')} mode active")
            if row['Access / Trunk'] != '':
                out.append("  no shutdown\n!")
            if row['Access / Trunk'] == '':
                out.append("  shutdown\n!")
            
            # port channel config    
            if row['Port Channel'] != '' and not row['Port Channel'].lower().replace('po','') in port_channels_configured:
                port_channels_configured.append(row['Port Channel'].lower().replace('po',''))

                out.append("interface " + row['Port Channel'].lower())
                out.append("  vpc " + row['Port Channel'].lower().replace('po',''))
                out.append("  description " + row['To Device Name'])
                out.append("  switchport")
                if row['Access / Trunk'] == 'access':
                    out.append("  switchport mode access\n  switchport access vlan " + row['Vlans'])
                if row['Access / Trunk'] == 'trunk':
                    out.append("  switchport mode trunk")
                    out.append("  switchport trunk allowed vlan " + row['Vlans'])
                if row['Access / Trunk'] != '':
                    out.append("  no shutdown\n!")
                
    out.append("exit\n")
    return out

def prefix_list_config(cfg): 
    out = []
    out.append('\n')

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!! Prefix-list config !!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    prefix_lists = cfg['prefix-lists']

    for plist in prefix_lists:
        out.append('ip prefix-list ' + plist['name'] + ' seq ' + plist['seq'] + ' ' + plist['action'] + ' ' + plist['network'])
    
    return out


def route_map_config(cfg):
    out = []
    out.append('\n')

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!! Route-map config !!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    route_maps = cfg['route-maps']

    for rmap in route_maps:
        out.append('route-map ' + rmap['name'] + ' ' + rmap['action'] + ' ' + rmap['seq'])
        if rmap['match']:
            out.append('  match ' + rmap['match'])
        if rmap['set']:
            out.append('  set ' + rmap['set'])

    return out

def routing_config(cfg): 
    out = []
    out.append('\n')

    out.append(
        '\n' + 
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n' +
        '!!!!! Routing config !!!!!\n' +
        '!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    )

    for route in cfg['static']['static_routes']:
        out.append('ip route ' + route)
    out.append('!\n')
    return out 

def routing_config_eigrp(cfg):
    out = []

    out.append('router eigrp ' + cfg['system']['hostname'].upper())
    out.append('  address-family ipv4 unicast autonomous-system ' + cfg['eigrp']['eigrp4_asn'] +
        '\n    eigrp router-id ' + cfg['eigrp']['eigrp4_rid']
    )
    
    for network in cfg['eigrp']['eigrp4_networks']:
        out.append('    network ' + network)

    out.append('    af-interface default' +
        '\n      passive-interface' +
        '\n      exit-af-interface'
    )

    for network in cfg['eigrp']['eigrp4_interfaces']:
        out.append('    af-interface ' + network + 
            '\n      no passive interface' +
            '\n      exit-af-interface'
        )
    if cfg['eigrp']['eigrp4_redist_static'] == True:
        out.append('    topology base' +
            '\n      redistribute static' + 
            '\n      exit'
        )
    out.append('    exit-address-family\n  exit\n!')
    

    if cfg['eigrp']['eigrp6_enable'] == True:
        out.append('router eigrp ' + cfg['system']['hostname'].upper())
        out.append('  address-family ipv6 unicast autonomous-system ' + cfg['eigrp']['eigrp6_asn'] +
            '\n    eigrp router-id ' + cfg['eigrp']['eigrp6_rid']
        )

        out.append('    af-interface default' +
            '\n      passive-interface' +
            '\n      exit-af-interface'
        )

        for interface in cfg['eigrp']['eigrp6_interfaces']:
            out.append('    af-interface ' + interface + 
                '\n      no passive interface' +
                '\n      exit-af-interface'
            )
        if cfg['eigrp']['eigrp6_redist_static'] == True:
            out.append('    topology base' +
                '\n      redistribute static' + 
                '\n      exit'
            )
        out.append('    exit-address-family\n  exit\n!')
    return out 

def routing_config_ospf(cfg): 
    out = []
    out.append('\n')

    out.append('router ospf ' + cfg['ospf']['ospf_process'] +
        '\n  router-id ' + cfg['ospf']['ospf4_rid']
    )

    if cfg['ospf']['ospf4_redist_static'] == True:
        out.append('  redistribute static')

    for area in cfg['ospf']['areas']:
        out.append('\n! --' + ' area ' + area + ' enabled interfaces:')
        interfaces = cfg['ospf']['areas'][area]
        for int in interfaces:
            out.append('interface ' + int)
            out.append('  ip router ospf ' + cfg['ospf']['ospf_process'] + ' area ' + area) 
    out.append('  exit\n!\n')
    return out

def routing_config_bgp(cfg): 
    out = []
    out.append('\n')

    out.append('router bgp ' + cfg['bgp']['asn'] +
        '\n  bgp log-neighbor-changes '
    )

    networks = cfg['bgp']['networks']
    groups = cfg['bgp']['neighbors']

    for net in networks:
        out.append('  network ' + net
    )

    for group in groups:
        remote_as = cfg['bgp']['neighbors'][group]['remote-as']
        password = cfg['bgp']['neighbors'][group]['password']
        version = password = cfg['bgp']['neighbors'][group]['version']
        timers = password = cfg['bgp']['neighbors'][group]['timers']

        route_map_in = cfg['bgp']['neighbors'][group]['route-map-in']
        route_map_out= cfg['bgp']['neighbors'][group]['route-map-out']
        prefix_list_in = cfg['bgp']['neighbors'][group]['prefix-list-in']
        prefix_list_out = cfg['bgp']['neighbors'][group]['prefix-list-out']

        out.append(
            '  neighbor ' + group + ' peer-group' + '\n' +
            '  neighbor ' + group + ' remote-as ' + remote_as + '\n' +
            '  neighbor ' + group + ' password ' + password + '\n' +
            '  neighbor ' + group + ' version ' + version + '\n' +
            '  neighbor ' + group + ' timers ' + timers + '\n' +
            '  neighbor ' + group + ' ISP1 soft-reconfiguration inbound' + '\n' +
            '  neighbor ' + group + ' prefix-list ' + prefix_list_out + ' out' + '\n' +
            '  neighbor ' + group + ' prefix-list ' + prefix_list_in + ' in' + '\n' +
            '  neighbor ' + group + ' route-map ' + route_map_out + ' out' + '\n' +
            '  neighbor ' + group + ' route-map ' + route_map_in + ' in'
        )

    for group in groups:
        for peer in cfg['bgp']['neighbors'][group]['peers']:
            out.append('  neighbor ' + peer['address'] + ' peer-group ' + group)



    out.append('  exit\n!\n')
    return out

def main():
    ar = argparse.ArgumentParser()
    ar.add_argument("--config",
        help="config path",
        default='./config/default'
    )
    args = ar.parse_args()


    config_file = args.config + '/config.json'
    vlan_file = args.config + '/vlan.csv'
    matrix_file = args.config + '/matrix.csv'
    svi_file = args.config + '/svi.csv'

    f = open(config_file,'r')
    cfg = json.load(f)
    f.close()
    # print(json.dumps(cfg, indent=4, sort_keys=False))

    now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    output_file = []
    output_file.append([
        '!!!!!! Configuration script for device ' + cfg['system']['hostname'], 
        f'!!!!!! Generated on {now}\n\n',
        'configure terminal\n'
    ])
    
    if cfg['base']['system']: output_file.append(system_config(cfg))
    if cfg['base']['vlan']: output_file.append(vlan_config(cfg, vlan_file))
    if cfg['base']['svi']: output_file.append(svi_config(cfg, svi_file))
    if cfg['base']['matrix']: output_file.append(matrix_config(cfg, matrix_file))
    if cfg['base']['prefix-list']: output_file.append(prefix_list_config(cfg))
    if cfg['base']['route-map']: output_file.append(route_map_config(cfg))
    if cfg['base']['routing']: output_file.append(routing_config(cfg))
    if cfg['base']['routing_eigrp']: output_file.append(routing_config_eigrp(cfg))
    if cfg['base']['routing_ospf']: output_file.append(routing_config_ospf(cfg))
    if cfg['base']['routing_bgp']: output_file.append(routing_config_bgp(cfg))

    output_file.append(['\ndo copy run start'])

    output_file_name = "output/" + cfg['system']['hostname'] + f"-{now}.txt"
    with open (output_file_name, 'a') as output:
        for line in output_file: 
            output.write("\n".join(line))
    
if __name__ == "__main__":
    main()
