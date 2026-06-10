/* ============================================================
   ЖИВИ С УНИСТРОЙ — interactive logic
   ============================================================ */

/* ---- CONFIG: все коэффициенты в одном месте — ЗАМЕНИТЬ на реальные ---- */
const CONFIG = {
  baseRentMonthly: { studio: 40000, r1: 45000, r2: 60000, r3: 70000 }, // долгосрочная, ₽/мес (тип ремонта «Комфорт»)
  dailyRateByType: { studio: 5000, r1: 5000, r2: 5000, r3: 5000 },     // посуточная, ₽/сутки — пока единая ставка для всех типов
  dailyDaysPerYear: 265,       // занятость посуточной, суток в год
  guaranteedShare: 0.75,       // гарант. платёж = 75% рыночной долгосрочной (комиссия 25% в ставке)
  commission: { longterm: 0.12, daily: 0.28, guaranteed: 0 }, // комиссия УК
  renovationFactor: { comfort: 1.0, business: 1.15 }, // тип ремонта: «Бизнес» = +15% к ставке (все модели)
  appreciationYearly: 0.10,    // капитализация: удорожание недвижимости в год
  price: { min: 3000000, max: 20000000, step: 100000, default: 6500000 } // диапазон стоимости — ЗАМЕНИТЬ
};

const TYPE_LABEL = { studio: 'Студия', r1: '1-комнатная', r2: '2-комнатная', r3: '3-комнатная' };
const MODEL_LABEL = { longterm: 'Долгосрочная', daily: 'Посуточная', guaranteed: 'Гарантированная' };

/* ---- formatters ---- */
const fmtRub = n => Math.round(n / 1000) * 1000;
const nf = new Intl.NumberFormat('ru-RU');
const money = n => nf.format(fmtRub(n));
const num = n => nf.format(Math.round(n));
const one = n => (Math.round(n * 10) / 10).toLocaleString('ru-RU');

/* ---- calculator state ---- */
const state = {
  model: 'longterm',
  type: 'r1',
  price: CONFIG.price.default,
  condition: 'comfort',
  days: CONFIG.dailyDaysPerYear
};

function compute() {
  const { model, type, price, condition, days } = state;
  const cf = CONFIG.renovationFactor[condition];
  let gross = 0, commissionRate = 0, net = 0;

  if (model === 'longterm') {
    gross = CONFIG.baseRentMonthly[type] * cf;
    commissionRate = CONFIG.commission.longterm;
    net = gross * (1 - commissionRate);
  } else if (model === 'daily') {
    gross = CONFIG.dailyRateByType[type] * days * cf / 12; // месячная ставка из годовой занятости
    commissionRate = CONFIG.commission.daily;
    net = gross * (1 - commissionRate);
  } else { // guaranteed
    gross = CONFIG.baseRentMonthly[type] * cf;          // рыночная база
    net = gross * CONFIG.guaranteedShare;               // фикс = 85%, комиссия зашита
    commissionRate = CONFIG.guaranteedShare;            // для отображения «доля выплаты»
  }

  const monthly = net;
  const yearlyCash = monthly * 12;                          // живые арендные деньги за год
  const appreciation = price * CONFIG.appreciationYearly;   // капитализация — удорожание квартиры
  const yearly = yearlyCash + appreciation;                 // доход в год с учётом капитализации
  const yieldPct = price > 0 ? (yearly / price) * 100 : 0;  // доходность (за первый год) с капитализацией
  const payback = paybackYears(price, yearlyCash);          // окупаемость: аренда + сложная капитализация
  const commissionAmount = gross - net;

  return { gross, monthly, yearly, yieldPct, payback, commissionRate, commissionAmount, model };
}

/* Окупаемость с учётом капитализации: квартира дорожает на 10% к стоимости
   предыдущего года (сложный процент), аренда — по текущей ставке.
   Внутри последнего года — линейная интерполяция до десятых. */
function paybackYears(price, yearlyCash) {
  if (price <= 0) return 0;
  let acc = 0, value = price;
  for (let y = 0; y < 100; y++) {
    const income = yearlyCash + value * CONFIG.appreciationYearly;
    if (income <= 0) return 0;
    if (acc + income >= price) return y + (price - acc) / income;
    acc += income;
    value *= 1 + CONFIG.appreciationYearly;
  }
  return 100;
}

