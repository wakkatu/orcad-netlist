import re
from pprint import pprint

def parse_xnet(f):
    if isinstance(f, str):
        f = open(f, 'r')
    nets = {}
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
            chip, pin = buf.split()[1:]
            _ = f.readline().strip()
            buf = f.readline().strip()
            desc = re.sub(r"^'|'.*$", "", buf)
            nets.setdefault(net_name, []).append((chip, pin, desc))
        elif buf == "END.":
            break
    return nets

def test1(nets):
    pprint([(net, nodes[0][2], nodes[1][2]) for net, nodes in nets.items() if re.match(r'^P\d+_ISG.*', net)])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true')
    parser.add_argument('pstxnet_dat', type=file)
    args = parser.parse_args()

    nets = parse_xnet(args.pstxnet_dat)

    if args.interactive:
        import sys
        from code import interact
        interact(local=globals())
        sys.exit()
    else:
        test1(nets)
