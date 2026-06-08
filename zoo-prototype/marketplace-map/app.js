
const routes={home:renderHome,new:renderNew,my:renderMy,map:renderMap};
function qs(s,e=document){return e.querySelector(s)}
function qsa(s,e=document){return [...e.querySelectorAll(s)]}
function make(el,a={},c=[]){const n=document.createElement(el);Object.entries(a).forEach(([k,v])=>{if(k==='class')n.className=v;else if(k==='onclick')n.onclick=v;else n.setAttribute(k,v)});(c||[]).forEach(ch=>n.appendChild(typeof ch==='string'?document.createTextNode(ch):ch));return n}
function toast(m){const t=make('div',{class:'toast'},[m]);document.body.appendChild(t);setTimeout(()=>t.remove(),2000)}
function mountNav(){const nav=qs('#nav');const tabs=make('div',{class:'tabs'});[['home','Главная'],['new','Новое задание'],['my','Мои'],['map','Карта']].forEach(([k,l])=>tabs.appendChild(make('button',{class:'tab','data-route':k,onclick:()=>navigate(k)},[l])));nav.appendChild(make('div',{class:'nav-inner'},[make('div',{},['Marketplace']),tabs]))}
function navigate(h){const v=qs('#view');v.innerHTML='';(routes[h]||renderHome)(v);qsa('.tab').forEach(t=>t.classList.remove('active'));const b=qs(`[data-route="${h}"]`);if(b)b.classList.add('active');location.hash=h}
function load(){return JSON.parse(localStorage.getItem('tasks')||'[]')}
function save(d){localStorage.setItem('tasks',JSON.stringify(d))}
function uid(){return Math.random().toString(36).slice(2,7).toUpperCase()}
function renderHome(v){v.appendChild(make('div',{class:'container'},[make('h2',{},['Главная']),make('p',{},['Создайте задание или смотрите на карте'])]))}
let newMarker=null;
function renderNew(v){const wrap=make('div',{class:'container'});wrap.appendChild(make('h2',{},['Новое задание']));const form=make('div',{class:'card'},[make('div',{class:'p'},[make('input',{id:'title',class:'input',placeholder:'Название'}),make('input',{id:'price',class:'input',type:'number',placeholder:'Цена'}),make('textarea',{id:'desc',class:'textarea',placeholder:'Описание'}),make('button',{class:'btn',onclick:saveNew},['Сохранить'])])]);const mapBox=make('div',{id:'map-new',class:'map'});wrap.appendChild(form);wrap.appendChild(mapBox);v.appendChild(wrap);setTimeout(initMapNew,0)}
function initMapNew(){const m=L.map('map-new').setView([55.75,37.61],11);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);m.on('click',e=>{if(newMarker)newMarker.setLatLng(e.latlng);else newMarker=L.marker(e.latlng).addTo(m)})}
function saveNew(){const t=qs('#title').value,p=+qs('#price').value,d=qs('#desc').value;if(!t||!p||!newMarker){toast('Заполните поля и выберите точку');return}const {lat,lng}=newMarker.getLatLng();const tasks=load();tasks.push({id:'T-'+uid(),title:t,price:p,desc:d,lat,lng});save(tasks);toast('Сохранено');navigate('my')}
function renderMy(v){const wrap=make('div',{class:'container'});wrap.appendChild(make('h2',{},['Мои задания']));load().forEach(t=>{const c=make('div',{class:'card'},[make('div',{class:'p'},[make('strong',{},[t.title]),make('div',{},[t.price+' ₽']),make('div',{id:'map-'+t.id,class:'map'})])]);wrap.appendChild(c);setTimeout(()=>{const m=L.map('map-'+t.id).setView([t.lat,t.lng],13);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);L.marker([t.lat,t.lng]).addTo(m)},0)});v.appendChild(wrap)}
function renderMap(v){const wrap=make('div',{class:'container'});wrap.appendChild(make('h2',{},['Задания на карте']));const mapBox=make('div',{id:'map-browse',class:'map'});wrap.appendChild(mapBox);v.appendChild(wrap);setTimeout(()=>{const tasks=load();const m=L.map('map-browse').setView([55.75,37.61],11);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);tasks.forEach(t=>{L.marker([t.lat,t.lng]).addTo(m).bindPopup(t.title+' '+t.price+'₽')})},0)}
window.addEventListener('hashchange',()=>navigate(location.hash.replace('#','')))
document.addEventListener('DOMContentLoaded',()=>{mountNav();navigate(location.hash.replace('#','')||'home')})
