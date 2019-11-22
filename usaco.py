import collections
import re
import random
import urllib.request
import zipfile
import pathlib
import shutil
import asyncio
import concurrent.futures
import jinja2
from bs4 import BeautifulSoup
from pySmartDL import SmartDL


sep_statement = r'<span\s*id="probtext-text"[^>]*>\s*'
sep_input_format = r'<div\s*class=\'prob-in-spec\'[^>]*>\s*<h\d>INPUT\s*FORMAT[^<]*</h\d>\s*'
sep_output_format = r'<div\s*class=\'prob-out-spec\'[^>]*>\s*<h\d>OUTPUT\s*FORMAT[^<]*</h\d>\s*'
sep_sample_input = r'<h\d>SAMPLE\s*INPUT[^<]*</h\d>\s*<pre\s*class=\'in\'[^>]*>\s*'
sep_sample_output = r'</pre>\s*<h\d>SAMPLE\s*OUTPUT[^<]*</h\d>\s*<pre\s*class=\'out\'[^>]*>\s*'
sep_notes = sep_sample_output + r'.*?' + r'</pre>'
sep_end = r'(Problem\s*credits|</span>)'
sep_content = r'(.*?)'


res = list(map(lambda x: re.compile(x, re.MULTILINE | re.DOTALL), [
    r'<h2>\s*Problem\s*\d\s*\.\s*([^<]*?)\s*</h2>',
    sep_statement + sep_content + sep_input_format,
    sep_input_format + sep_content + sep_output_format,
    sep_output_format + sep_content + sep_sample_input,
    sep_sample_input + sep_content + sep_sample_output,
    sep_sample_output + sep_content + r'</pre>',
    sep_notes + sep_content + sep_end,
]))


Problem = collections.namedtuple('Problem', (
    'problem_num_id', 'problem_id', 'color',
    'title', 'statement',
    'input_format', 'output_format',
    'sample_in', 'sample_out',
    'notes'
))


def valid_zip(dest):
    with zipfile.ZipFile(dest) as f:
        return f.testzip() is None
    return False


async def download_data(url, dest):
    loop = asyncio.get_running_loop()
    if dest.exists():
        valid = await loop.run_in_executor(None, valid_zip, dest)
        if valid:
            print(dest, 'exists and is valid')
            return
        print(dest, 'is invalid')
        dest.unlink()
    print('Downloading', url, 'to', dest, '...')
    try:
        dl = await loop.run_in_executor(None, lambda *x: SmartDL(*x, progress_bar=False), url, str(dest))
        result = await loop.run_in_executor(None, dl.start)
    except Exception as e:
        print('Failed to download', url, e)
        return
    print('Downloaded', url, 'to', dest)
    return result


async def prepare_data(download=False):
    loop = asyncio.get_running_loop()
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(20))
    pathlib.Path('data_cache').mkdir(parents=True, exist_ok=True)
    tasks = []
    urls = []
    for problem_desc in problems.values():
        data_path = pathlib.Path(f'data_cache/{problem_desc.sid}.zip')
        url = f'http://www.usaco.org/current/data/{problem_desc.sid}.zip'
        if download:
            tasks.append(download_data(url, data_path))
        urls.append(url)
    await asyncio.gather(*tasks)
    return urls


async def extract_data(num, problem_desc, download=False):
    loop = asyncio.get_running_loop()
    problem_id = chr(ord('a') + num)
    path = pathlib.Path(f'problems/{problem_id}/data')
    (path / 'secret').mkdir(parents=True, exist_ok=True)
    (path / 'sample').mkdir(parents=True, exist_ok=True)
    pathlib.Path('data_cache').mkdir(parents=True, exist_ok=True)
    data_path = pathlib.Path(f'data_cache/{problem_desc.sid}.zip')
    if not data_path.exists():
        url = f'http://www.usaco.org/current/data/{problem_desc.sid}.zip'
        if download:
            await download_data(url, data_path)
        else:
            raise FileNotFoundError(data_path)
    with zipfile.ZipFile(data_path) as f:
        print('Extract', data_path, 'to', path)
        await loop.run_in_executor(None, f.extractall, path / 'secret')
    for i in (path / 'secret').glob('*.out'):
        i.rename(str(i)[:-len('.out')] + '.ans')
    (path / 'secret/1.in').rename(path / 'sample/1.in')
    (path / 'secret/1.ans').rename(path / 'sample/1.ans')


