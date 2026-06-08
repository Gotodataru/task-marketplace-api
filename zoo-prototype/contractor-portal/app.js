const routes = {
  "dashboard": renderDashboard,
  "orders": renderOrders,
  "my": renderMyOrders,
  "earnings": renderEarnings,
  "schedule": renderSchedule,
  "messages": renderMessages,
  "settings": renderSettings
};

function qs(s, el=document){ return el.querySelector(s); }
function qsa(s, el=document){ return [...el.querySelectorAll(s)]; }
function make(el, attrs={}, children=[]){
  const node = document.createElement(el);
  Object.entries(attrs).forEach(([k,v])=>{
    if(k==='class') node.className = v;
    else if(k==='html') node.innerHTML = v;
    else if(k==='onclick') node.onclick = v;
    else node.setAttribute(k,v);
  });
  children.forEach(c => node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
  return node;
}

function initTheme(){
  const saved = localStorage.getItem('theme');
  if(saved === 'dark') document.documentElement.classList.add('dark');
}
function toggleTheme(){
  const r = document.documentElement;
  r.classList.toggle('dark');
  localStorage.setItem('theme', r.classList.contains('dark') ? 'dark' : 'light');
  toast('Тема переключена');
}

const STORE = {
  ordersKey: 'zc_orders',
  myKey: 'zc_my_orders'
};

const seedOrders = [
  {id: 'A-1024', title:'Заявка: осмотр объекта', price: 1800, distance:'2.1 км', eta:'сегодня, 15:00', rating:4.8},
  {id: 'A-1027', title:'Заявка: консультация', price: 1200, distance:'5.7 км', eta:'сегодня, 18:30', rating:4.6},
  {id: 'B-2031', title:'Заявка: сопровождение', price: 2600, distance:'3.4 км', eta:'завтра, 11:00', rating:4.9},
  {id: 'C-4431', title:'Заявка: проверка документов', price: 2200, distance:'онлайн', eta:'по договорённости', rating:4.7},
];

function getOrders(){
  const raw = localStorage.getItem(STORE.ordersKey);
  if(!raw){
    localStorage.setItem(STORE.ordersKey, JSON.stringify(seedOrders));
    return [...seedOrders];
  }
  try { return JSON.parse(raw); } catch { return [...seedOrders]; }
}
function setOrders(arr){ localStorage.setItem(STORE.ordersKey, JSON.stringify(arr)); }
function getMy(){ try { return JSON.parse(localStorage.getItem(STORE.myKey)||'[]'); } catch { return []; } }
function setMy(arr){ localStorage.setItem(STORE.myKey, JSON.stringify(arr)); }

function acceptOrder(id){
  const orders = getOrders();
  const idx = orders.findIndex(o=>o.id===id);
  if(idx===-1) return;
  const order = orders.splice(idx,1)[0];
  setOrders(orders);
  const mine = getMy();
  mine.push({...order, status:'в работе'});
  setMy(mine);
  navigate('my');
  toast(`Заявка ${id} взята в работу`);
}
function rejectOrder(id){
  const orders = getOrders().filter(o=>o.id!==id);
  setOrders(orders);
  toast(`Заявка ${id} скрыта`);
}
function completeOrder(id){
  const mine = getMy();
  const idx = mine.findIndex(o=>o.id===id);
  if(idx>-1){ mine[idx].status='завершена'; setMy(mine); toast(`Заявка ${id} завершена`); renderMyOrders(true); }
}
function cancelOrder(id){
  const mine = getMy().filter(o=>o.id!==id);
  setMy(mine);
  toast(`Заявка ${id} отменена`);
}

function currency(n){ return new Intl.NumberFormat('ru-RU').format(n) + ' ₽'; }

function stat(label, value, hint){
  return make('div', {class:'stat'}, [
    make('div', {class:'col'}, [
      make('div', {class:'muted small'}, [label]),
      make('strong', {}, [value]),
      hint ? make('div', {class:'small'}, [hint]) : make('span', {class:'small'}, [' '])
    ])
  ]);
}

function cardOrder(o, actions=true){
  const c = make('div', {class:'card'});
  c.appendChild(make('div', {class:'p'}, [
    make('div', {class:'row', style:'justify-content:space-between;align-items:center'}, [
      make('div', {class:'row'}, [
        make('span', {class:'badge'}, [o.id]),
        make('strong', {}, [o.title])
      ]),
      make('div', {class:'row'}, [
        make('span', {class:'badge good'}, [currency(o.price)]),
        make('span', {class:'badge'}, [o.distance]),
        make('span', {class:'badge'}, ['★ ' + o.rating])
      ])
    ]),
    make('div', {class:'small muted', style:'margin-top:6px'}, ['Когда: ', o.eta])
  ]));
  if(actions){
    c.appendChild(make('div', {class:'p'}, [
      make('div', {class:'row'}, [
        make('button', {class:'btn', onclick:()=>acceptOrder(o.id)}, ['Взять в работу']),
        make('button', {class:'btn secondary', onclick:()=>rejectOrder(o.id)}, ['Скрыть'])
      ])
    ]));
  }
  return c;
}

function renderDashboard(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'row', style:'align-items:flex-start'}, [
    make('div', {style:'flex:2', class:'col'}, [
      make('div', {class:'section-title'}, [
        make('h2', {}, ['Личный кабинет исполнителя']),
        make('span', {class:'badge'}, ['уровень: PRO'])
      ]),
      make('div', {class:'row'}, [
        stat('Баланс за месяц', currency(getMy().reduce((s,o)=> s + (o.status==='завершена'?o.price:0),0)), 'выплачивается по пятницам'),
        stat('Заявки в работе', String(getMy().filter(o=>o.status!=='завершена').length), 'активные задачи'),
        stat('Рейтинг', '4.8', 'по 124 отзывам')
      ]),
      make('div', {class:'section-title', style:'marginTop:16px'}, [
        make('h3', {}, ['Доступные заявки']),
        make('a', {href:'#orders', class:'btn ghost', onclick:(e)=>{e.preventDefault(); navigate("orders")}}, ['Все заявки →'])
      ]),
      (function(){
        const list = make('div', {class:'list'});
        getOrders().slice(0,3).forEach(o => list.appendChild(cardOrder(o,true)));
        return list;
      })()
    ]),
    make('div', {style:'flex:1', class:'col'}, [
      make('div', {class:'card'}, [
        make('div', {class:'p'}, [
          make('strong', {}, ['Настройки быстрого доступа']),
          make('div', {class:'kv'}, [make('div', {}, ['Уведомления']), make('div', {}, [make('button', {class:'btn secondary', onclick:()=>toast('Уведомления включены')}, ['Вкл'])])]),
          make('div', {class:'kv'}, [make('div', {}, ['Автопринятие']), make('div', {}, [make('button', {class:'btn secondary', onclick:()=>toast('Правила сохранены')}, ['Правила…'])])]),
          make('div', {class:'kv'}, [make('div', {}, ['Город']), make('div', {}, [make('select', {class:'select'}, [make('option', {}, ['Москва']), make('option', {}, ['СПб']), make('option', {}, ['Екб'])])])])
        ])
      ]),
      make('div', {class:'card'}, [
        make('div', {class:'p'}, [
          make('strong', {}, ['Профиль']),
          make('div', {class:'small'}, ['Заполнено на 80%']),
          make('div', {class:'row', style:'margin-top:8px'}, [
            make('button', {class:'btn secondary', onclick:()=>navigate('settings')}, ['Настроить профиль'])
          ])
        ])
      ])
    ])
  ]));
  return wrap;
}

