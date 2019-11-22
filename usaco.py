import urllib.request
import re
import collections
import zipfile
import pathlib
import io
import os
from bs4 import BeautifulSoup


sep_statement = r'<span\s*id="probtext-text"[^>]*>\s*'
sep_input_format = r'<div\s*class=\'prob-in-spec\'[^>]*>\s*<h\d>INPUT\s*FORMAT[^<]*</h\d>\s*'
sep_output_format = r'<div\s*class=\'prob-out-spec\'[^>]*>\s*<h\d>OUTPUT\s*FORMAT[^<]*</h\d>\s*'
sep_sample_input = r'<h\d>SAMPLE\s*INPUT[^<]*</h\d>\s*<pre\s*class=\'in\'[^>]*>\s*'
sep_sample_output = r'</pre>\s*<h\d>SAMPLE\s*OUTPUT[^<]*</h\d>\s*<pre\s*class=\'out\'[^>]*>\s*'
sep_notes = r'</pre>\n'
sep_end = r'(Problem\s*credits|</span>)'
sep_content = r'(.*?)'


res = list(map(lambda x: re.compile(x, re.MULTILINE | re.DOTALL), [
    r'<h2>\s*Problem\s*\d\s*\.\s*([^<]*?)\s*</h2>',
    sep_statement + sep_content + sep_input_format,
    sep_input_format + sep_content + sep_output_format,
    sep_output_format + sep_content + sep_sample_input,
    sep_sample_input + sep_content + sep_sample_output,
    sep_sample_output + sep_content + sep_notes,
    sep_notes + sep_content + sep_end,
]))

Content = collections.namedtuple('Content', (
    'problem_num_id', 'problem_id', 'color',
    'title', 'statement',
    'input_format', 'output_format',
    'sample_in', 'sample_out',
    'notes'
))


def prepare_data():
    for problem in problems.values():
        data_path = pathlib.Path(f'{problem.sid}.zip')
        url = f'http://www.usaco.org/current/data/{problem.sid}.zip'
        os.system(f'wget {url} -O {data_path}')


def extract_data(num, problem):
    problem_id = chr(ord('a') + num)
    path = pathlib.Path(f'problems/{problem_id}/data')
    (path / 'secret').mkdir(parents=True, exist_ok=True)
    (path / 'sample').mkdir(parents=True, exist_ok=True)
    data_path = pathlib.Path(f'{problem.sid}.zip')
    if not data_path.exists():
        url = f'http://www.usaco.org/current/data/{problem.sid}.zip'
        os.system(f'wget {url} -O {data_path}')
    with zipfile.ZipFile(data_path) as f:
        f.extractall(path / 'secret')
    (path / 'secret/1.in').rename(path / 'sample/1.in')
    (path / 'secret/1.ans').rename(path / 'sample/1.ans')


def escape(s):
    return re.sub(r'\n{3,}', '\n\n', BeautifulSoup(s).get_text().replace('%', '\\%'), re.MULTILINE)


def process(num, html_content):
    html_content = html_content.replace('<p>', '\n\n').replace('</p>', '\n\n')
    c = []
    for r in res:
        m = r.search(html_content)
        if m:
            c.append(escape(m.groups()[0]))
        else:
            c.append('')
    if c[-1]:
        c[-1] = '\\Notes\n' + c[-1]
    problem_id = chr(ord('a') + num)
    color = '#%02X%02X%02X' % tuple((random.randint(0, 255) for _ in range(3)))
    return Content(num, problem_id, color, *c)


def solve(num, pid):
    problem = problems[pid]
    url = f'http://usaco.org/index.php?page=viewproblem2&cpid={pid}'
    html = urllib.request.urlopen(url).read().decode('utf8')
    content = process(num, html)



problem_re = re.compile(r'''
<div[^>]*>\s*<b>\s*([^<]*?)\s*</b>\s*<br\s*/>
[^<]*
<a[^>]*cpid=(\d+)[^>]*>\s*View\s*problem\s*</a>
[^<]*
<a[^>]*current/data/(\w+).zip[^>]*>\s*Test\s*data\s*</a>
.*?
</div>
'''.replace('\n', ''), re.MULTILINE | re.DOTALL)

Problem = collections.namedtuple('Problem', ('title', 'pid', 'sid'))

problems = dict()


def contest(cid):
    url = f'http://www.usaco.org/index.php?page={cid}'
    content = urllib.request.urlopen(url).read().decode('utf8')
    global problems
    for r in problem_re.findall(content):
        p = Problem(*r)
        problems[p.pid] = p


if __name__ == '__main__':
    import sys
    contest(sys.argv[1])
