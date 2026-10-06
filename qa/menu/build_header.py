"""Build the isolated static header from the verified public DOM/CSS baseline.
Run from release_header/qa/menu. No network or production code is executed.
"""
import json, re, hashlib
from pathlib import Path
from urllib.parse import urljoin
from lxml import html, etree

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / 'header'
OUT.mkdir(exist_ok=True)
CONTACT_PHONE_HREF = 'tel:+79600693030'
CONTACT_PHONE_TEXT = '+7 (960) 069-30-30'
states = {}
for path in HERE.glob('reference-*.json'):
    if path.name == 'reference-css.json': continue
    name = path.stem.removeprefix('reference-')
    if name.endswith('-callback'): continue
    data = json.loads(path.read_text())
    if 'header' in data:
        states[name.replace('1440-dark-', 'desktop-').replace('390-dark-', 'mobile-')] = data['header']
states['city-modal'] = (HERE / 'city-modal.html').read_text()
states['callback-modal'] = (HERE / 'callback-modal.html').read_text()
states['city-tablet-modal'] = (HERE / 'city-tablet-modal.html').read_text()

def clean(markup):
    root = html.fromstring(markup)
    for c in root.xpath('//comment()'): c.drop_tree()
    for el in root.iter():
        if not isinstance(el.tag, str): continue
        for attr in list(el.attrib):
            if attr.startswith('on') or attr.startswith('data-scroll-lock') or attr in ['data-test-id','to']:
                del el.attrib[attr]
        if 'class' in el.attrib:
            el.set('class',' '.join(dict.fromkeys(c for c in el.get('class').split() if not c.startswith(('fade-', 'slide-')))))
        if el.get('style') in ['', 'padding-right: 0px;']: el.attrib.pop('style',None)
        for attr in ['href','src']:
            val = el.get(attr)
            if val and val.startswith('/'): el.set(attr,urljoin('https://unistroy.ru/',val))
        if el.get('href','').startswith('tel:'):
            el.set('href',CONTACT_PHONE_HREF)
            el.set('aria-label',CONTACT_PHONE_TEXT)
            for textel in el.iter():
                if textel.text and re.search(r'\+7[\s(]',textel.text): textel.text = CONTACT_PHONE_TEXT
        # Every image keeps the exact original responsive sources, without its blurred placeholder.
        if el.tag == 'img' and el.get('srcset'):
            el.set('src',el.get('srcset').split(',')[0].strip().split(' ')[0])
        if el.tag == 'input': el.attrib.pop('id',None)
    return html.tostring(root, encoding='unicode').replace('viewbox=', 'viewBox=').replace('preserveaspectratio=', 'preserveAspectRatio=')

states = {k:clean(v) for k,v in states.items()}
# One catalogue for all responsive variants. Inventory counts and prices are intentionally
# omitted from this static landing, even if a future source snapshot includes them.
catalog_path = OUT/'catalog.json'
if catalog_path.exists():
    catalog = json.loads(catalog_path.read_text())
else:
    catalog = {'source':'https://unistroy.ru/', 'city':'kzn', 'capturedOn':'2026-10-05', 'items':{}}
    for category in ['projects','apartments','parking','storages']:
        root = html.fromstring(states['tablet-'+category])
        for a in root.xpath('.//a[contains(@class,"_ProjectCard_")]'):
            title=a.xpath('.//*[contains(@class,"_title_2a6i4_")]')
            info=a.xpath('.//*[contains(@class,"_information_2a6i4_")]/li')
            catalog['items'][a.get('href')]={'title':title[0].text_content() if title else '', 'information':[el.text_content() for el in info]}
for item in catalog['items'].values():
    item['information'] = [value for value in item['information']
                           if not re.fullmatch(r'\d[\d\s]*\s+вариант(?:а|ов)?', value.strip())
                           and not re.search(r'^от\s+\d.*(?:₽|руб\.?)$', value.strip(), re.I)
                           and value.strip() != item['title'].strip()]
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
for key,markup in states.items():
    root=html.fromstring(markup)
    for a in root.xpath('.//a[contains(@class,"_ProjectCard_")]'):
        item=catalog['items'].get(a.get('href'))
        info=a.xpath('.//*[contains(@class,"_information_2a6i4_")]')
        if item and info:
            districts=[bool(el.xpath('.//*[contains(@class,"_district_2a6i4_")]')) for el in info[0]]
            for el in list(info[0]): info[0].remove(el)
            for i,value in enumerate(item['information']):
                el=etree.SubElement(info[0],'li',{'class':'_item_2a6i4_132'})
                if i<len(districts) and districts[i]:
                    el=etree.SubElement(el,'p',{'class':'_district_2a6i4_154'})
                el.text=value
            if not item['information']:
                info[0].getparent().remove(info[0])
    states[key]=html.tostring(root,encoding='unicode').replace('viewbox=','viewBox=').replace('preserveaspectratio=','preserveAspectRatio=')
