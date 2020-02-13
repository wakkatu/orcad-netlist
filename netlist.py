import csv
import logging
import re
import weakref
from pprint import pprint

logHdr = logging.StreamHandler()
logHdr.setFormatter(logging.Formatter(
    "%(name)s:%(lineno)d:%(levelname)s: %(message)s"))
log = logging.getLogger(__file__)
log.addHandler(logHdr)

class NetlistObj(object):
    def __init__(self, name):
        self.name = name
        if hasattr(self.__class__, 'objs'):
            self.__class__.objs[name] = self
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.name))

class Net(NetlistObj):
    objs = weakref.WeakValueDictionary()
    def __init__(self, name):
        super(Net, self).__init__(name)
        self.nodes = weakref.WeakValueDictionary()

class Chip(NetlistObj):
    objs = weakref.WeakValueDictionary()
    def __init__(self, name):
        super(Chip, self).__init__(name)
        self.nodes = weakref.WeakValueDictionary()

class Node(NetlistObj):
    def __init__(self, name, desc, chip, net):
        super(Node, self).__init__(name)
        if not isinstance(chip, Chip):
            chip = Chip.objs.get(chip) or Chip(chip)
        if not isinstance(net, Net):
            net = Net.objs.get(net) or Net(net)
        self.desc = desc
        self.chip = chip
        self.attach_net(net)
    def __repr__(self):
        return "%s(%s,%s,%s,%s)" % (
            self.__class__.__name__,
            repr(self.name),
            repr(self.desc),
            repr(self.chip.name),
            repr(self.net.name))
    def attach_net(self, net):
        if not isinstance(net, Net):
            net = Net.objs.get(net)
        if hasattr(self, 'net'):
            self.chip.nodes[self.net.name] = None
            self.net.nodes[self.chip.name] = None
        self.net = net
        if net is not None:
            self.net.nodes[self.chip.name] = self
            self.chip.nodes[self.net.name] = self
    def is_orphan(self):
        if self.net is None:
            return True
        if self.chip.nodes[self.net.name] is not self:
            return True
        if self.net.nodes[self.chip.name] is not self:
            return True
        return False

def parse_xnet(f):
    if isinstance(f, str):
        f = open(f, 'r')
    nodes = []
    net_name = 'UNKNOWN'
    while True:
        buf = f.readline().strip()
        if not buf:
            # file corrupt?
            break
        elif buf == 'NET_NAME':
            buf = f.readline().strip()
            net_name = re.sub(r"^'|'$", "", buf)
        elif buf.startswith('NODE_NAME'):
            chip_name, pin_name = buf.split()[1:]
            _ = f.readline().strip()
            buf = f.readline().strip()
            node_desc = re.sub(r"^'|'.*$", "", buf)
            nodes.append(Node(pin_name, node_desc, chip_name, net_name))
        elif buf == 'END.':
            break
    return nodes

def filter_nodes(nodes, key_objs):
    keys = map(lambda x: x.name if hasattr(x, 'name') else x, key_objs)
    return [node for key, node in nodes.items() if key not in keys]

def set_chip_transparent(net, chip):
    """
    ... - net - node - chip - client_node - client_net - client_node - ...
    to
    ... net - target_node - ...
    """
    if len(chip.nodes) != 2:
        log.error("set_chip_transparent: %r too many nodes" % (chip))
        return False
    client_net = filter_nodes(chip.nodes, [net])[0].net
    client_node = filter_nodes(client_net.nodes, [chip])[0]
    client_node.attach_net(net)
    net.nodes[chip.name] = None
    return True

def numerical_sorting_key(k):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', k)]

def sorted_rows(k):
    return map(numerical_sorting_key, k)

def dump_nets(nets, host_chip, f, key=None):
    fcsv = csv.writer(f)
    rows = []
    for net_name in nets:
        net = Net.objs[net_name]
        host_node = net.nodes[host_chip]
        client_node = filter_nodes(net.nodes, [host_chip])[0]
        rows.append([net.name, host_node.desc, client_node.chip.name, client_node.desc])
    for row in sorted(rows, key=key):
        log.debug("csv.writerow: %r" % row)
        fcsv.writerow(row)

def netlist_main(argv=None, dump_f=dump_nets, key_f=sorted_rows):
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-C', '--chip')
    parser.add_argument('-N', '--match-net', type=re.compile, metavar='REGEX')
    parser.add_argument('-X', '--exclude-chip', nargs='+', type=re.compile,
        default=[], metavar='REGEX')
    parser.add_argument('-f', '--input-file', default="pstxnet.dat",
        metavar='pstxnet.dat')
    parser.add_argument('-o', '--output-file', default=sys.stdout,
        metavar='CSV_FILE')

    args = parser.parse_args(args=argv)
    if args.verbose:
        log.setLevel({1: logging.INFO}.get(args.verbose, logging.DEBUG))
    log.info("args=%r" % args)

    global nodes
    nodes = parse_xnet(args.input_file)

    global nets
    nets = []

    if args.chip is not None:
        for net_name, node in Chip.objs[args.chip].nodes.items():
            if args.match_net and not args.match_net.match(net_name):
                continue
            nets.append(net_name)

    if len(nets):
        dump_f(nets, args.chip, args.output_file, key=key_f)

    import os
    if os.isatty(1) and args.interactive:
        from code import interact
        interact(local=globals())
        sys.exit()

if __name__ == "__main__":
    netlist_main()
