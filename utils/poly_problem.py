import argparse
import os
import stat
import sys
import math
import random
import pathlib
import shutil
import traceback
import functools
import xml.etree.ElementTree as ET


def rand_color():
    x = tuple((random.randint(0, 255) for _ in range(3)))
    return '#%02X%02X%02X' % x


parser = argparse.ArgumentParser()
parser.add_argument('--language', default='chinese')
parser.add_argument('--color', default=rand_color())
parser.add_argument('--probid', default=None)
parser.add_argument('--src_root', type=pathlib.Path, default=pathlib.Path('.'))
parser.add_argument('--dst_root', type=pathlib.Path, default=pathlib.Path('./dom-pack'))


def read_desc(path):
    with open(path) as f:
        d = {}
        for l in f.readlines():
            u, v = map(str.strip, l.split(':', 1))
            d[u] = v
        return d

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)

def write(dst, content):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, 'w') as f:
        f.write(content)

def read_xml(path):
    return ET.parse(path).getroot()

def find_tags(node, keys):
    results = {k: None for k in keys}
    def dfs(node):
        if node.tag in results:
            if results[node.tag] is not None:
                raise Exception(
                    f'multiple occurrences of `{node.tag}` are found'
                )
            results[node.tag] = node
        for child in node:
            dfs(child)
    dfs(node)
    return results

def check_nodes(nodes, keys):
    for k in keys:
        if nodes[k] is None:
            raise Exception(f'no occurrence of `{k}` is found')

@functools.lru_cache
def get_xml_nodes(src_root):
    root = read_xml(src_root / 'problem.xml')
    nodes = find_tags(root, {'problem', 'names', 'judging', 'solutions', 'checker', 'interactor'})
    check_nodes(nodes, {'problem', 'names', 'judging', 'solutions', 'checker'})
    nodes.update(find_tags(next(iter(nodes['judging'])), {'time-limit', 'memory-limit'}))
    return nodes


def write_domjudge_problem_ini(args, nodes):
    for tag in nodes['names']:
        if tag.get('language').lower() == args.language.lower():
            name = tag.get('value')
            break
    else:
        raise Exception(f'there is no name in language `{args.language}`')
    s = f'''\
probid = {args.probid or nodes['problem'].get('short-name')}
name = {name}
timelimit = {float(nodes['time-limit'].text) * 1e-3}
color = {args.color}
'''
    write(args.dst_root / 'domjudge-problem.ini', s)

def write_problem_yaml(args, nodes):
    if nodes['interactor'] is None:
        validation = 'custom'
    else:
        validation = 'custom interactive'
    s = f'''\
limits:
    memory: {math.ceil(float(nodes['memory-limit'].text) * 0.5 ** 20)}
validation: {validation}
'''
    write(args.dst_root / 'problem.yaml', s)

def make_problem_info(args):
    nodes = get_xml_nodes(args.src_root)
    write_domjudge_problem_ini(args, nodes)
    write_problem_yaml(args, nodes)


def read_testset(args):
    nodes = get_xml_nodes(args.src_root)
    keys = {
        'time-limit', 'memory-limit',
        'input-path-pattern', 'answer-path-pattern',
        'test-count', 'tests',
    }
    testset = {'sample': [], 'secret': []}
    cnt = 0
    for testset_node in nodes['judging']:
        t_nodes = find_tags(testset_node, keys)
        check_nodes(t_nodes, keys)
        assert len(list(t_nodes['tests'])) == int(t_nodes['test-count'].text)
        for i, t in enumerate(t_nodes['tests']):
            u, v = map(lambda x: t_nodes[x].text % (i + 1),
                ('input-path-pattern', 'answer-path-pattern'))
            if t.get('sample', '').lower() == 'true':
                cnt += 1
                testset['sample'].append((cnt, u, v))
            else:
                cnt += 1
                testset['secret'].append((cnt, u, v))
    return testset

def copy_data(args):
    testset = read_testset(args)
    for k in testset:
        for i, u, v in testset[k]:
            copy(args.src_root / u, args.dst_root / 'data' / k / f'{i}.in')
            copy(args.src_root / v, args.dst_root / 'data' / k / f'{i}.ans')


def write_wrap_tex(args):
    nodes = get_xml_nodes(args.src_root)
    probid = args.probid or nodes['problem'].get('short-name')
    def guess_id():
        if len(probid) != 1 and not probid.isalpha():
            return 0
        if probid.isupper():
            return ord(probid) - ord('A')
        if probid.islower():
            return ord(probid) - ord('a')
        return 0
    pid = guess_id()
    s = '''\
\\input{../../../common.tex}
\\begin{document}
\\raggedbottom
\\addtocounter{problem}{%d}
\\import{}{problem}
\\end{document}
''' % pid
    write(args.dst_root / 'problem_statement' / 'wrap.tex', s)


def copy_statement(args):
    src_path = args.src_root / 'statements' / args.language
    for i in src_path.glob('**/*'):
        copy(i, args.dst_root / 'problem_statement' / i.relative_to(src_path))
    write_wrap_tex(args)
    try:
        os.symlink('../../../olymp.sty/olymp.sty', args.dst_root / 'problem_statement/olymp.sty')
    except OSError:
        print('[FAIL] Create symlink to olymp.sty')


