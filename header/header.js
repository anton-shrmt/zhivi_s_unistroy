/* Standalone adapter for the captured Unistroy header. No vendor app, analytics or CRM scripts. */
(() => {
  'use strict';
  const host = document.getElementById('sharedHeader');
  const templates = window.UNISTROY_HEADER_TEMPLATES;
  if (!host || !templates) return;
  const wrapper = document.getElementById('siteHeader');
  const themeKey = 'unistroy-rent-header-theme-v2';
  const names = {'Казань':'city','О компании':'about','Униблог':'blog','Клиентам':'clients',
    'Недвижимость':'realty','Способы покупки':'purchase','Проекты':'projects',
    'Квартиры и апартаменты':'apartments','Машино-места':'parking','Кладовые':'storages'};
  const cities = {'Казань':'','Санкт-Петербург':'spb','Екатеринбург':'ekb','Тольятти':'tlt',
    'Махачкала':'mhchkala','Пермь':'perm','Нижний Новгород':'nn'};
  const realty = ['projects','apartments','parking','storages'];
  let state = 'closed';
  let modal = null;
  let mobile = innerWidth < 1280;
  let layout = innerWidth<768?'mobile':mobile?'tablet':'desktop';
  let dark = matchMedia('(prefers-color-scheme:dark)').matches;
  try { const saved = localStorage.getItem(themeKey); if (saved) dark = saved === 'dark'; } catch {}
  let lock = null;
  let hoverTimer = 0;
  let openedByHover = false;
  let returnAction = 'burger';
  let swipe = null;
  let swipeConsumed = false;

  function action(el, name) {
    if (!el) return;
    el.dataset.action = name;
    if (!['BUTTON','A','INPUT','LABEL'].includes(el.tagName)) { el.setAttribute('role','button'); el.tabIndex=0; }
    if (name in templates || Object.values(names).includes(name) || name==='burger') {
      el.setAttribute('aria-expanded',String(name===state || name==='realty' && realty.includes(state) || name==='burger' && state!=='closed'));
    }
  }
  function syncTheme() {
    host.dataset.theme = dark ? 'dark' : 'light';
    document.documentElement.classList.toggle('header-dark-mode',dark);
    host.querySelectorAll('[role="switch"]').forEach(el => {
      el.setAttribute('aria-checked',String(dark));
      el.classList.toggle('__active_1bglq_51',dark);
      const input=el.querySelector('input'); if(input) input.checked=dark;
      el.querySelectorAll('._label_h3zi8_19').forEach(e=>e.textContent=dark?'Тёмная тема':'Светлая тема');
    });
  }
  function syncScroll() { host.querySelector('._HeaderNavigation_p8zyz_15')?.classList.toggle('__scrolling_opi8c_50',scrollY>0); }
  window.addEventListener('scroll',syncScroll,{passive:true});
  function syncLock() {
    const open=state!=='closed'||modal;
    wrapper.classList.toggle('ref-open',!!open);
    if (open && !lock) {
      lock={overflow:document.body.style.overflow,paddingRight:document.body.style.paddingRight};
      const gap=innerWidth-document.documentElement.clientWidth;
      if(gap) document.body.style.paddingRight=gap+'px';
      document.body.style.overflow='hidden';
    } else if(!open && lock) {
      Object.assign(document.body.style,lock); lock=null;
    }
  }
  function decorate() {
    host.querySelectorAll('._MenuTab_xihyy_15 > ._link_xihyy_19').forEach(el => {
      const name=names[el.textContent.trim()]; if(name) action(el,name);
    });
    host.querySelectorAll('button').forEach(el=>{
      const text=el.textContent.trim(), label=el.getAttribute('aria-label');
      if(names[text]) action(el,names[text]);
      if(label==='Открыть меню'||label==='Закрыть меню') action(el,'burger');
      if(text==='Назад') action(el,'back');
      if(text==='Заказать звонок') action(el,'callback');
      if(el.className.includes('_CloseButton')) {action(el,'close-modal');el.setAttribute('aria-label','Закрыть окно');}
    });
    host.querySelectorAll('._item_s8tre_28:not(a), ._category_f3pe3_44').forEach(el=>{
      const name=names[el.textContent.trim()]; if(name) action(el,name);
    });
    // Desktop category controls are VLink elements without href.
    host.querySelectorAll('._MainMenuList_f3pe3_15 [class*="_VLink_"]').forEach(el=>{
      const name=names[el.textContent.trim()]; if(name && !el.closest('a')) action(el,name);
    });
    host.querySelectorAll('[role="switch"]').forEach(el=>action(el,'theme'));
    host.querySelectorAll('._overlay_eh7mv_16').forEach(el=>action(el,'close'));
    host.querySelectorAll('._overlay_1abu0_43').forEach(el=>action(el,'close-modal'));
    host.querySelectorAll('._overlay_eh7mv_16, ._overlay_1abu0_43').forEach(el=>{el.tabIndex=-1;el.setAttribute('aria-hidden','true');});
    host.querySelectorAll('._VSelectOption_ivyab_15').forEach(el=>{
      const text=el.textContent.trim(); if(text in cities) {
        action(el,'city:'+cities[text]); el.setAttribute('aria-label',text);
        el.querySelectorAll('input').forEach(x=>{x.tabIndex=-1;x.setAttribute('aria-hidden','true');});
      }
    });
    host.querySelectorAll('a[href*="/favorites"]').forEach(el=>{el.removeAttribute('disabled');el.setAttribute('aria-label','Перейти в избранное');});
    const logo=host.querySelector('._link_p8zyz_78');
    if(logo && logo.tagName!=='A') {const a=document.createElement('a');a.className=logo.className;a.href='https://unistroy.ru/';a.setAttribute('aria-label','Унистрой, главная');a.innerHTML=logo.innerHTML;logo.replaceWith(a);}
    const dialog=host.querySelector('._VModal_1abu0_15');
    if(dialog) {dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label',modal==='city'?'Город':'Оставьте заявку на консультацию');}
    const form=host.querySelector('form');
    if(form) {
      form.noValidate=true;
      form.querySelectorAll('input').forEach(el=>{
        el.id='header-'+el.name;
        if(el.name==='name') {el.required=true;el.autocomplete='name';el.setAttribute('aria-label','Имя');}
        if(el.name==='phone') {el.required=true;el.autocomplete='tel';el.setAttribute('aria-label','Телефон');}
        if(el.name==='personal-consent') {el.required=true;el.setAttribute('aria-label','Согласие на обработку персональных данных');}
        if(el.name==='distribution-consent') el.setAttribute('aria-label','Согласие на рекламные сообщения');
        if(el.name==='taxi') el.setAttribute('aria-label','Хочу добраться на такси');
      });
    }
  }
  function slideTo(index) {
    host.querySelectorAll('.swiper').forEach(slider=>{
      const slides=[...slider.querySelectorAll('.swiper-slide')];
      const selected=Math.min(index,slides.length-1);
      slides.forEach((el,i)=>{
        el.style.width=Math.round(slider.getBoundingClientRect().width)+'px';
        el.style.transform=`translate3d(${-i*100}%,0,0)`;
        el.style.opacity=i===selected?'1':'0';el.style.pointerEvents=i===selected?'auto':'none';
        el.inert=i!==selected;el.classList.toggle('swiper-slide-active',i===selected);
      });
    });
    host.querySelectorAll('.swiper-pagination-bullet').forEach((el,i)=>{el.classList.toggle('swiper-pagination-bullet-active',i===index);el.setAttribute('aria-pressed',String(i===index));});
  }
  function render(focusAction) {
    const key=state==='closed'?'desktop-closed':(mobile?(innerWidth>=768 && templates['tablet-'+state]?'tablet-':'mobile-'):'desktop-')+(state==='realty'&&!mobile?'projects':state);
    host.innerHTML=templates[key] || templates['desktop-closed'];
    if(modal) host.insertAdjacentHTML('beforeend',templates[modal==='city'&&innerWidth>=768?'city-tablet-modal':modal+'-modal']);
    host.dataset.state=state;
    decorate();syncTheme();syncLock();syncScroll();
    host.querySelectorAll('.swiper-pagination-bullet').forEach((el,i)=>{action(el,'slide:'+i);el.setAttribute('aria-label','Слайд '+(i+1));});
    slideTo(0);
    if(focusAction) [...host.querySelectorAll(`[data-action="${focusAction}"]`)].find(el=>el.getClientRects().length)?.focus({preventScroll:true});
    if(modal) host.querySelector('[role="dialog"] button')?.focus({preventScroll:true});
    document.documentElement.style.setProperty('--header-offset',wrapper.getBoundingClientRect().height+'px');
  }
  function close() {
    clearTimeout(hoverTimer);modal=null;state='closed';openedByHover=false;render(mobile?'burger':returnAction);
  }
  function activate(name, fromKeyboard=false) {
    clearTimeout(hoverTimer);
    if(name.startsWith('slide:')) {slideTo(Number(name.slice(6)));return;}
    if(name==='theme') {dark=!dark;try{localStorage.setItem(themeKey,dark?'dark':'light')}catch{}syncTheme();return;}
    if(name==='close') {close();return;}
    if(name==='close-modal') {modal=null;render(returnAction);return;}
    if(name==='callback') {returnAction='callback';modal='callback';render();return;}
    if(name.startsWith('city:')) {
      const code=name.slice(5);
      if(!code){modal=null;if(!mobile) state='closed';render('city');}
      else location.assign('https://unistroy.ru/'+code);
      return;
    }
    if(name==='burger') {returnAction='burger';state=state==='closed'?'main':'closed';modal=null;render('burger');return;}
    if(name==='back') {state=realty.includes(state)?'realty':'main';render();host.querySelector('[data-action="back"], [data-action="burger"]')?.focus({preventScroll:true});return;}
    if(name==='city'&&mobile) {returnAction='city';modal='city';render();return;}
    const target=name==='realty'&&!mobile?'projects':name;
    if(!mobile && state===target && !openedByHover && !realty.includes(name)) {close();return;}
    openedByHover=false;returnAction=name;state=target;render(name);
    if(mobile) host.querySelector('[data-action="back"]')?.focus({preventScroll:true});
  }
  host.addEventListener('click',event=>{
    if(swipeConsumed) {event.preventDefault();swipeConsumed=false;return;}
    const el=event.target.closest('[data-action]');
    if(el) {event.preventDefault();activate(el.dataset.action,event.detail===0);return;}
    const link=event.target.closest('a'); if(link) {clearTimeout(hoverTimer);}
  });
  host.addEventListener('dragstart',event=>{if(event.target.closest('.swiper'))event.preventDefault();});
  host.addEventListener('pointerdown',event=>{
    const slider=event.target.closest('.swiper');
    if(slider) swipe={x:event.clientX,y:event.clientY,slider};
  });
  window.addEventListener('pointerup',event=>{
    if(!swipe) return;
    const dx=event.clientX-swipe.x,dy=event.clientY-swipe.y;
    const slides=[...swipe.slider.querySelectorAll('.swiper-slide')];
    if(Math.abs(dx)>30&&Math.abs(dx)>Math.abs(dy)&&slides.length>1) {
      const current=slides.findIndex(el=>el.classList.contains('swiper-slide-active'));
      slideTo((current+(dx<0?1:slides.length-1))%slides.length);swipeConsumed=true;
      // Suppress only the click produced by this drag, never the next unrelated click.
      setTimeout(()=>{swipeConsumed=false;},0);
    }
    swipe=null;
  });
  window.addEventListener('pointercancel',()=>{swipe=null;});
  host.addEventListener('keydown',event=>{
    const el=event.target.closest('[data-action]');
    if(el && ['Enter',' '].includes(event.key) && !['BUTTON','A'].includes(el.tagName)) {event.preventDefault();activate(el.dataset.action,true);}
    if(el && realty.includes(el.dataset.action) && ['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
      event.preventDefault();const idx=realty.indexOf(el.dataset.action);
      const next=event.key==='Home'?0:event.key==='End'?3:(idx+(event.key==='ArrowDown'?1:3))%4;
      state=realty[next];render(state);
    }
  });
  host.addEventListener('pointermove',event=>{
    if(mobile||modal||event.pointerType==='touch') return;
    clearTimeout(hoverTimer);
    const el=event.target.closest('[data-action]');
    if(!el || !Object.values(names).includes(el.dataset.action) || el.dataset.action==='city') return;
    const next=el.dataset.action==='realty'?'projects':el.dataset.action;
    if(state===next) return;
    hoverTimer=setTimeout(()=>{state=next;returnAction=el.dataset.action;openedByHover=true;render();},120);
  });
  // The overlay is the explicit outside-click target; crossing the gap never closes a panel.
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape' && (state!=='closed'||modal)) {event.preventDefault(); if(modal){modal=null;render(returnAction)}else close();}
    if(event.key==='Tab' && (mobile&&state!=='closed'||modal)) {
      const scope=modal?host.querySelector('[role="dialog"]'):host;
      const els=[...scope.querySelectorAll('a[href],button,input,[tabindex="0"]')].filter(el=>el.getClientRects().length&&!el.disabled&&el.tabIndex>=0);
      const first=els[0],last=els[els.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }
  });
  host.addEventListener('change',event=>{
    const input=event.target;
    if(input.type==='checkbox') input.closest('label')?.classList.toggle('__active_kacqt_257',input.checked);
  });
  host.addEventListener('submit',async event=>{
    event.preventDefault();
    const form=event.target;
    if(form.dataset.submitting==='true') return;
    const name=form.elements.name,phone=form.elements.phone,consent=form.elements['personal-consent'];
    const phoneDigits=phone.value.replace(/\D/g,'').replace(/^8/,'7');
    const invalid=name.value.trim().length<2?name:!/^7\d{10}$/.test(phoneDigits)?phone:!consent.checked?consent:null;
    form.querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid'));
    form.querySelectorAll('[aria-describedby="header-form-error"]').forEach(el=>el.removeAttribute('aria-describedby'));
    form.querySelector('.ref-form-error')?.remove();
    if(invalid) {
      invalid.setAttribute('aria-invalid','true');invalid.setAttribute('aria-describedby','header-form-error');invalid.focus();
      const p=document.createElement('p');p.id='header-form-error';p.className='ref-form-error';p.role='alert';
      p.textContent=invalid===consent?'Подтвердите согласие на обработку персональных данных.':'Укажите имя и телефон в формате +7 999 999-99-99.';
      form.append(p);return;
    }
    const detail={name:name.value.trim(),phone:'+'+phoneDigits,city:'kzn',taxi:form.elements.taxi.checked,
      consent:{personalData:true,marketing:form.elements['distribution-consent'].checked,capturedAt:new Date().toISOString()},source:'shared-header'};
    host.dispatchEvent(new CustomEvent('unistroy:callback-ready',{bubbles:true,detail}));
    const endpoint=window.UNISTROY_HEADER_CONFIG?.callbackEndpoint;
    if(!endpoint) return;
    form.dataset.submitting='true';form.setAttribute('aria-busy','true');
    const submit=form.querySelector('[type="submit"]');submit.disabled=true;
    try {
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(detail)});
      if(!response.ok) throw new Error('callback');
      form.innerHTML='<p class="ref-form-success" role="status">Заявка отправлена. Мы свяжемся с вами в ближайшее время.</p>';
    }catch{const p=document.createElement('p');p.className='ref-form-error';p.role='alert';p.textContent='Не удалось отправить заявку. Попробуйте ещё раз.';form.append(p);}
    finally{delete form.dataset.submitting;form.removeAttribute('aria-busy');if(submit.isConnected)submit.disabled=false;}
  });
  window.addEventListener('resize',()=>{const next=innerWidth<768?'mobile':innerWidth<1280?'tablet':'desktop';if(next!==layout){layout=next;mobile=innerWidth<1280;close();}else{const active=[...host.querySelectorAll('.swiper-slide')].findIndex(el=>el.classList.contains('swiper-slide-active'));slideTo(Math.max(0,active));}document.documentElement.style.setProperty('--header-offset',wrapper.getBoundingClientRect().height+'px');});
  render();
})();
