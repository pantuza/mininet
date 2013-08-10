#!/usr/bin/python

"""
    This script builds a network using mininet for using with
a remote controller like POX.

    The script receives from command line two arguments. The number
of Switches and the number of Hosts per Switch. Then, it will build
the network topology based on this arguments.

    First of all, it build a topology and add the Switches to the network.
After that, add the same number of Hosts for each Switch added. Lastly
it make links between each switch.

@author: Gustavo Pantuza
@since: 18.07.2013

"""

from optparse import OptionParser

from mininet.topo import LinearTopo
from mininet.log import setLogLevel, info, output, error
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, Host, OVSSwitch
from mininet.util import dumpNetConnections, ipAdd, macColonHex
from mininet.link import Link, Intf
import traceback

class DynCLI(CLI):
    "Extended CLI to remove nodes"
    
    def __init__(self, *args, **kwargs):
        ""
        CLI.__init__( self, *args, **kwargs )

    def _net_container(self, type):
        " "
        if type == 'switch':
            return self.mn.switches
        elif type == 'host':
            return self.mn.hosts
        elif type == 'controller':
            return self.mn.controllers
        else:
            return None

    def _check_pair(self, name1, name2):
        " "
        if name1 not in self.nodemap:
            error( 'Node(1) %s not exists.\n' % name1)
            return False
        elif name2 not in self.nodemap:
            error( 'Node(2) %s not exists.\n' % name2)
            return False
        return True

    def _node_deattach_intf(self, node, intf):
        " "
        if isinstance(node, OVSSwitch):
            node.detach(intf)
        try:
            port = node.ports[intf]
            del node.intfs[port]
            del node.ports[intf]
            del node.nameToIntf[intf.name]
        except:
            pass

    def _node_attach_intf(self, node, intf):
        " "
        if isinstance(node, Host):
            node.configDefault()
        elif isinstance(node, OVSSwitch):
            node.attach(intf)

    def _delete_link(self, link):
        link.delete()
        intf1, intf2 = link.intf1, link.intf2
        node1, node2 = intf1.node, intf2.node
        self._node_deattach_intf(node1, intf1)
        self._node_deattach_intf(node2, intf2)

    def _add_node(self, type, name, **param):
        " "
        if name in self.nodemap:
            error( 'Already exists node %s\n' % name)
            return
        # Add to Mininet
        if type == 'host':
            node = self.mn.addHost(name, **param)
        elif type == 'switch':
            node = self.mn.addSwitch(name, **param)
            node.start(self.mn.controllers)
        elif type == 'controller':
            node = self.mn.addController(name, **param)
            node.start()
        # Add to CLI
        self.nodelist.append(node)
        self.nodemap[name] = node
        info("!!! New node pid = %s.\n" % str(node.pid))

    def _add_intf(self, node_name, intf_name, **param):
        " "
        info("Use 'add link' instead.\n")
        
    def _add_link(self, name1, name2, **param):
        " "
        if not self._check_pair(name1, name2):
            return
        node1, node2 = self.nodemap[name1], self.nodemap[name2]
        link = self.mn.addLink(node1, node2, **param)
        info('*** Starting link %s...\n' % link)
        #  Activate interfaces
        self._node_attach_intf(link.intf1.node, link.intf1)
        self._node_attach_intf(link.intf2.node, link.intf2)

    def _del_node(self, type, name):
        " "
        if name not in self.nodemap:
            error( 'Node %s not exists.\n' % name)
            return
        node = self.nodemap[name]
        # Remove from Mininet
        container = self._net_container(type)
        if node not in container:
            error( 'Is %s a %s?\n' % (name, type))
            return
        info( '*** Stopping %s %s...\n' % (type, name))
        # Remove links (interfaces pairs)
        for intf in node.intfList():
            link = intf.link
            if link:
                info( '--- Deleting link %s...\n' % link)
                self._delete_link(link)
        node.stop()
        try:
            container.remove(node)
        except:
            error('Cleanup failure of %s %s.\n' % (type, name))
        # Remove from CLI
        del self.nodemap[name]
        self.nodelist.remove(node)

    def _del_intf(self, node_name, intf_name):
        " "
        if node_name not in self.nodemap:
            error( 'Node %s not exists.\n' % node_name)
            return
        node = self.nodemap[node_name]
        if intf_name not in node.nameToIntf:
            error("Node %s hasn't interface %s." % (node, name))
            return
        intf = node.nameToIntf[intf_name]
        self._node_deattach_intf(node, intf)
        intf.delete()

    def _del_link(self, name1, name2, all=True):
        " "
        if not self._check_pair(name1, name2):
            return
        src_node, dst_node = self.nodemap[name1], self.nodemap[name2]
        for intf in src_node.intfList():
            link = intf.link
            if link:
                node1, node2 = link.intf1.node, link.intf2.node
                if (node1 == src_node and node2 == dst_node) or \
                   (node1 == dst_node and node2 == src_node):
                    info('*** Deleting link %s...\n' % link)
                    self._delete_link(link)
                    if not all:
                        break

    def _parse_args(self, cmd, line):
        " "
        args = line.split()
        if len(args) < 2:
            error('invalid number of args: ' + cmd + ' <type> <param [...]>')
            return None, None
        elif args[0] not in ['switch', 'host', 'controller', 'intf', 'link']:
            error('invalid network component type: ' + cmd + 
                  ' <switch|host|intf|link|controller> <name1> [<name2>]' +
                  ' [opt_1[=val_1] ... opt_n[=val_n]]\n')
            return None, None
        elif args[0] == 'link' and len(args) < 3:
            error('invalid number of args: ' + cmd +
                  ' link <name1> <name2> [opt_1[=val_1] ... opt_n[=val_n]]\n')
            return None, None
        if args[0] == 'intf' and len(args) < 3:
            error('invalid number of args: ' + cmd + ' intf <node> ' +
                  '[<name>|auto] [opt_1[=val_1] ... opt_n[=val_n]]\n')
            return None, None
        param = {}
        opt_pos = 3 if args[0] in ['link', 'intf'] else 2
        for opt_param in args[opt_pos:]:
            opt, sep, str_val = opt_param.partition('=')
            if str_val:
                val = eval(str_val)
            else:
                val = True
            param[opt] = val
        return args, param

    def do_add(self, line):
        "Add a network component"
        args, param = self._parse_args('add', line)
        if args:
            if args[0] == 'link':
                self._add_link(args[1], args[2], **param)
            elif args[0] == 'intf':
                self._add_intf(args[1], args[2], **param)
            else:
                self._add_node(args[0], args[1], **param)

    def do_del(self, line):
        "Delete a network"
        args, param = self._parse_args('del', line)
        if args:
            if args[0] == 'link':
                self._del_link(args[1], args[2])
            elif args[0] == 'intf':
                self._del_intf(args[1], args[2])
            else:
                self._del_node(args[0], args[1])
                
    def do_pingall( self, _line ):
        "Ping between all hosts that has a interface."
        hosts = [node for node in self.mn.hosts 
                 if node.intf() and hasattr(node.intf(), 'ip')]
        if len(hosts) > 1:
            self.mn.ping(hosts)
        else:
            error("There's not enough hosts with ip address.\n")

    def do_net( self, _line ):
        "List network connections."
        dumpNetConnections(self.mn)


def main():
    # Defines the log level
    setLogLevel('info')

    # parses command line arguments
    parser = OptionParser()
    parser.add_option('-H', dest='hosts', default=5,
                      help='Number of hosts per switch')
    parser.add_option('-S', dest='switches', default=2,
                      help='Number of switches')
    (options, args) = parser.parse_args()

    # Build network topology (see mininet/topo.py)
    #topo = LinearTopo(int(options.switches), int(options.hosts))
    topo = LinearTopo()

    # Creates the Network using a remote controller
    #net = Mininet(topo)
    net = Mininet(topo,
                  controller=lambda a: RemoteController(a, ip='127.0.0.1'))

    # Starts the network
    net.start()
    # Run the mininet client
    while True:
        try:
            DynCLI(net)
            break
        except Exception as e:
            error('Fail: %s\n Args: %s \n %s \n' % (type(e), e.args, e))
            traceback.print_exc()
            continue
        
    # Stop the network
    net.stop()

if __name__ == "__main__":
    main()
