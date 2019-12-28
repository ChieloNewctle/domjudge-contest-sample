import collections
import pathlib
import argparse

from . import poly_problem


parser = argparse.ArgumentParser()
parser.add_argument('--language', default='chinese')
parser.add_argument('--src_root', type=pathlib.Path, default=pathlib.Path('./poly'))
parser.add_argument('--dst_root', type=pathlib.Path, default=pathlib.Path('.'))


ProbArgs = collections.namedtuple('ProbArgs', 'language, color, probid, src_root, dst_root')


def gene_prob_args(args, pid, pname):
    return ProbArgs(
        args.language,
        poly_problem.rand_color(),
        pid,
        args.src_root / 'problems' / pname,
        args.dst_root / 'problems' / pid
    )


def get_root(args):
    xml_path = args.src_root / 'contest.xml'
    root = poly_problem.read_xml(xml_path)
    return root


def get_problems(args):
    root = get_root(args)
    def parse(node):
        pid = node.get('index')
        _, pname = node.get('url').rsplit('/', 1)
        return pid, pname
    return list(map(parse, root.findall('./problems/problem')))


def get_contest_name(args):
    root = get_root(args)
    node = root.find(f"./names/name[@language='{args.language}']")
    assert node is not None, f'there is no name found in language {args.language}'
    return node.get('value')


def write_common_tex(args):
    template_path = pathlib.Path(__file__).parent / 'common.tex'
    with open(template_path) as f:
        template = f.read()
    with open(args.dst_root / 'common.tex', 'w') as f:
        f.write(template.replace('$contest_name$', get_contest_name(args)))


def main(args):
    write_common_tex(args)
    problems = get_problems(args)
    for pid, pname in problems:
        print(pid, pname)
        poly_problem.main(gene_prob_args(args, pid, pname))


if __name__ == '__main__':
    args = parser.parse_args()

    main(args)