function renderOrders(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'section-title'}, [
    make('h2', {}, ['Доступные заявки']),
    make('div', {class:'row'}, [
      make('input', {class:'input', placeholder:'Поиск…', style:'max-width:220px'}),
      make('select', {class:'select'}, [
        make('option', {}, ['Все']), make('option', {}, ['Онлайн']), make('option', {}, ['Рядом'])
      ]),
      make('button', {class:'btn secondary', onclick:()=>{ localStorage.removeItem(STORE.ordersKey); toast('Список обновлён'); renderOrders(true);} }, ['Сбросить фильтры'])
    ])
  ]));
  const list = make('div', {class:'list'});
  getOrders().forEach(o => list.appendChild(cardOrder(o,true)));
  wrap.appendChild(list);
  return wrap;
}

function rowMyOrder(o){
  const c = make('div', {class:'card'});
  c.appendChild(make('div', {class:'p'}, [
    make('div', {class:'row', style:'justify-content:space-between;align-items:center'}, [
      make('div', {class:'row'}, [
        make('span', {class:'badge'}, [o.id]),
        make('strong', {}, [o.title]),
        make('span', {class:'badge ' + (o.status==='завершена'?'good':'')}, [o.status])
      ]),
      make('div', {class:'row'}, [
        make('span', {class:'badge good'}, [currency(o.price)]),
        make('button', {class:'btn secondary', onclick:()=>completeOrder(o.id)}, ['Завершить']),
        make('button', {class:'btn secondary', onclick:()=>cancelOrder(o.id)}, ['Отменить'])
      ])
    ])
  ]));
  return c;
}

