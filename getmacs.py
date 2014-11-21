#!/usr/local/bin/python

import re, os, sys, getopt, getpass, time, argparse
from optparse import OptionParser
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
    vlan_tag: interface-vlan-member-tagid
    tag: interface-vlan-member-tagness
 
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

yamlfile = open("yamlethtable.yml","wb")
print  >>yamlfile,YamlTable
yamlfile.close()
globals().update( loadyaml('yamlethtable.yml'))



results = ''
test = []
macaddr = ''
ipmacaddr = ''
vlan = ''
uname = ''
upass = ''
cert = ''
exlinks = ''
onedevice = ''
start_time = time.time()

f = open("iplist.txt")
ip_list = f.readlines()

def syntax():
  print ('\nUsage:\n--------------------------------------\nFull table using username/password:\n\n\tgetmacs.py -u <username> [-p <password>]\n\nFull table using Certlogin:\n\n\tgetmacs.py -c\n\nFull table and exclude interfaces:\n\n\tgetmacs.py -x <interface-name> -u <username> [-p <password>]\n\nSingle device:\n\n\tgetmacs.py -d <ip-address> -u <username> [-p <password>]\n\nMultiple devices:\n\n\tgetmacs.py -l <file> -u <username> [-p <password>]\n\nFind a Mac-Address:\n\n\tgetmacs.py -m <mac-address>\n\n')

try:
  opts, args = getopt.getopt(sys.argv[1:],"achx:i:v:m:u:p:d:l:?", ["help"])
except getopt.GetoptError as err:
  print ('\nIncorrect usage - ') + str(err)
  syntax()
  sys.exit(2)

for o, a in opts:
  if o == '-c':
    cert = 1
  elif o == '-x':
    exlinks = a
  elif o == '-i':
    ipmacaddr = a
  elif o == '-v':
    vlan = a
  elif o == '-m':
    if not re.match("[0-9a-f]{2}([:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", a.lower()):
      print ("\nPlease enter your MAC address in the form xx:xx:xx:xx:xx:xx using only letters a-f,\nnumbers 0-9, and colons as separators.\n")
      sys.exit()
    macaddr = a.lower()
  elif o == '-u':
    uname = a
  elif o == '-p':
    upass = a
  elif o == '-d':
    onedevice = a
    singledevice = open("onedevice.txt","wb")
    print >>singledevice, a
    singledevice = open("onedevice.txt")
    ip_list = singledevice.readlines()
    singledevice.close()
    os.remove("onedevice.txt")
  elif o == '-l':
    iplist = a
    listips = open(iplist)
    ip_list = listips.readlines()
    listips.close()
  elif o in ['-h','-?','--help']:
    syntax()
    sys.exit()

alldatafile = open("output.txt","wb")

def printheader():
  print >>alldatafile,'Device-IP'+'\t'.expandtabs(8)+'\t'+'Mac-Address'+'\t'.expandtabs(10)+'Interface'+'\t'.expandtabs(4)+'\t'+'Vlan-ID'+'\t'.expandtabs(6)+'\t'+'Vlan-Name'
  print ('Device-IP'+'\t'.expandtabs(8)+'\t'+'Mac-Address'+'\t'.expandtabs(10)+'Interface'+'\t'.expandtabs(4)+'\t'+'Vlan-ID'+'\t'.expandtabs(6)+'\t'+'Vlan-Name')

def process_device(ip, **kwargs):
  dev = Device(ip, **kwargs)
  try:
    dev.open()
    switch_table = EthSwitchTable(dev)
    switch_table.get()

    if len(switch_table) > 0:
      for x in switch_table:
        if macaddr != '':
          if x.interface != exlinks:
            if macaddr == x.mac_address:
              print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name
              print (ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name)
          elif x.interface != exlinks:
            print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name
            print (ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name)
        elif exlinks == '':
          print >>alldatafile,ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name
          print (ip.rstrip()+'\t'.expandtabs(8)+'\t'+x.mac_address+'\t'.expandtabs(4)+x.interface+'\t'.expandtabs(6)+'\t'+x.tag+'\t'.expandtabs(6)+'\t'+x.vlan_name)
    else:
      print ('\nNo table entries for this device.\n\n')

  except RpcError:
    print >>alldatafile,ip.rstrip(),'was Skipped due to RPC Error.  Device is not EX/Branch-SRX Series'
    print (ip.rstrip(),'was Skipped due to RPC Error.  Device is not EX/Branch-SRX Series')
    dev.close()
  dev.close()

def runcert(ip):
  test.append(ip)
  result = process_device(ip)
  return result

def multiRuncert():
  pool = ThreadPool(cpu_count()*8)
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
  pool = ThreadPool(cpu_count()*8)
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
  os.remove("yamlethtable.yml")  
  print ("--- {0} seconds ---").format(time.time() - start_time)
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
