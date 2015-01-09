#!/usr/bin/python

import re, os, sys, getopt, getpass, time, argparse
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.factory import loadyaml, yaml
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import cpu_count

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
  item: arp-table-entry
  key:
    - mac-address
  view: ArpView

ArpView:
  fields:
    mac_address: mac-address
    ip_address: ip-address
    l3_interface: interface-name"""

yamlfile = open("yamlfile.yml","wb")
print  >>yamlfile,YamlTable
yamlfile.close()
globals().update( loadyaml('yamlfile.yml'))

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
untagged_port = 'Device is possibly connected to this port'

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

if args.c == False:
  cert = 1
if args.d:
  onedevice = args.d
  singledevice = open("onedevice.txt","wb")
  print >>singledevice, onedevice
  singledevice = open("onedevice.txt")
  ip_list = singledevice.readlines()
  singledevice.close()
  os.remove("onedevice.txt")
if args.i:
  ipaddr = args.i
if args.x:
  exlinks = args.x
if args.m:
  macaddr = args.m
if args.l:
  iplist = args.l
  listips = open(iplist)
  ip_list = listips.readlines()
  listips.close()
elif not args.l:
  f = open("iplist.txt")
  ip_list = f.readlines()
if args.u:
  uname = args.u
if args.p:
  upass = args.p

alldatafile = open("output.txt","wb")

def printheader():
  print >>alldatafile,'Device'+'\t'.expandtabs(12)+'\t'+'Mac-Address'+'\t'.expandtabs(10)+'Interface'+'\t'.expandtabs(10)+'\t'+'IP-Address'+'\t'.expandtabs(6)+'\t'+'L3-Interface'+'\t'.expandtabs(4)+'\t'+'L3-Gateway-Address'+'\t'.expandtabs(4)+'\t'+'Vlan-ID'+'\t'.expandtabs(6)+'\t'+'Vlan-Name'
  print 'Device'+'\t'.expandtabs(12)+'\t'+'Mac-Address'+'\t'.expandtabs(10)+'Interface'+'\t'.expandtabs(10)+'\t'+'IP-Address'+'\t'.expandtabs(6)+'\t'+'L3-Interface'+'\t'.expandtabs(4)+'\t'+'L3-Gateway-Address'+'\t'.expandtabs(4)+'\t'+'Vlan-ID'+'\t'.expandtabs(6)+'\t'+'Vlan-Name'


def process_device(ip, **kwargs):
  dev = Device(ip, **kwargs)

  def printipdata():
    print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(8)+'\t'.expandtabs(2)+'\t'+a.ip_address+'\t'.expandtabs(8)+'\t'+a.l3_interface+'\t'.expandtabs(12)+'\t'+v.l3_interface_address+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name
    print ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(8)+'\t'.expandtabs(2)+'\t'+a.ip_address+'\t'.expandtabs(8)+'\t'+a.l3_interface+'\t'.expandtabs(12)+'\t'+v.l3_interface_address+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name

  def printxdata():
    print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(83)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name+'\t'.expandtabs(6)+'\t'
    print ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(83)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name+'\t'.expandtabs(6)+'\t'

  def printonexdata():
    print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(83)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name+'\t'.expandtabs(6)+'\t'+untagged_port
    print ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(83)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name+'\t'.expandtabs(6)+'\t'+untagged_port

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
            str=v.l3_interface
            if ipaddr == a.ip_address and a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
              printipdata()
              for i in switch_interface:
                if x.interface == i.interface and x.vlan_name == i.vlan_name:
                  if i.interface_tag == 'untagged':
                    printonexdata()
            elif macaddr == a.mac_address and a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
              printipdata()
            else:
              if macaddr =='' and ipaddr == '':
                if a.mac_address == x.mac_address and str.strip(' (UP)') == a.l3_interface:
                  printipdata()
        if x.mac_address != '' and macaddr == '' and ipaddr =='':
          printxdata()
        if macaddr == x.mac_address:
          for i in switch_interface:
            if macaddr != '':
              if x.interface == i.interface and macaddr == x.mac_address and x.vlan_name == i.vlan_name:
                if i.interface_tag == 'untagged':
                  printonexdata()
    else:
      print '\nNo table entries for this device: '+ip.rstrip()+'\n'

  except RpcError:
    print >>alldatafile,ip.rstrip(),'was Skipped due to RPC Error.  Device is not EX/Branch-SRX Series'
    print ip.rstrip(),'was Skipped due to RPC Error.  Device is not EX/Branch-SRX Series'
    dev.close()
  dev.close()

def runcert(ip):
  test.append(ip)
  result = process_device(ip)
  return result

def multiRuncert():
  pool = ThreadPool(cpu_count()*16)
  global ip_list
  global results
  results = pool.map_async(runcert, ip_list)
  pool.close()
  pool.join()

def runuser(ip):
  test.append(ip)
  result =   process_device(ip, user=uname, password=upass)
  return result

def multiRunuser():
  pool = ThreadPool(cpu_count()*16)
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
  os.remove("yamlfile.yml")  
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
