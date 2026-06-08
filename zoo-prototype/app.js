const routes = {
  "catalog": renderCatalog,
  "object": renderObject,
  "login": renderLogin,
  "profile": renderProfile,
  "admin": renderAdmin
};

function qs(s, el=document){ return el.querySelector(s); }
function qsa(s, el=document){ return [...el.querySelectorAll(s)]; }

function setActiveTab(hash){
  qsa('.tab').forEach(t=>t.classList.remove('active'));
  const btn = qs(`[data-route="${hash}"]`);
  if(btn) btn.classList.add('active');
}

function navigate(hash){
  const view = qs('#view');
  const fn = routes[hash] || renderCatalog;
  view.innerHTML = '';
  view.appendChild(fn());
  setActiveTab(hash);
  window.location.hash = hash;
}

function toggleTheme(){
  const r = document.documentElement;
  r.classList.toggle('dark');
  localStorage.setItem('theme', r.classList.contains('dark') ? 'dark' : 'light');
}

function initTheme(){
  const saved = localStorage.getItem('theme');
  if(saved === 'dark'){ document.documentElement.classList.add('dark'); }
}

function make(el, attrs={}, children=[]){
  const node = document.createElement(el);
  Object.entries(attrs).forEach(([k,v])=>{
    if(k==='class') node.className = v;
    else if(k==='html') node.innerHTML = v;
    else node.setAttribute(k,v);
  });
  children.forEach(c=> node.appendChild(typeof c==='string' ? document.createTextNode(c) : c));
  return node;
}

function renderCatalog(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'hero'}, [
    make('h1', {}, ['Каталог объектов']),
    make('div', {class:'searchbar'}, [
      make('input', {class:'input', placeholder:'Поиск по каталогу…'}),
      make('select', {class:'select'}, [
        make('option', {value:''}, ['Все категории']),
        make('option', {value:'popular'}, ['Популярные']),
        make('option', {value:'new'}, ['Новые'])
      ]),
      make('button', {class:'btn'}, ['Найти'])
    ]),
  ]));
  const grid = make('div', {class:'grid'});
  const data = Array.from({length:9}).map((_,i)=>({
    title:`Объект #${i+1}`, tag: i%2===0?'Доступен':'Ожидает', desc:'Короткое описание объекта в две строки максимум.'
  }));
  data.forEach(item=>{
    const card = make('div', {class:'card'});
    card.appendChild(make('img', {src:'assets/placeholder.svg', alt:item.title}));
    const p = make('div', {class:'p'});
    p.appendChild(make('div', {class:'row',}, [
      make('strong', {}, [item.title]),
      make('span', {class:'badge'}, [item.tag])
    ]));
    p.appendChild(make('div', {class:'small'}, [item.desc]));
    p.appendChild(make('div', {class:'row', style:'margin-top:10px'}, [
      make('button', {class:'btn secondary', onclick:()=>navigate('object')}, ['Подробнее']),
      make('button', {class:'btn', onclick:()=>alert('Добавлено в избранное')}, ['В избранное']),
    ]));
    card.appendChild(p);
    grid.appendChild(card);
  });
  wrap.appendChild(grid);
  return wrap;
}

function renderObject(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('div', {class:'row'}, [
    make('div', {style:'flex:2'}, [
      make('img', {src:'assets/placeholder.svg', alt:'object', style:'width:100%;border-radius:16px;border:1px solid var(--border)'}),
      make('div', {class:'row', style:'margin-top:12px'}, [
        make('button', {class:'btn'}, ['Забронировать']),
        make('button', {class:'btn secondary'}, ['Поделиться'])
      ]),
      make('h2', {style:'margin-top:16px'}, ['Описание']),
      make('p', {}, ['Это пример карточки объекта. Здесь будет описание, характеристики и прочие детали.'])
    ]),
    make('div', {style:'flex:1'}, [
      make('div', {class:'card'}, [
        make('div', {class:'p'}, [
          make('h3', {}, ['Характеристики']),
          make('div', {class:'kv'}, [make('div', {}, ['Категория']), make('div', {}, ['Общая'])]),
          make('div', {class:'kv'}, [make('div', {}, ['Статус']), make('div', {}, ['Доступен'])]),
          make('div', {class:'kv'}, [make('div', {}, ['Рейтинг']), make('div', {}, ['4.7/5'])]),
        ])
      ]),
      make('div', {class:'card', style:'margin-top:12px'}, [
        make('div', {class:'p'}, [
          make('h3', {}, ['Отзывы']),
          make('p', {class:'small'}, ['Здесь список отзывов пользователей.']),
          make('button', {class:'btn', onclick:()=>alert('Оставить отзыв')}, ['Оставить отзыв'])
        ])
      ])
    ])
  ]));
  return wrap;
}

