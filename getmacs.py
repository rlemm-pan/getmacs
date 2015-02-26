#!/usr/bin/python

import os
import sys
import getpass
import time
import argparse
import yaml
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import cpu_count
import traceback

from jnpr.junos import Device
from jnpr.junos.exception import RpcError
from jnpr.junos.factory.factory_loader import FactoryLoader


YamlTable = \
    """---
    EthSwitchTable:
      rpc: get-ethernet-switching-table-information
      args:
        detail: True
      item: ethernet-switching-table/mac-table-entry[mac-type='Learn' or mac-type='Learn(L)']
      key:
        - mac-address
        - mac-interface
      view: EthSwitchView

    EthSwitchView:
      fields:
        vlan_name: mac-vlan
        tag: mac-vlan-tag
        mac_address: mac-address
        interface: mac-interface

    EthSwitchInterfaceTable:
      rpc: get-ethernet-switching-interface-information
      item: interface/interface-vlan-member-list/interface-vlan-member
      key:
        - ../../interface-name
      view: EthSwitchInterfaceView

    EthSwitchInterfaceView:
      fields:
        interface: ../../interface-name
        vlan_name: interface-vlan-name
        tag: interface-vlan-member-tagid
        interface_tag: interface-vlan-member-tagness

    VlanTable:
      rpc: get-vlan-information
      args:
        extensive: True
      item: vlan[vlan-l3-interface]
      key:
        - vlan-l3-interface
      view: VlanView

    VlanView:
      fields:
        l3_interface: vlan-l3-interface
        l3_interface_address: vlan-l3-interface-address
        vlan_name: vlan-name
        vlan_tag: vlan-tag

    ArpTable:
      rpc: get-arp-table-information
      args:
        no_resolve: True
      item: arp-table-entry
      key:
        - mac-address
      view: ArpView

    ArpView:
      fields:
        mac_address: mac-address
        ip_address: ip-address
        l3_interface: interface-name"""

globals().update(FactoryLoader().load(yaml.load(YamlTable)))

results = ''
test = []
macaddr = ''
ipaddr = ''
uname = ''
upass = ''
cert = ''
exlinks = ''
onedevice = ''
start_time = time.time()
untagged_port = 'Device has a possible connection to this port'

parser = argparse.ArgumentParser(add_help=True)

parser.add_argument("-x", action="store",
                    help="Exclude Interface")

parser.add_argument("-d", action="store",
                    help="Specify Device")

parser.add_argument("-i", action="store",
                    help="Find info with IP-Address")

parser.add_argument("-l", action="store",
                    help="Specify file containing Device-IP's (example:  -l filename.txt).  If not specified, iplist.txt will be used")

parser.add_argument("-m", action="store",
                    help="Find info with MAC-Address")

parser.add_argument("-u", action="store",
                    help="Login with username")

parser.add_argument("-p", action="store",
                    help="Login with password")

parser.add_argument("-c", action="store_false",
                    help="Login with Device Certificate")

args = parser.parse_args()

if args.c is False:
    cert = 1
if args.d:
    onedevice = args.d
    ip_list = []
    ip_list.append(onedevice)
if args.i:
    ipaddr = args.i
if args.x:
    exlinks = args.x
if args.m:
    macaddr = args.m
if args.l:
    iplist = args.l
    listips = open(iplist)
    with listips as f:
        ip_list = [line.rstrip() for line in f]
    listips.close()
elif not args.l and not args.d:
    with open('iplist.txt') as f:
        ip_list = [line.rstrip() for line in f]
if args.u:
    uname = args.u
if args.p:
    upass = args.p

alldatafile = open("output.txt", "wb")

formatter = "{0:<20}{1:<20}{2:<20}{3:<20}{4:<20}{5:<20}{6:<20}{7:<20}{8:<20}"


def printheader():
    header = formatter.format('Device', 'Mac-Address', 'Interface', 'IP-Address', 'L3-Interface', 'L3-Gateway-Address', 'Vlan-ID', 'Vlan-Name', 'Notes')
    alldatafile.write(header + '\n')
    print header