/* ---- render ---- */
function render() {
  const r = compute();

  setText('resIncome', money(r.monthly));
  setText('resYearly', money(r.yearly) + ' ₽');
  setText('resYield', one(r.yieldPct) + '%');
  const pb = Math.round(r.payback * 10) / 10;
  // дробные значения («20,5») по-русски всегда «года»; целые склоняются как обычно
  setText('resPayback', one(r.payback) + ' ' + (Number.isInteger(pb) ? plural(pb, ['год','года','лет']) : 'года'));
  setText('resType', money(r.gross) + ' ₽');
  setText('resTypeK', state.model === 'guaranteed' ? 'Рыночная ставка' : 'Ставка до комиссии');

  // commission row
  const commWrap = document.getElementById('resCommission');
  if (state.model === 'guaranteed') {
    commWrap.querySelector('.ck').textContent = 'Гарантированный платёж';
    commWrap.querySelector('.cv').textContent = Math.round(CONFIG.guaranteedShare * 100) + '% от рыночной ставки';
  } else {
    commWrap.querySelector('.ck').textContent = 'Комиссия Унистрой ' + Math.round(r.commissionRate * 100) + '%';
    commWrap.querySelector('.cv').textContent = '− ' + money(r.commissionAmount) + ' ₽ / мес';
  }

  // guaranteed flag
  document.getElementById('resFlag').classList.toggle('show', state.model === 'guaranteed');

  // occupancy field visibility
  document.getElementById('occField').classList.toggle('show', state.model === 'daily');

  // highlight relevant comparison card
  document.querySelectorAll('.comp-card').forEach(c => {
    c.classList.toggle('feature', c.dataset.model === state.model);
  });

  // pulse animation on key number
  const inc = document.getElementById('resIncome');
  inc.style.color = '#A5FF00';
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function plural(n, forms) {
  n = Math.round(n);
  const n10 = n % 10, n100 = n % 100;
  if (n10 === 1 && n100 !== 11) return forms[0];
  if (n10 >= 2 && n10 <= 4 && (n100 < 10 || n100 >= 20)) return forms[1];
  return forms[2];
}

/* ---- wire calculator controls ---- */
function initCalculator() {
  // model segment
  document.querySelectorAll('#modelSeg button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#modelSeg button').forEach(b => b.setAttribute('aria-selected', 'false'));
      btn.setAttribute('aria-selected', 'true');
      state.model = btn.dataset.model;
      render();
    });
  });

  // type chips
  document.querySelectorAll('#typeChips .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#typeChips .chip').forEach(c => c.setAttribute('aria-pressed', 'false'));
      chip.setAttribute('aria-pressed', 'true');
      state.type = chip.dataset.type;
      render();
    });
  });

  // condition chips
  document.querySelectorAll('#condChips .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#condChips .chip').forEach(c => c.setAttribute('aria-pressed', 'false'));
      chip.setAttribute('aria-pressed', 'true');
      state.condition = chip.dataset.cond;
      render();
    });
  });

  // price slider + input sync
  const slider = document.getElementById('priceSlider');
  const input = document.getElementById('priceInput');
  slider.min = CONFIG.price.min; slider.max = CONFIG.price.max; slider.step = CONFIG.price.step;
  slider.value = state.price;
  input.value = nf.format(state.price);
  document.getElementById('priceMin').textContent = nf.format(CONFIG.price.min) + ' ₽';
  document.getElementById('priceMax').textContent = nf.format(CONFIG.price.max) + ' ₽';

  slider.addEventListener('input', () => {
    state.price = +slider.value;
    input.value = nf.format(state.price);
    render();
  });
  input.addEventListener('input', () => {
    let v = +input.value.replace(/\D/g, '');
    if (isNaN(v)) v = CONFIG.price.min;
    state.price = v;
    slider.value = Math.min(Math.max(v, CONFIG.price.min), CONFIG.price.max);
    render();
  });
  input.addEventListener('blur', () => {
    let v = Math.min(Math.max(state.price, CONFIG.price.min), CONFIG.price.max);
    state.price = v; slider.value = v; input.value = nf.format(v);
    render();
  });

  // occupancy slider (суток в год)
  const occ = document.getElementById('occSlider');
  occ.value = state.days;
  document.getElementById('occVal').textContent = occ.value + ' суток/год';
  occ.addEventListener('input', () => {
    state.days = +occ.value;
    document.getElementById('occVal').textContent = occ.value + ' суток/год';
    render();
  });

  render();
}