function renderLogin(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('h1', {}, ['Вход']));
  wrap.appendChild(make('div', {class:'card'}, [
    make('div', {class:'p'}, [
      make('div', {style:'display:grid; gap:10px'}, [
        make('input', {class:'input', placeholder:'Email'}),
        make('input', {class:'input', placeholder:'Пароль', type:'password'}),
        make('button', {class:'btn'}, ['Войти'])
      ]),
      make('p', {class:'small', style:'margin-top:8px'}, ['Нет аккаунта? ', make('a', {href:'#', onclick:(e)=>{e.preventDefault(); alert('Регистрация')}}, ['Зарегистрироваться'])])
    ])
  ]));
  return wrap;
}

function renderProfile(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('h1', {}, ['Профиль']));
  wrap.appendChild(make('div', {class:'card'}, [
    make('div', {class:'p'}, [
      make('div', {class:'kv'}, [make('div', {}, ['Имя']), make('div', {}, ['Иван'])]),
      make('div', {class:'kv'}, [make('div', {}, ['Email']), make('div', {}, ['user@example.com'])]),
      make('div', {class:'kv'}, [make('div', {}, ['Избранное']), make('div', {}, ['3 объекта'])]),
      make('hr'),
      make('button', {class:'btn secondary'}, ['Выйти'])
    ])
  ]));
  return wrap;
}

function renderAdmin(){
  const wrap = make('div', {class:'container'});
  wrap.appendChild(make('h1', {}, ['Админ-панель']));
  wrap.appendChild(make('div', {class:'row', style:'margin-bottom:12px'}, [
    make('button', {class:'btn'}, ['Новый объект']),
    make('button', {class:'btn secondary'}, ['Импорт']),
  ]));
  const table = make('div', {class:'card'}, [
    make('div', {class:'p'}, [
      make('div', {class:'row', style:'justify-content:space-between;align-items:center'}, [
        make('strong', {}, ['Объекты']),
        make('input', {class:'input', placeholder:'Поиск…', style:'max-width:260px'})
      ]),
      make('hr'),
      make('div', {class:'small'}, ['Пример списка объектов (заглушка).'])
    ])
  ]);
  wrap.appendChild(table);
  return wrap;
}

function mountNav(){
  const nav = qs('#nav');
  const routesList = [
    ['catalog','Каталог'],
    ['object','Карточка'],
    ['login','Вход'],
    ['profile','Профиль'],
    ['admin','Админ']
  ];
  const left = make('div', {class:'brand'}, [
    make('div', {class:'brand-badge'}, ['Z']),
    make('div', {}, ['Prototype'])
  ]);
  const tabs = make('div', {class:'tabs'});
  routesList.forEach(([key,label])=>{
    const b = make('button', {class:'tab', 'data-route': key, onclick:()=>navigate(key)}, [label]);
    tabs.appendChild(b);
  });
  const right = make('div', {class:'row'}, [
    make('button', {class:'toggle', onclick:toggleTheme}, ['☀︎/☾ Тема'])
  ]);
  const inner = make('div', {class:'nav-inner'}, [left, tabs, right]);
  nav.appendChild(inner);
}

window.addEventListener('hashchange', ()=>{
  const hash = (location.hash||'').replace('#','') || 'catalog';
  navigate(hash);
});

initTheme();
document.addEventListener('DOMContentLoaded', ()=>{
  mountNav();
  const hash = (location.hash||'').replace('#','') || 'catalog';
  navigate(hash);
});