def print_data(ip, mac_address, interface, ip_address, l3_interface, l3_interface_address, tag, vlan_name, untagged_port):
    data = formatter.format(ip, mac_address, interface, ip_address, l3_interface, l3_interface_address, tag, vlan_name, untagged_port)
    alldatafile.write(data + '\n')
    print data


def process_device(ip, **kwargs):
    dev = Device(host=ip, **kwargs)

    try:
        dev.open()
        arp_table = ArpTable(dev)
        arp_table.get()
        vlan_table = VlanTable(dev)
        vlan_table.get()
        switch_table = EthSwitchTable(dev)
        switch_table.get()
        switch_interface = EthSwitchInterfaceTable(dev)
        switch_interface.get()

        if len(switch_table) > 0:
            for x in switch_table:
                for a in arp_table:
                    for v in vlan_table:
                        str = v.l3_interface
                        if ipaddr == a.ip_address and a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
                            print_data(ip.rstrip(), x.mac_address, x.interface, a.ip_address, a.l3_interface, v.l3_interface_address, x.tag, x.vlan_name, '')
                            for i in switch_interface:
                                if x.interface == i.interface and x.vlan_name == i.vlan_name:
                                    if i.interface_tag == 'untagged':
                                        print_data(ip.rstrip(), x.mac_address, x.interface, '', '', '', x.tag, x.vlan_name, untagged_port)
                        elif macaddr == a.mac_address and a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
                            print_data(ip.rstrip(), x.mac_address, x.interface, a.ip_address, a.l3_interface, v.l3_interface_address, x.tag, x.vlan_name, '')
                        else:
                            if macaddr == '' and ipaddr == '':
                                if a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
                                    print_data(ip.rstrip(), x.mac_address, x.interface, a.ip_address, a.l3_interface, v.l3_interface_address, x.tag, x.vlan_name, '')
                if x.mac_address != '' and macaddr == '' and ipaddr == '':
                    print_data(ip.rstrip(), x.mac_address, x.interface, '', '', '', x.tag, x.vlan_name, '')
                if macaddr == x.mac_address:
                    for i in switch_interface:
                        if macaddr != '':
                            if x.interface == i.interface and macaddr == x.mac_address and x.vlan_name == i.vlan_name:
                                if i.interface_tag == 'untagged':
                                    print_data(ip.rstrip(), x.mac_address, x.interface, '', '', '', x.tag, x.vlan_name, untagged_port)
        else:
            print '\nNo table entries for this device: ' + ip.rstrip() + '\n'

    except RpcError:
        msg = "{0} was Skipped due to RPC Error.  Device is not EX/Branch-SRX Series".format(ip.rstrip())
        alldatafile.write(msg + '\n')
        print msg
        dev.close()

    except Exception as err:
        msg = "{0} was skipped due to unhandled exception.\n{1}".format(ip.rstrip(), err)
        alldatafile.write(msg + '\n')
        print msg
        traceback.print_exc(file=sys.stdout)

    dev.close()


def runcert(ip):
    test.append(ip)
    result = process_device(ip)
    return result


def multiRuncert():
    pool = ThreadPool(cpu_count() * 16)
    global ip_list
    global results
    results = pool.map_async(runcert, ip_list)
    pool.close()
    pool.join()


def runuser(ip):
    test.append(ip)
    result = process_device(ip, user=uname, password=upass)
    return result


def multiRunuser():
    pool = ThreadPool(cpu_count() * 16)
    global ip_list
    global results
    results = pool.map_async(runuser, ip_list)
    pool.close()
    pool.join()


def onefn(runner):
    os.system('clear')
    printheader()
    runner()
    alldatafile.close()
    print "--- {0} seconds ---".format(time.time() - start_time)
    sys.exit()

if cert:
    onefn(multiRuncert)
if uname == '':
    uname = raw_input("\nDevices will require valid login credentials.\nPlease enter your login name: ")
if upass == '':
    upass = getpass.getpass(prompt='Please enter your password: ')
    onefn(multiRunuser)
else:
    onefn(multiRunuser)