function renderMyOrders(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'section-title'}, [
    make('h2', {}, ['Мои заявки']),
    make('div', {class:'row'}, [
      make('button', {class:'btn secondary', onclick:()=>navigate('orders')}, ['+ Взять новую'])
    ])
  ]));
  const list = make('div', {class:'list'});
  const mine = getMy();
  if(mine.length===0){
    list.appendChild(make('div', {class:'card'}, [ make('div', {class:'p'}, [ make('div', {}, ['Пока пусто. Перейдите в доступные заявки.']) ]) ]));
  } else {
    mine.forEach(o => list.appendChild(rowMyOrder(o)));
  }
  wrap.appendChild(list);
  return wrap;
}

function renderEarnings(){
  const wrap = make('div', {class:'container'});
  const mine = getMy();
  const total = mine.filter(o=>o.status==='завершена').reduce((s,o)=>s+o.price,0);
  const inProgress = mine.filter(o=>o.status!=='завершена').reduce((s,o)=>s+o.price,0);
  wrap.appendChild(make('div', {class:'section-title'}, [
    make('h2', {}, ['Доходы']),
    make('div', {class:'row'}, [
      make('span', {class:'badge'}, ['Выплата по пятницам'])
    ])
  ]));
  wrap.appendChild(make('div', {class:'row'}, [
    stat('Завершено (месяц)', currency(total)),
    stat('В работе', currency(inProgress)),
    stat('Средний чек', currency(mine.length ? Math.round((total+inProgress)/mine.length) : 0))
  ]));
  wrap.appendChild(make('h3', {}, ['История']));
  const table = make('table', {class:'table'});
  table.appendChild(make('tr', {}, [
    make('th', {}, ['ID']),
    make('th', {}, ['Название']),
    make('th', {}, ['Статус']),
    make('th', {}, ['Сумма'])
  ]));
  mine.slice().reverse().forEach(o=>{
    table.appendChild(make('tr', {}, [
      make('td', {}, [o.id]),
      make('td', {}, [o.title]),
      make('td', {}, [o.status]),
      make('td', {}, [currency(o.price)]),
    ]));
  });
  wrap.appendChild(table);
  return wrap;
}

function renderSchedule(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'section-title'}, [
    make('h2', {}, ['Расписание']),
    make('div', {class:'row'}, [
      make('button', {class:'btn secondary', onclick:()=>toast('Синхронизация календаря подключена')}, ['Подключить календарь']),
      make('button', {class:'btn secondary', onclick:()=>toast('Доступность сохранена')}, ['Задать доступность'])
    ])
  ]));
  wrap.appendChild(make('div', {class:'card'}, [
    make('div', {class:'p'}, [
      make('div', {class:'small'}, ['Пример визуализации: свободные слоты подсвечиваются пастельным зелёным.']),
      make('img', {src:'assets/cover.svg', alt:'calendar', style:'width:100%;border-radius:12px;border:1px solid var(--border)'})
    ])
  ]));
  return wrap;
}