/* ---- "Оставить заявку с этим расчётом" ---- */
function applyCalcToForm() {
  const modelSel = document.getElementById('fModel');
  if (modelSel) modelSel.value = state.model;
  const r = compute();
  const note = document.getElementById('formCalcNote');
  if (note) {
    note.textContent = `${MODEL_LABEL[state.model]} · ${TYPE_LABEL[state.type]} · доход ≈ ${money(r.monthly)} ₽/мес`;
    note.style.display = 'block';
  }
  document.getElementById('lead').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---- accordion ---- */
function initFaq() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const q = item.querySelector('.faq-q');
    const a = item.querySelector('.faq-a');
    q.addEventListener('click', () => {
      const open = item.classList.contains('open');
      // close others
      document.querySelectorAll('.faq-item.open').forEach(o => {
        if (o !== item) { o.classList.remove('open'); o.querySelector('.faq-a').style.maxHeight = null; o.querySelector('.faq-q').setAttribute('aria-expanded','false'); }
      });
      item.classList.toggle('open', !open);
      q.setAttribute('aria-expanded', String(!open));
      a.style.maxHeight = open ? null : a.scrollHeight + 'px';
    });
  });
}

/* ---- sticky header shrink ---- */
function initHeader() {
  const header = document.getElementById('siteHeader');
  const onScroll = () => header.classList.toggle('shrink', window.scrollY > 30);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/* ---- mobile menu ---- */
function initMenu() {
  const burger = document.getElementById('burger');
  const menu = document.getElementById('mobileMenu');
  const backdrop = document.getElementById('menuBackdrop');
  const toggle = (open) => {
    burger.classList.toggle('open', open);
    menu.classList.toggle('open', open);
    backdrop.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  };
  burger.addEventListener('click', () => toggle(!menu.classList.contains('open')));
  backdrop.addEventListener('click', () => toggle(false));
  menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => toggle(false)));
}

/* ---- scroll reveal ---- */
function initReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { els.forEach(e => e.classList.add('in')); return; }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
  els.forEach(e => io.observe(e));
}

/* ---- form validation (заглушка) ---- */
function initForm() {
  const form = document.getElementById('leadForm');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    let ok = true;

    const name = form.querySelector('#fName');
    const phone = form.querySelector('#fPhone');
    const consent = form.querySelector('#fConsent');

    setFieldError(name, name.value.trim().length >= 2 ? '' : 'Укажите имя');
    if (name.value.trim().length < 2) ok = false;

    const phoneClean = phone.value.replace(/\D/g, '');
    const phoneOk = phoneClean.length >= 10;
    setFieldError(phone, phoneOk ? '' : 'Укажите корректный телефон');
    if (!phoneOk) ok = false;

    const consentWrap = consent.closest('.consent');
    consentWrap.classList.toggle('error', !consent.checked);
    if (!consent.checked) ok = false;

    if (!ok) return;

    // заглушка успеха
    document.getElementById('formFields').style.display = 'none';
    document.getElementById('formSuccess').classList.add('show');
  });

  // phone mask (light)
  const phone = form.querySelector('#fPhone');
  phone.addEventListener('input', () => {
    let d = phone.value.replace(/\D/g, '').slice(0, 11);
    if (d.startsWith('8')) d = '7' + d.slice(1);
    if (d && !d.startsWith('7')) d = '7' + d;
    let out = '+7';
    if (d.length > 1) out += ' (' + d.slice(1, 4);
    if (d.length >= 4) out += ') ' + d.slice(4, 7);
    if (d.length >= 7) out += '-' + d.slice(7, 9);
    if (d.length >= 9) out += '-' + d.slice(9, 11);
    phone.value = out;
  });
}

function setFieldError(input, msg) {
  const wrap = input.closest('.form-field');
  wrap.classList.toggle('error', !!msg);
  const em = wrap.querySelector('.err-msg');
  if (em) em.textContent = msg;
}

/* ---- smooth scroll buttons ---- */
function initScrollLinks() {
  document.querySelectorAll('[data-scroll]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const target = document.querySelector(btn.getAttribute('data-scroll'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });
  const applyBtn = document.getElementById('applyCalcBtn');
  if (applyBtn) applyBtn.addEventListener('click', applyCalcToForm);
}

/* ---- init ---- */
function boot() {
  initCalculator();
  initFaq();
  initHeader();
  initMenu();
  initReveal();
  initForm();
  initScrollLinks();
}

// Runs whether the DOM is still loading (normal page load) OR already parsed
// (e.g. when content is injected after DOMContentLoaded, as in the bundled file).
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