# The mobile city selector is a modal over the main stage.
states['mobile-city'] = states['mobile-main']
classes = set(re.findall(r'class="([^"]+)"',''.join(states.values())))
classes = set(' '.join(classes).split())
modules = {c.split('_')[-2] for c in classes if c.startswith('_') and len(c.split('_'))>3}
rules = json.loads((HERE/'reference-css.json').read_text())

def rem(s):
    return re.sub(r'(-?(?:\d*\.)?\d+)rem\b',lambda m:'calc('+m[1]+' * var(--ref-unit))',s)

def scoped(selector):
    result=[]
    # Original selectors have no commas inside :is/:where; preserve any future functional lists.
    for s in re.split(r',\s*(?![^()]*\))',selector):
        if '__nuxt' in s or '__layout' in s or '.lenis' in s: continue
        s=re.sub(r'^(:root|html|body)(?=[\s\[.:#>]|$)','#sharedHeader',s)
        if not s.startswith('#sharedHeader'): s='#sharedHeader '+s
        result.append(s)
    return ', '.join(result)

def rule(r):
    if 'selector' in r:
        sel=r['selector']; found=re.findall(r'\.([\w-]+)',sel)
        if found and not any(c in classes or (c.startswith('_') and len(c.split('_'))>3 and c.split('_')[-2] in modules) for c in found): return ''
        # Keep the header independent of root font-size and document height.
        if sel in ['html','body'] or '__nuxt' in sel or 'lenis' in sel: return ''
        ss=scoped(sel)
        return ss+' { '+rem(r['body'])+' }' if ss else ''
    if 'rules' in r:
        if 'prefers-color-scheme' in r['at']: return ''
        children='\n'.join(filter(None,(rule(c) for c in r['rules'])))
        return r['at']+'{\n'+children+'\n}' if children else ''
    raw=r.get('raw','')
    if raw.startswith('@font-face'): return ''
    if raw.startswith('@keyframes'): return raw
    return ''

css='\n'.join(dict.fromkeys(filter(None,(rule(r) for r in rules))))
fonts=[]
for family,names in [('TTNormsProTrial',[(400,'Regular'),(450,'Normal'),(500,'Medium')]),('TTNormsProTrlExp',[(600,'DemiBold'),(700,'Bold')])]:
    for weight,name in names:
        fonts.append(f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:normal;font-display:swap;src:url("../font/{family}-{name}.woff2") format("woff2")}}')
(OUT/'reference.css').write_text('/* Source: unistroy.ru, Kazan, 2026-10-05. Scoped, no original JS. */\n'+'\n'.join(fonts)+'\n'+css)
(OUT/'templates.js').write_text('/* Verified public menu templates, generated by qa/menu/build_header.py. */\nwindow.UNISTROY_HEADER_CATALOG = '+json.dumps(catalog,ensure_ascii=False)+';\nwindow.UNISTROY_HEADER_TEMPLATES = '+json.dumps(states,ensure_ascii=False)+';\n')
print('states:',len(states),'CSS bytes:',len(css),'modules:',len(modules))

index_path=OUT.parent/'index.html'
index=index_path.read_text()
start=index.index('<!-- SHARED_HEADER_START -->')
end=index.index('<!-- SHARED_HEADER_END -->',start)+len('<!-- SHARED_HEADER_END -->')
fallback=states['desktop-closed'].replace('Тёмная тема','Светлая тема').replace('aria-checked="true"','aria-checked="false"').replace('__active_1bglq_51','')
index=index[:start]+'<!-- SHARED_HEADER_START -->\n<div id="sharedHeader" data-theme="light">'+fallback+'</div>\n<!-- SHARED_HEADER_END -->'+index[end:]
for name in ['reference.css','header.css','templates.js','header.js']:
    digest=hashlib.sha256((OUT/name).read_bytes()).hexdigest()[:10]
    index=re.sub(r'header/'+re.escape(name)+r'(?:\?v=[a-f0-9]+)?','header/'+name+'?v='+digest,index)
index_path.write_text(index)
