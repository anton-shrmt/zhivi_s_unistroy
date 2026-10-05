"""Compare captured browser evidence and build a portable, offline QA report."""
from pathlib import Path
import collections, hashlib, json, re, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
rows = {r['label']: r for r in json.loads((HERE/'matrix.json').read_text())
        if len(r['label'].split('-')) == 3}
catalog = {r['label']: r for r in json.loads((HERE/'final-catalog-verification.json').read_text())}
results = []
for label, row in sorted(rows.items()):
    latest = catalog.get(label)
    ref = latest['ref'] if latest else row['ref']['text']
    local = latest['local'] if latest else row['local']['text']
    def comparable(items):
        # The canonical sales number intentionally differs from the session-specific Roistat number.
        return [x for x in items if not x['text'].startswith('+7') and x['text'] != 'Заказать звонок']
    a, b = comparable(ref), comparable(local)
    differences = []
    if len(a) != len(b): differences.append({'length': [len(a), len(b)]})
    for x, y in zip(a, b):
        d = {k: [x[k], y[k]] for k in x
             if (abs(x[k]-y[k]) > .1 if k in ['x', 'y', 'w', 'h'] else x[k] != y[k])}
        if d: differences.append({'text': x['text'], 'values': d})
    images_ok = all(x['ok'] for x in row['local']['images'])
    screenshots = all((HERE/(label+suffix)).exists() for suffix in ['-local.jpg', '-reference.png'])
    results.append({'label': label, 'comparedTextNodes': len(a), 'differences': differences,
                    'noOverflow': not row['local']['overflow'], 'imagesLoaded': images_ok,
                    'screenshotsPresent': screenshots})

old = (HERE/'source/index.before.html').read_text()
new = (ROOT/'index.html').read_text()
regression = {}
for tag in ['main','footer']:
    pattern = fr'<{tag}\b[\s\S]*?</{tag}>'
    regression[tag+'Unchanged'] = re.search(pattern, old)[0] == re.search(pattern, new)[0]
regression['legal'] = {}
for k, v in json.loads((ROOT/'policy/manifest.json').read_text()).items():
    regression['legal'][k] = (hashlib.sha256((ROOT/v['url']).read_bytes()).hexdigest() == v['sha256']
        and hashlib.sha256((ROOT.parent/'policy'/v['source']).read_bytes()).hexdigest() == v['sourceSha256'])
for name in ['header.js','templates.js']:
    subprocess.run(['node','--check',str(ROOT/'header'/name)],check=True,capture_output=True)
regression['javascriptSyntax'] = True
(HERE/'regression.json').write_text(json.dumps(regression, ensure_ascii=False, indent=2)+'\n')
summary = {'reference':'https://unistroy.ru/', 'city':'Казань', 'date':'2026-10-05',
           'browser':'Codex in-app browser / Chromium on macOS', 'toleranceCssPx':.1,
           'exclusions':['Динамический телефон Roistat и строка заказа звонка рядом с ним',
                         'Содержимое страницы за общим меню и дополнительная навигация аренды',
                         'Промежуточные кадры анимации, антиалиасинг и сжатие снимков'],
           'states':results, 'regression':regression}
