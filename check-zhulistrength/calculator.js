/*
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/calculator.js, 页面版强度计算逻辑
[INPUT]: DOM 事件和用户输入
[OUTPUT]: DOM 结果渲染
*/
function n(x){var y=parseFloat(x);return isNaN(y)?0:y}
function f2(x){return (Math.round(x*100)/100).toFixed(2)}
function compute(amount,mainNet,retailNet,pctChg){
  var a=0;
  if(amount>0){a=(mainNet/amount)*100}else{a=0}
  var base='';
  if(a>=3.0){base='抢筹'}
  else if(a>1.0 && a<3.0){base='建仓'}
  else if(a>=-1.0 && a<=1.0){base='洗盘'}
  else{base='出货'}
  var isTrue=true;
  if(a>0 && retailNet>0){isTrue=false}
  if(a<0 && retailNet<0){isTrue=false}
  var behavior=(isTrue?'真':'假')+base;
  var c=a>0?(pctChg/a):0;
  var e='观望';
  if(a>2.5 && c<0.3 && amount<500){e='下跌'}
  else if(behavior==='真抢筹' && retailNet>0){e='下跌'}
  else if(a<0.5 && amount<300){e='下跌'}
  else if(amount>8000 && a<1.0){e='冲高回落'}
  else if(behavior==='真出货' || behavior==='假建仓' || pctChg>5.0){e='冲高回落'}
  else if(['真建仓','真抢筹','真洗盘','假出货'].indexOf(behavior)>=0){
    if(pctChg<3.0){e='上涨'}else{e='冲高回落'}
  }
  return {a:a,b:behavior,c:c,e:e}
}
function addRowWithValues(amount,mainNet,retailNet,pctChg){
  var tbody=document.getElementById('rows');
  var tr=document.createElement('tr');
  tr.innerHTML=[
    '<td><input type="number" step="0.01" class="amount" value="'+amount+'"></td>',
    '<td><input type="number" step="0.01" class="mainNet" value="'+mainNet+'"></td>',
    '<td><input type="number" step="0.01" class="retailNet" value="'+retailNet+'"></td>',
    '<td><input type="number" step="0.01" class="pctChg" value="'+pctChg+'"></td>',
    '<td class="AVal"></td>',
    '<td class="BVal"></td>',
    '<td class="CVal"></td>',
    '<td class="EVal"></td>',
    '<td><button class="calc">计算</button> <button class="del" style="background:#e53e3e;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;">删除</button></td>'
  ].join('');
  tbody.appendChild(tr);
  bindRow(tr)
}
function bindRow(tr){
  var btn=tr.querySelector('.calc');
  var del=tr.querySelector('.del');
  btn.addEventListener('click',function(){calcRow(tr)})
  del.addEventListener('click',function(){tr.remove()})
}
function calcRow(tr){
  var amount=n(tr.querySelector('.amount').value);
  var mainNet=n(tr.querySelector('.mainNet').value);
  var retailNet=n(tr.querySelector('.retailNet').value);
  var pctChg=n(tr.querySelector('.pctChg').value);
  var r=compute(amount,mainNet,retailNet,pctChg);
  tr.querySelector('.AVal').textContent=f2(r.a);
  tr.querySelector('.BVal').textContent=r.b;
  tr.querySelector('.CVal').textContent=f2(r.c);
  var eCell=tr.querySelector('.EVal');
  eCell.textContent=r.e;
  eCell.classList.remove('ok','warn','bad');
  if(r.e==='上涨'){eCell.classList.add('ok')}
  else if(r.e==='下跌'){eCell.classList.add('bad')}
  else if(r.e==='冲高回落'){eCell.classList.add('warn')}
}
function calcAll(){
  var rows=document.querySelectorAll('#rows tr');
  rows.forEach(calcRow)
}
function addRow(){
  addRowWithValues(0,0,0,0)
}
document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('addRow').addEventListener('click',addRow);
  document.getElementById('calcAll').addEventListener('click',calcAll);
  addRowWithValues(1000,20,-10,1.5)
})
