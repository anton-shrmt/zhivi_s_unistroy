"""Build the handoff report from the recorded QA evidence. No browser automation."""
from pathlib import Path
from datetime import datetime, timezone
from html import escape
import json, hashlib

Q = Path(__file__).resolve().parent
ROOT = Q.parent.parent
def read(name): return json.loads((Q/name).read_text())
def esc(value): return escape(str(value), quote=True)
def link(file, label): return f'<a href="{esc(file)}">{esc(label)}</a>'

static, calc, functional = read('static.json'), read('calculator.json'), read('functional.json')
layouts = {(r['width'], r['dark']): r for r in read('layouts.json')}
menus = {(r['width'], r['dark'], r['label']): r for r in read('menus.json')}
links = read('browser-links.json')
scope = read('payload-and-scope.json')
assert len(layouts) == 12
assert all(r['pass'] for r in functional)
assert all(r['scrollWidth'] == r['width'] and not r['overflow'] and not r['brokenImages'] for r in layouts.values())
assert all(r['phonePass'] and r['locked'] for r in menus.values())
assert all(r['fixedPhone'] and not r['staleInventory'] for r in static['templates'])
assert not any(static[k] for k in ['missingResources','duplicateIds','brokenAnchors','secretPatternFiles'])
assert all(r['pass'] for r in static['javascript'])
assert all(scope.values())
assert all(not r['error'] and all(d['status']==200 for d in r['documents']) for r in links)
hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(ROOT.rglob('*')) if p.is_file() and 'qa' not in p.relative_to(ROOT).parts
          and not any(part.startswith('.') for part in p.relative_to(ROOT).parts)}