function renderMessages(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'section-title'}, [
    make('h2', {}, ['Сообщения']),
    make('div', {class:'row'}, [
      make('input', {class:'input', placeholder:'Поиск по диалогам', style:'max-width:240px'}),
      make('button', {class:'btn secondary', onclick:()=>toast('Фильтр применён')}, ['Фильтр'])
    ])
  ]));
  wrap.appendChild(make('div', {class:'grid'}, [
    make('div', {class:'card'}, [ make('div',{class:'p'},[ make('strong',{},['Клиент #4512']), make('div',{class:'small muted'},['Новое сообщение 2 мин назад']) ]) ]),
    make('div', {class:'card'}, [ make('div',{class:'p'},[ make('strong',{},['Клиент #7144']), make('div',{class:'small muted'},['Вчера']) ]) ]),
    make('div', {class:'card'}, [ make('div',{class:'p'},[ make('strong',{},['Поддержка']), make('div',{class:'small muted'},['Ответ за 1-2 ч']) ]) ]),
  ]));
  return wrap;
}

function renderSettings(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('h2', {}, ['Настройки профиля']));
  wrap.appendChild(make('div', {class:'card'}, [
    make('div', {class:'p'}, [
      make('div', {class:'kv'}, [ make('div',{},['Имя']), make('div',{},[ make('input', {class:'input', value:'Иван'}) ]) ]),
      make('div', {class:'kv'}, [ make('div',{},['Телефон']), make('div',{},[ make('input', {class:'input', value:'+7'}) ]) ]),
      make('div', {class:'kv'}, [ make('div',{},['Город']), make('div',{},[ make('select', {class:'select'}, [ make('option',{},['Москва']), make('option',{},['СПб']), make('option',{},['Екб']) ]) ]) ]),
      make('div', {class:'kv'}, [ make('div',{},['Уведомления']), make('div',{},[ make('label', {class:'toggle', onclick:()=>toast('Настройки сохранены')}, ['Вкл/Выкл']) ]) ]),
      make('div', {class:'row', style:'margin-top:8px'}, [
        make('button', {class:'btn'}, ['Сохранить']),
        make('button', {class:'btn secondary'}, ['Отмена'])
      ])
    ])
  ]));
  return wrap;
}

function mountNav(){
  const nav = qs('#nav');
  const left = make('div', {class:'brand'}, [
    make('div', {class:'brand-badge'}, ['Z']),
    make('div', {}, ['Contractor'])
  ]);
  const tabs = make('div', {class:'tabs'});
  const list = [
    ['dashboard','Главная'],
    ['orders','Заявки'],
    ['my','Мои'],
    ['earnings','Доходы'],
    ['schedule','Расписание'],
    ['messages','Сообщения'],
    ['settings','Настройки']
  ];
  list.forEach(([key,label])=>{
    const b = make('button', {class:'tab', 'data-route': key, onclick:()=>navigate(key)}, [label]);
    tabs.appendChild(b);
  });
  const right = make('div', {class:'row'}, [
    make('button', {class:'toggle', onclick:toggleTheme}, ['☀︎/☾ Тема'])
  ]);
  nav.appendChild(make('div', {class:'nav-inner'}, [left, tabs, right]));
}

function setActiveTab(hash){
  qsa('.tab').forEach(t=>t.classList.remove('active'));
  const btn = qs(`[data-route="${hash}"]`);
  if(btn) btn.classList.add('active');
}
function navigate(hash){
  const view = qs('#view');
  const fn = routes[hash] || renderDashboard;
  view.innerHTML = '';
  view.appendChild(fn());
  setActiveTab(hash);
  window.location.hash = hash;
}

function toast(msg){
  const t = make('div', {class:'toast'}, [msg]);
  document.body.appendChild(t);
  setTimeout(()=> t.remove(), 2200);
}

window.addEventListener('hashchange', ()=>{
  const hash = (location.hash||'').replace('#','') || 'dashboard';
  navigate(hash);
});

initTheme();
document.addEventListener('DOMContentLoaded', ()=>{
  mountNav();
  const hash = (location.hash||'').replace('#','') || 'dashboard';
  navigate(hash);
});