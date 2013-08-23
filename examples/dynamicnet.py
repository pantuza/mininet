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
from mininet.node import RemoteController
from mininet.util import dumpNetConnections
from mininet.link import Intf
import traceback
import time


class DynCLI(CLI):
    "Extended CLI to remove nodes"

    def __init__(self, *args, **kwargs):
        CLI.__init__(self, *args, **kwargs)

    def _net_delete(self, node_type, node):
        if node_type == 'switch':
            self.mn.delSwitch(node)
        elif node_type == 'host':
            self.mn.delHost(node)
        elif node_type == 'controller':
            self.mn.delController(node)
        else:
            error("Wrong node type %s." % node_type)

    def _check_pair(self, name1, name2):
        if name1 not in self.nodemap:
            error('Node(1) %s not exists.\n' % name1)
            return False
        elif name2 not in self.nodemap:
            error('Node(2) %s not exists.\n' % name2)
            return False
        return True

    def _add_node(self, node_type, name, **param):
        if name in self.nodemap:
            error('Already exists node %s\n' % name)
            return
        # Add to Mininet
        if node_type == 'host':
            node = self.mn.addHost(name, **param)
        elif node_type == 'switch':
            node = self.mn.addSwitch(name, **param)
            node.start(self.mn.controllers)
        elif node_type == 'controller':
            node = self.mn.addController(name, **param)
            node.start()
        # Add to CLI
        self.nodelist.append(node)
        self.nodemap[name] = node
        info("!!! New node pid = %s.\n" % str(node.pid))

    def _add_intf(self, node_name, intf_name, **param):
        info("Use 'add link' instead.\n")

    def _add_link(self, name1, name2, **param):
        if not self._check_pair(name1, name2):
            return
        node1, node2 = self.nodemap[name1], self.nodemap[name2]
        link = self.mn.addLink(node1, node2, **param)
        
    def _del_node(self, node_type, name):
        if name not in self.nodemap:
            error('Node %s not exists.\n' % name)
            return
        node = self.nodemap[name]
        # Remove from Mininet
        if node_type == 'switch':
            self.mn.delSwitch(node)
        elif node_type == 'host':
            self.mn.delHost(node)
        elif node_type == 'controller':
            self.mn.delController(node)
        else:
            error("Wrong node type %s." % node_type)
            return
        # Remove from CLI
        del self.nodemap[name]
        self.nodelist.remove(node)

    def _del_intf(self, node_name, intf_name):
        if node_name not in self.nodemap:
            error('Node %s not exists.\n' % node_name)
            return
        node = self.nodemap[node_name]
        if intf_name not in node.nameToIntf:
            error("Node %s hasn't interface %s." % (node_name, intf_name))
            return
        intf = node.nameToIntf[intf_name]
        intf.delete()

    def _param_intf_name_to_port(self, param_intf, param_port, node, param):
        if (param_intf in param):
            intf_name = param[param_intf]
            del param[param_intf]
            if isinstance(intf_name, basestring):
                intf = node.getIntf(intf_name)
                if isinstance(intf, Intf):
                    param[param_port] = node.getPort(intf)

    def _del_link(self, name1, name2, **param):
        if not self._check_pair(name1, name2):
            return
        node1, node2 = self.nodemap[name1], self.nodemap[name2]
        self._param_intf_name_to_port('intf1', 'port1', node1, param)
        self._param_intf_name_to_port('intf2', 'port2', node2, param)
        self.mn.delLink(node1, node2, **param)

    def _parse_add_del_args(self, cmd, line):
        args = line.split()
        if len(args) < 2:
            error('invalid number of args: ' + cmd)
            return None, None
        elif args[0] not in ['switch', 'host', 'controller', 'intf', 'link']:
            error('invalid network component type: ' + cmd +
                  ' <switch|host|intf|link|controller>\n')
            return None, None
        elif args[0] == 'link' and len(args) < 3:
            error('invalid number of args: ' + cmd + ' link')
            return None, None
        if args[0] == 'intf' and len(args) < 3:
            error('invalid number of args: ' + cmd + ' intf')
            return None, None
        param = {}
        opt_pos = 3 if args[0] in ['link', 'intf'] else 2
        for opt_param in args[opt_pos:]:
            opt, sep, str_val = opt_param.partition('=')
            if str_val:
                try:
                    val = eval(str_val)
                except:
                    val = str_val
            else:
                val = True
            param[opt] = val
        return args, param

    def do_add(self, line):
        "Add a network component"
        args, param = self._parse_add_del_args('add', line)
        if args:
            if args[0] == 'link':
                self._add_link(args[1], args[2], **param)
            elif args[0] == 'intf':
                self._add_intf(args[1], args[2], **param)
            else:
                self._add_node(args[0], args[1], **param)

    def do_del(self, line):
        "Delete a network"
        args, param = self._parse_add_del_args('del', line)
        if args:
            if args[0] == 'link':
                self._del_link(args[1], args[2], **param)
            elif args[0] == 'intf':
                self._del_intf(args[1], args[2])
            else:
                self._del_node(args[0], args[1])

    def do_pingall(self, line):
        "Ping between all hosts that has a interface."
        hosts = [node for node in self.mn.hosts
                 if node.intf() and hasattr(node.intf(), 'ip')]
        if len(hosts) > 1:
            self.mn.ping(hosts)
        else:
            error("There's not enough hosts with ip address.\n")

    def do_net(self, line):
        "List network connections."
        dumpNetConnections(self.mn)

    def do_wait(selfself, line):
        " "
        args = line.split()
        if len(args) != 1:
            error('invalid number of args: wait <secs>')
            return
        time.sleep(float(args[0]))

    dynHelpStr = (
        'Dynamic commands:\n'
        'add <switch|host|controller> <name>'
        ' [<opt_1>[=<val_1>]]... [<opt_n>[=<val_n>]]\n'
        'add link <name1> <name2> '
        '[<opt_1>[=<val_1>]] ... [<opt_n>[=<val_n>]]\n'
        'add intf <name> <auto|<intf_name>> '
        '[<opt_1>[=<val_1>]] ... [<opt_n>[=<val_n>]] (not implemented!)\n'
        'del <switch|host|controller> <name>\n'
        'del link <name1> <name2> [intf1=<intf1_name>] [intf2=<intf2_name>]\n'
        'del intf <name> <intf_name>\n'
        '\n'
    )

    def do_help(self, line):
        " "
        CLI.do_help(self, line)
        output(self.dynHelpStr)


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
    topo = LinearTopo(k=int(options.switches), n=int(options.hosts))
    #topo = LinearTopo()

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
        except Exception as obj:
            error('Fail: %s\n Args: %s \n %s \n' % (type(obj), obj.args, obj))
            traceback.print_exc()
            continue

    # Stop the network
    net.stop()

if __name__ == "__main__":
    main()