(Q/'release-manifest.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
summary = {
    'date': '2026-10-06', 'builtAt': datetime.now(timezone.utc).isoformat(),
    'baseCommit': read('baseline.json')['baseCommit'], 'indexSha256': hashes['index.html'],
    'verdict': 'Ready for developer handoff; production launch blocked by form integrations and pending approvals',
    'phone': '+7 (960) 069-30-30', 'phoneReplacementAllowed': False,
    'calculatorCases': calc['passed'], 'functionalChecks': len(functional),
    'responsiveCases': len(layouts), 'menuCasesUnique': len(menus),
    'localResources': static['localResourcesChecked'], 'browserExternalPages': len(links),
    'published': False, 'realCRMTested': False, 'realPaymentsTested': False,
    'openIssues': [
        {'priority':'P1','id':'FORMS','text':'Both form endpoints are absent. Configure and prove real receipt before launch.'},
        {'priority':'P1','id':'CALC-ASSUMPTIONS','text':'Daily model does not separately deduct operating costs; confirm rates and assumptions with business owner.'},
        {'priority':'P2','id':'PROMO-URL','text':'Inherited mobile About promo points to google.com. Correct destination requires owner confirmation.'},
        {'priority':'P2','id':'DEPLOYMENT','text':'Production domain metadata, compression/cache/CSP and Safari/Firefox/device smoke tests remain to be verified.'},
        {'priority':'SIGNOFF','id':'LEGAL','text':'Approved legal copy preserved pending lawyers; confirm operator/routing of header callback and font rights.'}
    ]
}
(Q/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

matrix = ''
for (w,dark), row in sorted(layouts.items()):
    theme='dark' if dark else 'light'
    count=sum(1 for k in menus if k[0]==w and k[1]==dark)
    shots=' · '.join(link(f'{w}-{theme}-{s}.jpg',label) for s,label in [('top','Первый экран'),('calculator','Калькулятор'),('tenants','Арендаторы'),('lead','Форма')])
    matrix+=f'<tr><td>{w} × {row["height"]}</td><td>{"Тёмная" if dark else "Светлая"}</td><td class="ok">Пройдено</td><td>{count}</td><td>{shots}</td></tr>'

names={
 'main-incomplete-phone':'Основная форма: неполный телефон отклоняется',
 'main-success':'Основная форма: успешный ответ тестового сервера',
 'main-server-error':'Основная форма: ошибка сервера, данные сохраняются',
 'main-pending-guard':'Основная форма: блокировка повторной отправки',
 'header-consent-required':'Обратный звонок: обязательное согласие',
 'header-keyboard-consent-success':'Обратный звонок: согласие с клавиатуры и отправка',
 'header-server-error':'Обратный звонок: ошибка сервера',
 'header-pending-guard':'Обратный звонок: блокировка повторной отправки',
 'calculator-arrow-key':'Калькулятор: клавиатура и фокус вкладок',
 'calculator-occupancy-ui-boundaries':'Калькулятор: границы занятости 150 / 340 дней',
 'calculator-price-clamp':'Калькулятор: ограничение стоимости 3 / 20 млн ₽',
 'calculator-transfer-to-form':'Передача выбранной модели в форму',
 'stale-form-calculation-hidden':'Устаревшая подпись расчёта скрывается после изменения',
 'faq-keyboard-single-open-and-resize':'FAQ: 10 ответов, Enter, один раскрытый ответ, изменение ширины',
 'faq-space-close':'FAQ: закрытие пробелом',
 'city-current-selection':'Выбор текущего города закрывает диалог',
 'callback-focus-trap-and-escape':'Диалог: Tab / Shift+Tab по кругу и Escape',
 'desktop-keyboard-menu-focus':'Настольное меню: Enter, Escape и возврат фокуса',
 'menu-outside-click':'Меню закрывается по клику снаружи',
 'main-consent-required':'Основная форма: обязательное согласие',
 'main-short-name':'Основная форма: слишком короткое имя',
 'main-unconnected-no-request-or-false-success':'Отключённая форма: нет запроса и ложного подтверждения',
 'anchor-navigation-reduced-motion':'8 якорей: заголовки доступны под фиксированной шапкой',
 'cta-reduced-motion':'CTA учитывает настройку уменьшения анимации'
}
checks=''.join(f'<tr><td>{esc(names.get(r.get("id",r.get("name")),r.get("id",r.get("name"))))}</td><td class="ok">Пройдено</td></tr>' for r in functional)
link_rows=''.join(f'<tr><td>{link(r["url"],r["url"].replace("https://unistroy.ru", ""))}</td><td>{esc(r["title"])}</td><td class="ok">Открывается</td></tr>' for r in links)

html=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Итоговый QA: Живи с Унистрой, 06.10.2026</title>
<style>
@font-face{{font-family:TT;src:url('../../font/TTNormsProTrial-Regular.woff2');font-display:swap}}
:root{{--dark:#364B4B;--accent:#A5FF00;--mint:#E5FFF1;--ink:#17161A;--line:rgba(54,75,75,.18)}}
*{{box-sizing:border-box}}body{{margin:0;background:#f5f8f6;color:var(--ink);font:17px/1.5 TT,system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:40px 24px 80px}}h1{{font-size:clamp(30px,4vw,48px);line-height:1.08;margin:12px 0 24px}}h2{{margin-top:38px;color:var(--dark)}}h3{{color:var(--dark)}}a{{color:#245a52;text-underline-offset:3px}}p{{max-width:1000px}}.hero{{padding:32px;background:var(--dark);color:white;border-radius:22px}}.hero a{{color:var(--accent)}}.phone{{font-size:28px;font-weight:bold;color:var(--accent)}}.badge{{font-size:13px;letter-spacing:.12em;text-transform:uppercase}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.card{{border:1px solid var(--line);border-radius:14px;background:white;padding:20px}}.card b{{display:block;font-size:32px;color:var(--dark)}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top;font-size:15px}}th{{background:var(--mint)}}td:first-child{{min-width:110px}}.ok{{color:#166346;font-weight:bold}}.pending{{background:#fff2df;border-left:4px solid #99621e;padding:16px 20px}}.evidence{{width:100%;height:auto;border:1px solid var(--line);border-radius:14px}}small{{color:#586764}}code{{overflow-wrap:anywhere}}details{{margin:20px 0}}summary{{cursor:pointer;font-weight:bold}}li{{margin:8px 0}}@media(max-width:650px){{.cards{{grid-template-columns:1fr 1fr}}main{{padding:20px 12px}}.hero{{padding:22px}}}}@media print{{details{{display:block}}.hero{{color:var(--ink);background:white}}.phone{{color:var(--ink)}}}}
</style><main>
<div class="hero"><div class="badge">Живи с Унистрой · release_header · 06.10.2026</div><h1>Итоговый QA перед передачей разработчикам</h1><p>Статический интерфейс проверен и подготовлен к передаче. Запуск приёма заявок требует подключения обеих форм и проверки реального получения данных на целевом сервере.</p><div class="phone">+7 (960) 069-30-30</div><p>Постоянный номер во всех вариантах меню и в статическом резервном HTML. Подмену номера и коллтрекинг на этой странице не подключать.</p></div>
<div class="cards"><div class="card"><b>12</b>размеров и тем</div><div class="card"><b>{calc['passed']}</b>расчётных сценария</div><div class="card"><b>{len(functional)}</b>функциональные проверки</div><div class="card"><b>95</b>локальных ресурсов</div></div>
<p>Проверена рабочая версия поверх коммита <code>{summary['baseCommit']}</code>. Изменения локальные, публикация и push не выполнялись. SHA-256 итогового <code>index.html</code>: <code>{hashes['index.html']}</code>. Полный состав версии: {link('release-manifest.json','контрольные суммы файлов')}.</p>
<h2>Что исправлено</h2><ul>
<li>Во всех 34 шаблонах закреплён телефон аренды. Генератор сохраняет его при обновлении снимков головного сайта. Удалённые ранее цены и остатки не возвращаются.</li>
<li>Основная форма больше не принимает 10 цифр вместо полного номера. Ошибки связаны с полями для вспомогательных технологий.</li>
<li>При выборе посуточной модели форма передаёт её расчёт: 95 400 ₽ вместо ошибочных 39 600 ₽ при исходных параметрах. Для неопределённой модели расчётные поля равны null. Изменение калькулятора скрывает устаревшую подпись перенесённого расчёта.</li>
<li>Обе формы блокируют повторную отправку, пока ожидают ответ. Ошибка сервера сохраняет введённые данные и позволяет повторить попытку.</li>
<li>Чекбоксы обратного звонка доступны с клавиатуры. Настольное меню сохраняет фокус после открытия. Калькулятор поддерживает стрелки, Home и End; FAQ сообщает состояние и подстраивает открытый ответ при изменении ширины.</li>
<li>Убраны переносы внутри слов заголовка формы. Изображению приложения заданы размеры и отложенная загрузка. CTA учитывают reduced motion.</li>
</ul><p>Тексты основной страницы сохранены побуквенно после нормализации пробелов. Юридические PDF, владелец формы, блок арендаторов и финансовые коэффициенты не изменены. {link('changes.diff','Изменения кода')} · {link('payload-and-scope.json','Проверка данных и границ изменений')}.</p>
<h2>Адаптив и меню</h2><p>Проверены обе темы на 320, 390, 768, 1024, 1440 и 1920 px. Горизонтальное переполнение основного содержимого, недостающие изображения и неправильные телефонные ссылки не обнаружены. Проверены город, компания, блог, клиенты, покупка, проекты, квартиры, парковки, кладовые и обратный звонок; на мобильном дополнительно основной экран и возврат по уровням. 120 обязательных комбинаций состояний, дополнительные проверки записаны отдельно.</p><div class="scroll"><table><tr><th>Экран</th><th>Тема</th><th>Геометрия</th><th>Состояний меню</th><th>Снимки</th></tr>{matrix}</table></div>
<p>{link('menus.json','Журнал меню')} · {link('layouts.json','Журнал адаптива')} · {link('390-light-form-controls.jpg','Поля формы на телефоне')}.</p>
<h2>Сценарии и данные</h2><div class="scroll"><table><tr><th>Проверка</th><th>Результат</th></tr>{checks}</table></div>
<p>Формы проверены на изолированном локальном сервере: успех 200, отказ 500 и медленный ответ. Использованы синтетические контакты; реальных отправок в CRM не было. В журнале медленного сценария ровно по одному запросу от каждой формы, реклама выключена. Первый запрос в журнале воспроизводит исходную ошибку и не считается успешным итоговым тестом.</p>
<p>Калькулятор: 3 модели × 4 типа квартиры × 2 варианта ремонта × 3 стоимости, дополнительно 2 границы занятости. Независимо проверены суммы, комиссия, округление, годовой денежный доход, рост стоимости, доходность и интерполяция окупаемости. {link('calculator.json','74 результата')} · {link('functional.json','Функциональные результаты')} · {link('mock-requests.jsonl','Локальные тестовые запросы')}.</p>
<h2>Ссылки, ресурсы и загрузка</h2><p>95 локальных ресурсов найдены; синтаксис JavaScript корректен, повторяющихся ID и битых внутренних якорей нет. Контрольные суммы трёх PDF совпадают с версиями в ссылках. В исходниках не обнаружены секреты по проверенным шаблонам; это не полноценный аудит безопасности. В хранилище браузера код сохраняет только тему.</p>
<p>61 адрес разделов головного сайта открыт в обычном браузере без страницы ошибки, в том числе все 7 способов покупки и 3 юридических адреса. При наличии ответа документа статус 200; часть переходов браузер выполнил без нового события документа. Прямые HTTP-проверки сайта получили 403, поэтому они не трактуются как битые ссылки. Внешние ссылки Telegram, VK и Rutube ответили HTTP 200. Ссылка Google работает технически, но не соответствует назначению карточки.</p>
<p>Контрольная загрузка без кеша: 14 ответов со статусом 200, около 1,71 МБ полученных данных, DOMContentLoaded около 45 мс на localhost. Ошибок загрузки и предупреждений/ошибок консоли не было. Эти цифры не характеризуют скорость на мобильной сети. Полноценные Lighthouse / Core Web Vitals на целевом сервере не измерялись. Для публикации включить сжатие и кеширование; изображения меню зависят от CDN головного сайта.</p>
<p>{link('static.json','Статический аудит')} · {link('network-final.json','Сеть и консоль')} · {link('links.json','Прямые HTTP-проверки')}.</p><details><summary>61 проверенный адрес головного сайта</summary><div class="scroll"><table><tr><th>Адрес</th><th>Страница</th><th>Результат</th></tr>{link_rows}</table></div></details>
<h2>Что остаётся перед запуском</h2><div class="pending"><strong>Передать разработчикам можно. Включать сайт как работающий канал заявок пока рано:</strong> обе формы сейчас без принимающего API. На сайте нет технической заглушки и ложного сообщения об успешной отправке, но заявки никуда не доставляются.</div>
<div class="scroll"><table><tr><th>Приоритет</th><th>Действие</th><th>Условие закрытия</th></tr>
<tr><td>P1 · интеграция</td><td>Подключить AMOCRM_CONFIG основной формы и отдельный callbackEndpoint шапки. Выбрать один путь отправки для каждой формы.</td><td>Заявка и согласия сохранены сервером, появился реальный контакт в нужной воронке; ошибки и защита от дублей проверены на целевом окружении.</td></tr>
<tr><td>P1 · расчёты</td><td>Подтвердить ставки и расходы посуточной модели. Сейчас формула не вычитает отдельные эксплуатационные издержки, хотя текст говорит о комиссии от чистой прибыли. Текущие долгосрочные ставки 2/3-комнатных: 60/70 тыс. ₽; в проектных заметках есть 55/65 тыс. ₽.</td><td>Владелец продукта подтверждает актуальные исходные данные и согласованную формулу; при изменении повторить 74 проверки.</td></tr>
<tr><td>P2 · ссылка</td><td>Согласовать адрес карточки «Комфорт начинается здесь» в мобильном меню «О компании».</td><td>Ссылка Google заменена на утверждённую целевую страницу одновременно с головным меню.</td></tr>
<tr><td>P2 · публикация</td><td>Настроить конечные og:url / og:image, HTTPS, сжатие, кеш и CSP. Исключить qa/ из публикации.</td><td>Проверены корень/подпапка, PDF, изображения, телефон, reload с якорем и обе формы на фактическом адресе.</td></tr>
<tr><td>Согласование</td><td>Юристам: оператор, документы и маршрут формы шапки, доказательства согласий. Бизнесу: 1 200 квартир, 94%, выплаты, страхование и налоговые обещания. Подтвердить права на используемые шрифты, включая файлы Trial.</td><td>Получено подтверждение ответственных. Согласованные тексты в этом QA сохранены.</td></tr>
</table></div>
<h2>Границы проверки</h2><p>Среда: macOS, встроенный Chromium-браузер Codex, программное изменение ширины окна. Версия движка через доступный API не предоставляется. Реальные iPhone/Android, экранная клавиатура, VoiceOver, Safari и Firefox не проверялись. Это не сертификат WCAG и не юридическое заключение. Перед релизом нужен короткий прогон в этих браузерах и на физических устройствах.</p><p>Эквайринг, банковское согласование, реальная доставка сообщений, серверное хранение согласий и боевой HTTPS не проверялись. В локальном стенде страница работает в корне, на основном preview в подпапке <code>/release_header/</code>. Продукционный URL после выкладки требует отдельного smoke-теста.</p>
<h2>Подтверждение номера и внешнего вида</h2><img class="evidence" src="1440-light-top.jpg" alt="Первый экран лендинга с постоянным номером +7 (960) 069-30-30 в меню"><p><small>Снимок локальной проверенной версии. Дополнительные снимки по размерам находятся в таблице выше. Отчёт и тестовый стенд входят только в материалы передачи разработчикам.</small></p>
</main></html>'''
(Q/'report.html').write_text(html)
print(json.dumps(summary,ensure_ascii=False,indent=2))