(HERE/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
passed = sum(not x['differences'] and x['noOverflow'] and x['imagesLoaded'] and x['screenshotsPresent'] for x in results)
print(f'{passed}/{len(results)} states: text, typography, color, geometry, overflow, images, paired screenshots')
print('Differences:', [(x['label'],len(x['differences'])) for x in results if x['differences']])

page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка общего меню Унистрой</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf5f2;color:#263535;font:16px/1.55 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:32px}h1{font-size:clamp(28px,4vw,48px);line-height:1.1;margin:0 0 20px}h2{font-size:24px;margin:0 0 12px}p{max-width:1000px}a{color:#24625d}section{background:white;border-radius:20px;padding:24px;margin:20px 0}.eyebrow{font-size:13px;letter-spacing:.08em;color:#637676;margin-bottom:12px}.stats{display:flex;gap:16px;flex-wrap:wrap}.stat{background:#e9f0ef;padding:16px 24px;border-radius:14px}.stat b{display:block;font-size:28px}.controls{display:flex;align-items:end;gap:16px;flex-wrap:wrap;position:sticky;top:0;background:white;padding:16px 0;z-index:2}label{display:grid;gap:6px;font-size:13px}select,button{font:inherit;padding:10px 14px;border:1px solid #b7c9c5;border-radius:10px;background:white;color:#263535}input{accent-color:#345050}#stage{position:relative;width:min(100%,1440px);margin:auto;background:#d7e2df;overflow:hidden;border:1px solid #b7c9c5}#stage img{width:100%;display:block}#local{position:absolute;top:0;left:0;clip-path:inset(0 50% 0 0)}#line{position:absolute;left:50%;top:0;bottom:0;border-left:2px solid #ff6060;pointer-events:none}#stage.side{display:grid;grid-template-columns:1fr 1fr;align-items:start}#stage.side #local{position:static;clip-path:none!important}#stage.side #line{display:none}#stage.side img{min-width:0}.note{color:#637676;font-size:14px}.status{border-left:4px solid #a9ed18;padding-left:16px}.warning{border-left:4px solid #e5ad42;padding-left:16px}li{margin:7px 0}code{background:#edf3f1;padding:2px 5px;border-radius:4px}details{padding:12px 0;border-top:1px solid #e2e9e7}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:8px;border-bottom:1px solid #e1e9e6}@media(max-width:700px){main{padding:16px}section{padding:18px}.controls{position:static}#stage.side{display:block}}
</style><main><div class="eyebrow">УНИСТРОЙ · RELEASE_HEADER · 05.10.2026</div><h1>Проверка общего меню</h1>
<p>Меню лендинга приведено к зафиксированной версии головного сайта для Казани. Проверены состав, порядок, адреса, оформление и основные сценарии. Постоянная синхронизация каталога, коллтрекинг и сервер приёма заявок требуют интеграции.</p>
<section class="warning"><h2>Обновление статического меню</h2><p>После этой сверки по решению заказчика удалены счётчики доступных квартир, машино-мест и кладовых, а также цены «от». Это согласованное отличие от головного сайта. Матрица и галерея ниже относятся к предыдущей версии. <a href="price-removal.json">Проверка статического меню без цен и остатков</a> · <a href="menu-without-prices.jpg">Текущий вид меню</a>. Автообновление цен и остатков больше не требуется.</p></section><div class="stats"><div class="stat"><b>118</b>состояний интерфейса</div><div class="stat"><b>5</b>размеров экрана</div><div class="stat"><b>2</b>темы оформления</div><div class="stat"><b>PASS_COUNT / 118</b>сравнений с учётом исключений</div></div>
<section><h2>Оригинал и лендинг</h2><p class="note">Слева от красной линии показан лендинг, справа оригинал. Фон страницы под меню отличается по назначению. Ползунок позволяет увидеть совпадение границ и текста; режим «Рядом» показывает полные снимки. В нём оригинал слева, лендинг справа.</p>
<div class="controls"><label>Ширина<select id="width"><option>390</option><option>768</option><option>1280</option><option selected>1440</option><option>1920</option></select></label><label>Тема<select id="theme"><option value="light">Светлая</option><option value="dark">Тёмная</option></select></label><label>Раздел<select id="state"></select></label><label>Наложение<input id="range" type="range" min="0" max="100" value="50"></label><button id="mode">Рядом</button></div>
<p id="caption" class="note"></p><div id="stage"><img id="reference" alt="Меню головного сайта"><img id="local" alt="Меню лендинга"><div id="line"></div></div></section>
<section><h2>Что проверено</h2><ul><li>390 и 768 px: закрытая шапка, основное меню, недвижимость, 4 категории, способы покупки, о компании, блог, клиентам, города и обратный звонок.</li><li>1280, 1440 и 1920 px: закрытая шапка, 4 категории, способы покупки, о компании, блог, клиентам, города и обратный звонок.</li><li>Шрифты, размер и вес текста, цвет, координаты и размеры текстовых элементов с допуском 0,1 CSS px. Горизонтального переполнения и незагруженных изображений в проверенной матрице нет.</li><li>Открытие кликом, повторное закрытие, мобильные переходы и «Назад», Escape, Enter/Space, стрелки/Home/End, возврат фокуса, блокировка прокрутки и смена размера окна.</li><li>Форма: проверка пустых обязательных полей, согласия изначально сняты, реклама необязательна, ложного подтверждения успеха нет. Реальные заявки не отправлялись.</li><li>58 адресов головного сайта проверены HTTP-запросами; 52 успешны, 6 возвращают 500. Шесть региональных адресов возвращают 200.</li><li>Содержимое main и footer совпадает с исходной версией побайтно. Контрольные суммы трёх PDF и исходных DOCX сохранены. JavaScript проходит проверку синтаксиса.</li></ul></section>
<section><h2>Ограничения полного соответствия</h2><div class="warning"><p><strong>Безусловное «100%» не подтверждено.</strong> QA подтверждает проверенный статический интерфейс с перечисленными исключениями. Тест проводился в Chromium на macOS; отдельного прогона в Safari, Firefox и на физических телефонах не было.</p></div><ol><li><strong>Каталог меняется.</strong> Во время работы общий остаток изменился 2300 → 2301 → 2302. Финальная копия содержит 2302 квартиры, 858 однокомнатных и 608 машино-мест. Для постоянного совпадения нужен общий источник CMS.</li><li><strong>Телефон подменяется Roistat.</strong> Использован исходный номер +7 (843) 295-53-83. Персональный номер сеанса оригинала и положение строки «Заказать звонок» исключены из численного сравнения.</li><li><strong>Внешние страницы недоступны.</strong> /oplata/ipoteka, /oplata/rassrochka, /oplata/trade-in, /oplata/lizing, /oplata/materinskij-kapital, /oplata/online возвращают 500. Повторный GET и просмотр страницы ипотеки подтвердили технические работы. Адреса сохранены как в оригинале.</li><li><strong>Исходная ссылка-заглушка.</strong> Мобильная промокарточка «О компании» на головном сайте ведёт на https://google.com/. Адрес сохранён и требует согласованного исправления.</li><li><strong>Обратный звонок.</strong> Интерфейс и проверка полей готовы, сервер не подключён. Подключить обработчик/endpoint и серверное хранение согласий до запуска. Форма аренды остаётся отдельной.</li><li><strong>Динамика и доступность.</strong> Промокарточки переключаются свайпом и точками. Покадровая идентичность анимации и автопрокрутка Swiper отдельно не подтверждены. В копии исправлена работа мобильных кнопок и добавлено управление клавиатурой.</li><li><strong>Изображения и избранное.</strong> Изображения загружаются с CDN головного сайта. Персональные данные избранного не синхронизируются между доменами.</li></ol></section>
<section><h2>Материалы для разработчиков</h2><p><a href="../../header/README.md">Инструкция по компоненту</a> · <a href="summary.json">Сводка измерений</a> · <a href="behavior.json">История поведенческих проверок</a> · <a href="behavior-final.json">Финальные сценарии</a> · <a href="links.json">Проверка адресов</a> · <a href="links-get-recheck.json">Повторная проверка недоступных страниц</a> · <a href="regression.json">Проверка сохранности лендинга</a></p><p class="note">matrix.json сохраняет историю повторов, включая промежуточные ошибки. summary.json использует последний результат по состоянию и финальную проверку каталога после исправления подписей. Снимки *-local.jpg и *-reference.png соответствуют галерее. Ранние снимки *-local.png не используются в отчёте из-за ошибок масштаба при съёмке. Полное попиксельное тождество не заявляется: разные страницы за меню, динамические кадры, телефон и JPEG-сжатие создают ожидаемые отличия.</p></section>
<script>const states=STATES_DATA;const names={closed:'Шапка закрыта',main:'Основное меню',realty:'Недвижимость',projects:'Проекты',apartments:'Квартиры и апартаменты',parking:'Машино-места',storages:'Кладовые',purchase:'Способы покупки',about:'О компании',blog:'Униблог',clients:'Клиентам',city:'Города',callback:'Обратный звонок'};const $=s=>document.getElementById(s);function options(){let old=$('state').value;let all=states.filter(x=>x.label.startsWith($('width').value+'-'+$('theme').value+'-'));$('state').innerHTML=all.map(x=>{let s=x.label.split('-')[2];return '<option value="'+s+'">'+names[s]+'</option>'}).join('');$('state').value=all.some(x=>x.label.endsWith('-'+old))?old:'projects';show()}function show(){let label=[$('width').value,$('theme').value,$('state').value].join('-');$('reference').src=label+'-reference.png';$('local').src=label+'-local.jpg';$('stage').style.maxWidth=$('width').value+'px';$('caption').textContent=label+' · оригинал: unistroy.ru · лендинг: release_header'}$('width').onchange=options;$('theme').onchange=options;$('state').onchange=show;$('range').oninput=()=>{$('local').style.clipPath='inset(0 '+(100-$('range').value)+'% 0 0)';$('line').style.left=$('range').value+'%'};$('mode').onclick=()=>{$('stage').classList.toggle('side');$('mode').textContent=$('stage').classList.contains('side')?'Наложение':'Рядом'};options();</script></main></html>'''
page = page.replace('PASS_COUNT',str(passed)).replace('STATES_DATA',json.dumps(results,ensure_ascii=False))
(HERE/'report.html').write_text(page)
