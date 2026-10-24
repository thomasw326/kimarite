const root=document.body;
root.insertAdjacentHTML('beforeend', '<section id="setup"><label>You <select id="human"></select></label> <label>AI <select id="opponent"></select></label> <button id="start">Start Bout</button></section><section id="score"></section><section id="choices"></section><section id="hand"></section><button id="end" disabled>End Turn</button><p id="notice" role="status"></p>');
const $=id=>document.getElementById(id);
let token=null,game=null,selected=new Set();
const escapeHTML=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;':'&quot;'}[c]));
async function request(path,body){const res=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await res.json();if(!res.ok)throw Error(data.message||data.error||'Request rejected');return data;}
function button(label,onClick){const b=document.createElement('button');b.textContent=label;b.onclick=onClick;return b;}
function show(g){
 game=g;selected=new Set();$('notice').textContent=g.finished?(g.win_method||g.stopped_reason||'Bout completed'):'';
 $('score').replaceChildren();$('score').innerHTML='<h2>Turn '+g.turn+'</h2><p>Position '+g.position+' · Momentum '+g.momentum+'</p><p>'+escapeHTML(g.human.name)+' · Power '+g.human.power+' · Grip '+g.human.grip.join('/')+' · Plays '+g.human.plays_remaining+'</p><p>'+escapeHTML(g.opponent.name)+' · Power '+g.opponent.power+' · Grip '+g.opponent.grip.join('/')+' · Hidden hand '+g.opponent.hand_count+'</p>';
 for(const side of ['human','opponent']){const d=document.createElement('p');d.textContent=side+': Kimarite '+g[side].kimarite.map(c=>c.name).join(', ')+' | Temporary '+g[side].temporary.map(c=>c.name).join(', ');$('score').append(d)}
 $('choices').replaceChildren();
 if(g.selection){$('choices').append(document.createTextNode('Choose '+g.selection.keep+' cards: '));g.selection.options.forEach((c,i)=>{const b=button(c.name+' ['+c.power+'/'+c.technique+'/'+c.spirit+']',()=>{if(selected.has(i)){selected.delete(i);b.classList.remove('selected')}else{selected.add(i);b.classList.add('selected')}});$('choices').append(b)});$('choices').append(button('Keep selected',()=>{if(selected.size===g.selection.keep)act({type:'choose_cards',indices:[...selected]});else $('notice').textContent='Choose exactly '+g.selection.keep+' cards.'}))}
 $('hand').replaceChildren();const legal=new Set(g.legal_plays.map(a=>a.hand_index));for(let i=0;i<g.human.hand.length;i++){const c=g.human.hand[i];const b=button(c.name+' ['+c.power+'/'+c.technique+'/'+c.spirit+']',()=>act({type:'play_card',hand_index:i}));b.disabled=!legal.has(i);$('hand').append(b)}$('end').disabled=!g.can_end_turn;
}
async function act(command){try{const result=await request('/api/session/'+token+'/action',command);show(result.state)}catch(err){$('notice').textContent=err.message}}
$('start').onclick=async()=>{try{const result=await request('/api/session',{human:$('human').value,opponent:$('opponent').value});token=result.token;show(result.state)}catch(err){$('notice').textContent=err.message}};
$('end').onclick=()=>act({type:'end_turn'});
request('/api/roster').then(r=>{for(const id of ['human','opponent']){for(const name of r.roster){const o=document.createElement('option');o.value=name;o.textContent=name;$(id).append(o)}}$('human').value='Arm Controller';$('opponent').value='The Technician'}).catch(e=>$('notice').textContent=e.message);