def escape(s):
    s = re.compile(r'<pre[^>]*>', re.MULTILINE | re.DOTALL).sub(r'\\begin{verbatim}', s)
    s = re.compile(r'</pre[^>]*>', re.MULTILINE | re.DOTALL).sub(r'\\end{verbatim}', s)
    s = BeautifulSoup(s, 'html5lib').get_text()
    conv = {
        '&': r'\&',
        '%': r'\%',
        '#': r'\#',
        '~': r'\textasciitilde{}',
    }
    conv_regex = re.compile('|'.join(re.escape(key) for key in sorted(conv.keys(), key=lambda item: -len(item))))
    s = conv_regex.sub(lambda match: conv[match.group()], s)
    return re.sub(r'\n{3,}', '\n\n', s, re.MULTILINE)


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
    color = '%02X%02X%02X' % tuple((random.randint(0, 255) for _ in range(3)))
    return Problem(num, problem_id, color, *c)


async def render_template(template_path, dest, context):
    print('Render', template_path, 'to', dest)
    loop = asyncio.get_running_loop()
    with open(template_path) as f:
        content = await loop.run_in_executor(None, f.read)
        template = await loop.run_in_executor(None, jinja2.Template, content)
    def r():
        return template.render(**context)
    result = await loop.run_in_executor(None, r)
    with open(dest, 'w') as f:
        await loop.run_in_executor(None, f.write, result)


async def gene_from_template(num, problem):
    problem_id = chr(ord('a') + num)
    problem_root = pathlib.Path(f'problems/{problem_id}')
    template_root = pathlib.Path('template')
    tasks = []
    for i in template_root.glob('**'):
        file_path = i.relative_to(template_root)
        (problem_root / file_path).mkdir(parents=True, exist_ok=True)
    for i in template_root.glob('**/*'):
        if not i.is_file():
            continue
        file_path = i.relative_to(template_root)
        if i.name == 'olymp.sty':
            shutil.copy(str(i), str(problem_root / file_path))
            continue
        tasks.append(render_template(i, problem_root / file_path, problem._asdict()))
    await asyncio.gather(*tasks)


async def dump_html(num, html):
    loop = asyncio.get_running_loop()
    problem_id = chr(ord('a') + num)
    problem_root = pathlib.Path(f'problems/{problem_id}')
    with open(problem_root / 'origin.html', 'w') as f:
        await loop.run_in_executor(None, f.write, html)


async def add_problem(num, pid):
    loop = asyncio.get_running_loop()
    problem_desc = problems[int(pid)]

    extract_task = asyncio.create_task(extract_data(num, problem_desc))

    url = f'http://usaco.org/index.php?page=viewproblem2&cpid={pid}'
    print(pid, 'request')
    response = await loop.run_in_executor(None, urllib.request.urlopen, url)
    print(pid, 'response')
    html = (await loop.run_in_executor(None, response.read)).decode('utf8')
    print(pid, 'read')

    dump_task = asyncio.create_task(dump_html(num, html))

    problem = process(num, html)

    template_task = asyncio.create_task(gene_from_template(num, problem))
    await asyncio.gather(extract_task, dump_task, template_task)


async def add_problems(*pid):
    loop = asyncio.get_running_loop()
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(20))
    await asyncio.gather(*(add_problem(i, j) for i, j in enumerate(pid)))


problem_desc_re = re.compile(r'''
<div[^>]*>\s*<b>\s*([^<]*?)\s*</b>\s*<br\s*/>
[^<]*
<a[^>]*cpid=(\d+)[^>]*>\s*View\s*problem\s*</a>
[^<]*
<a[^>]*current/data/(\w+).zip[^>]*>\s*Test\s*data\s*</a>
.*?
</div>
'''.replace('\n', ''), re.MULTILINE | re.DOTALL)

ProblemDesc = collections.namedtuple('ProblemDesc', ('title', 'pid', 'sid'))


problems = dict()


async def add_contest(cid):
    global problems
    url = f'http://www.usaco.org/index.php?page={cid}'
    loop = asyncio.get_running_loop()
    print(cid, 'request')
    response = await loop.run_in_executor(None, urllib.request.urlopen, url)
    print(cid, 'response')
    content = (await loop.run_in_executor(None, response.read)).decode('utf8')
    print(cid, 'read')
    for r in problem_desc_re.finditer(content):
        p = ProblemDesc(*r.groups())
        print(cid, p)
        problems[int(p.pid)] = p


async def add_contests(*cid):
    loop = asyncio.get_running_loop()
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(20))
    await asyncio.gather(*(add_contest(i) for i in cid))