type_map = {
    'accepted': 'accepted', 'main': 'accepted',
    'wrong_answer': 'wrong_answer', 'presentation_error': 'wrong_answer',
    'rejected': 'wrong_answer',
    'memory_limit_exceeded': 'run_time_error',
    'time_limit_exceeded': 'time_limit_exceeded',
    'time_limit_exceeded_or_accepted': 'time_limit_exceeded',
    'time_limit_exceeded_or_memory_limit_exceeded': 'time_limit_exceeded',
}

def copy_solutions(args):
    src_path = args.src_root / 'solutions'

    solution_type = {}
    def get_solution_type(node):
        if node.tag == 'source':
            p = args.src_root / node.get('path')
            solution_type[p] = node.get('type').lower()
        for child in node:
            get_solution_type(child)
    get_solution_type(get_xml_nodes(args.src_root)['solutions'])

    for i in src_path.glob('*.desc'):
        desc = read_desc(i)
        filename, tag = desc['File name'], type_map[desc['Tag'].lower()]

        src = src_path / filename
        if src not in solution_type:
            print('[WARN]', f'{i} is in {src_path} but not in problem.xml')
            continue

        if solution_type[src] == 'python.3':
            name = filename.replace('.py3', '.py').replace('.py', '.py3')
            dst = args.dst_root / 'submissions' / tag / name
        elif solution_type[src] == 'python.2':
            name = filename.replace('.py2', '.py').replace('.py', '.py2')
            dst = args.dst_root / 'submissions' / tag / name
        else:
            dst = args.dst_root / 'submissions' / tag / filename

        copy(src, dst)


def get_build_cmd(src_type, src_filename, src_target):
    if src_type.startswith('cpp.'):
        return f'g++ -Wall -DDOMJUDGE -O2 {src_filename} -o {src_target}\n'
    elif src_type.startswith('c.'):
        return f'gcc -Wall -DDOMJUDGE -O2 {src_filename} -o {src_target}\n'
    else:
        raise Exception(f'unknown type `{src_type}` for build and run')

def make_checker_scripts(args, checker_type, checker_filename):
    return f'''\
#!/bin/sh
{get_build_cmd(checker_type, checker_filename, 'run')}
chmod +x run
'''
"""
    return f'''\
#!/bin/sh
{get_build_cmd(checker_type, checker_filename, 'checker_run')}
chmod +x checker_run
cat > run << EOF
#!/bin/sh
exec ./checker_run "\\$1" /dev/stdin "\\$2" "\\$3"/judgemessage.txt
EOF
chmod +x run
'''
"""

def make_interactor_scripts(args, checker_type, checker_filename,
        interactor_type, interactor_filename):
    return f'''\
#!/bin/sh
{get_build_cmd(interactor_type, interactor_filename, 'run')}
chmod +x run
'''
"""
    return f'''\
#!/bin/sh
{get_build_cmd(checker_type, checker_filename, 'checker_run')}
{get_build_cmd(interactor_type, interactor_filename, 'interactor_run')}
chmod +x checker_run interactor_run
cat > run << EOF
#!/bin/sh
./interactor_run "\\$1" "\\$3"/teammessage.txt "\\$2" "\\$3"/judgemessage.txt <&0
if [ \\$? -ne 42 ]; then
    exit \\$?
fi
./checker_run "\\$1" "\\$3"/teammessage.txt "\\$2" "\\$3"/judgeerror.txt
if [ \\$? -ne 42 ]; then
    exit \\$?
fi
cat "\\$3"/judgeerror.txt >> "\\$3"/judgemessage.txt
rm "\\$3"/judgemessage.txt
exit 42
EOF
chmod +x run
'''
"""


def copy_checker_and_interactor(args):
    copy(pathlib.Path(__file__).parent / 'testlib.h',
        args.dst_root / 'output_validators/checker/testlib.h')

    nodes = get_xml_nodes(args.src_root)

    checker_node = find_tags(nodes['checker'], {'source'})['source']
    checker_src = args.src_root / checker_node.get('path')
    checker_dst = args.dst_root / 'output_validators/checker' / checker_src.name
    copy(checker_src, checker_dst)

    if nodes['interactor'] is None:
        build_script = make_checker_scripts(args,
            checker_node.get('type'), checker_src.name)
    else:
        interactor_node = find_tags(nodes['interactor'], {'source'})['source']
        interactor_src = args.src_root / interactor_node.get('path')
        interactor_dst = args.dst_root / 'output_validators/checker' / interactor_src.name
        copy(interactor_src, interactor_dst)
        build_script = make_interactor_scripts(args,
            checker_node.get('type'), checker_src.name,
            interactor_node.get('type'), interactor_src.name)

    build_script_path = args.dst_root / 'output_validators/checker/build'
    write(build_script_path, build_script)
    os.chmod(build_script_path, os.stat(build_script_path).st_mode | stat.S_IEXEC)


def main(args):
    def wrap(func):
        func_name = ' '.join(func.__qualname__.split('_')).capitalize()
        try:
            func(args)
        except:
            print('[FAIL]', func_name)
            traceback.print_exception(*sys.exc_info(), file=sys.stdout)
        else:
            print('[OK]', func_name)

    wrap(make_problem_info)
    wrap(copy_statement)
    wrap(copy_solutions)
    wrap(copy_data)
    wrap(copy_checker_and_interactor)


if __name__ == '__main__':
    args = parser.parse_args()

    main(args)
