"""Static release audit; optional read-only HTTP link verification with --network."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from concurrent.futures import ThreadPoolExecutor
from lxml import html
import json, re, hashlib, subprocess, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
source=(ROOT/'index.html').read_text()
doc=html.fromstring(source)
templates=json.JSONDecoder().raw_decode((ROOT/'header/templates.js').read_text().split('window.UNISTROY_HEADER_TEMPLATES = ',1)[1])[0]
pages=[('index.html',doc)]+[(name,html.fromstring(markup)) for name,markup in templates.items()]
links=set(); assets=set(); template_checks=[]
for name,page in pages:
    links.update(page.xpath('//a/@href'))
    assets.update(page.xpath('//@src'))
    if name!='index.html':
        phones=page.xpath('//a[starts-with(@href,"tel:")]/@href')
        template_checks.append({'name':name,'phoneLinks':len(phones),'fixedPhone':all(x=='tel:+79600693030' for x in phones),
          'staleInventory':bool(re.search(r'\d[\d\s]*\s+вариант(?:а|ов)?\b|от\s+\d[\d\s,.]*(?:₽|руб\.)',page.text_content()))})
missing=[];checked=set()
def local(path,base=ROOT):
    if not path or path.startswith(('data:','http:','https:','tel:','mailto:','#')):return
    target=(base/unquote(urlsplit(path).path)).resolve()
    checked.add(str(target.relative_to(ROOT)))
    if not target.exists():missing.append(str(target))
for link in links|assets|set(doc.xpath('//link/@href')):local(link)
for css in [ROOT/'font/stylesheet.css',ROOT/'header/reference.css',ROOT/'header/header.css']:
    for url in re.findall(r'url\([\s\'"]*([^\)\'"\s]+)',css.read_text()):local(url,css.parent)
ids=doc.xpath('//@id'); duplicates=sorted({x for x in ids if ids.count(x)>1})
broken_anchors=sorted({x for x in links if x.startswith('#') and x[1:] not in ids})
syntax=[]
for i,script in enumerate(doc.xpath('//script[not(@src)]')):
    result=subprocess.run(['node','--check'],input=script.text or '',text=True,capture_output=True)
    syntax.append({'file':'inline-'+str(i),'pass':result.returncode==0,'error':result.stderr})
for script in ['header/header.js','header/templates.js']:
    result=subprocess.run(['node','--check',str(ROOT/script)],text=True,capture_output=True)
    syntax.append({'file':script,'pass':result.returncode==0,'error':result.stderr})
privacy=[]
for name in ['privacy','personal-data-consent','marketing-consent']:
    path=ROOT/'policy'/f'{name}.pdf';digest=hashlib.sha256(path.read_bytes()).hexdigest()
    privacy.append({'file':str(path.relative_to(ROOT)),'sha256':digest,'referencedVersionCorrect':f'{name}.pdf?v={digest[:16]}' in source})
secrets=[]
patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',r'AKIA[A-Z0-9]{16}',r'sk-(?:proj-)?[A-Za-z0-9_-]{30,}']
for path in [ROOT/'index.html',*list((ROOT/'header').glob('*'))]:
    if path.suffix not in ['.html','.js','.json','.css']:continue
    value=path.read_text()
    if any(re.search(p,value) for p in patterns):secrets.append(str(path.relative_to(ROOT)))
report={'sourceSha256':hashlib.sha256(source.encode()).hexdigest(),'templates':template_checks,'localResourcesChecked':len(checked),
 'missingResources':missing,'duplicateIds':duplicates,'brokenAnchors':broken_anchors,'javascript':syntax,'privacy':privacy,'secretPatternFiles':secrets,
 'scripts':doc.xpath('//script/@src'),'externalLinks':sorted(x for x in links if x.startswith('https://')),
 'images':[{ 'src':x.get('src'),'alt':x.get('alt'),'loading':x.get('loading'),'width':x.get('width'),'height':x.get('height'),
 'bytes':(ROOT/x.get('src')).stat().st_size if x.get('src') and not x.get('src').startswith('https://') else None} for x in doc.xpath('//main//img')],
 'sizes':{x: (ROOT/x).stat().st_size for x in ['index.html','header/templates.js','header/reference.css','header/header.js']}}
(HERE/'static.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['localResourcesChecked','missingResources','duplicateIds','brokenAnchors','secretPatternFiles','sizes']},ensure_ascii=False))
if '--network' in sys.argv:
    def check(url):
        result=subprocess.run(['curl','--silent','--show-error','--location','--max-time','20','--output','/dev/null','--write-out','%{http_code}\t%{url_effective}\t%{time_total}',url],text=True,capture_output=True)
        parts=result.stdout.split('\t')
        return {'url':url,'status':int(parts[0]) if parts[0].isdigit() else 0,'finalUrl':parts[1] if len(parts)>1 else '', 'seconds':parts[2] if len(parts)>2 else '', 'error':result.stderr}
    with ThreadPoolExecutor(max_workers=6) as pool: responses=list(pool.map(check,report['externalLinks']))
    (HERE/'links.json').write_text(json.dumps(responses,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'linksChecked':len(responses),'issues':[x for x in responses if x['status']>=400 or x['status']==0]},ensure_ascii=False))
