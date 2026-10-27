const $=id=>document.getElementById(id);let token=null,game=null,picked=new Set(),pendingPlay=null,sessionSetup=null,actionJournal=[];
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok){const e=new Error(v.message||v.error||'Request failed');e.data=v;throw e}return v}
function rememberSession(){try{if(token)sessionStorage.setItem('kimarite_session',token);if(sessionSetup)sessionStorage.setItem('kimarite_setup',JSON.stringify(sessionSetup));sessionStorage.setItem('kimarite_actions',JSON.stringify(actionJournal))}catch(e){}}
async function recoverSession(){if(!sessionSetup)throw new Error('This bout expired and has no recovery data. Please start a new bout.');const restored=await api('/api/session',sessionSetup);let state=restored.state;for(const command of actionJournal){const next=await api('/api/session/'+restored.token+'/action',command);state=next.state}token=restored.token;rememberSession();return state}
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function btn(text,fn,cls=''){const b=node('button',cls,text);b.onclick=fn;return b}
function card(c,fn,enabled=true){const b=btn(c.name,fn,'card'+(c.is_kimarite?' kimarite':''));const o=node('div','orb','POWER '+c.power+'  ·  TECH '+c.technique+'  ·  SPIRIT '+c.spirit);b.append(o);b.disabled=!enabled;return b}
function names(cards){return cards.map(c=>c.name).join(', ')||'—'}
function zoneEffect(c,zone){
 const d=c.description||'';
 if(zone==='kimarite')return (d.match(/Win:\s*(.*?)(?=\s*On play:|$)/)||[])[1]||'Winning condition not available';
 if(['Gain Left Grip','Gain Right Grip','Uwate','Shitate'].includes(c.name))return 'Blocks 1 incoming Push; consumed when used, otherwise expires at the start of your next turn.';
 if(c.name==='Shiko Stomp')return 'Prevents the next negative effect against you; persists until consumed.';
 if(c.name==='Kannuki')return 'While active: suppresses opponent Grip benefits and Grip-building cards. Next turn: reduce both opposing Grips one level and make opponent Unstable (subject to prevention).';
 if(c.name==='Henka')return 'Blocks the first incoming Push. If it survives: gain 1 Momentum and make opponent Unstable. If disrupted: you become Unstable.';
 if(c.name==='Sidestep')return 'While side-by-side: Push is suppressed. On survival: Momentum determines favourable orientation; opponent becomes Unstable.';
 if(c.name==='Spin Away')return 'While active: Push is suppressed. On survival: Momentum determines favourable orientation. If disrupted: opponent gains Okuridashi.';
 const m=d.match(/(?:Temporary(?: \([^)]*\))?|While active:|Next turn:|On each later turn:|At the start of your next turn:)[\s:]*(.*)$/i);
 return m?m[0]:d.replace(/^.*?Exchange:\s*/,'')||'Active effect unavailable';
}

function inspect(c,playAction){$('inspect-name').textContent=c.name;$('inspect-orbs').textContent=c.zone_only?'':('Power '+(c.power??0)+' · Technique '+(c.technique??0)+' · Spirit '+(c.spirit??0));const desc=c.description||'This card needs a B10 wording audit before its full rules can be shown.';const effect=$('inspect-effect');effect.replaceChildren();const terms=Object.keys((game&&game.glossary)||{}).sort((a,b)=>b.length-a.length);const split=terms.length?new RegExp('\\b('+terms.join('|')+')\\b','gi'):null;const chunks=split?desc.split(split):[desc];for(const chunk of chunks){const key=terms.find(t=>t.toLowerCase()===chunk.toLowerCase());if(key){const link=btn(chunk,()=>{const old=$('glossary-detail');if(old)old.remove();const panel=node('p','glossary-detail',key+': '+game.glossary[key]);panel.id='glossary-detail';effect.after(panel)},'term-link');link.type='button';effect.append(link)}else effect.append(document.createTextNode(chunk))}$('inspect-orbs').textContent+=' · '+(c.timing||'')+(c.description_status==='needs_audit'?' · TEXT PENDING AUDIT':'');$('inspect-actions').replaceChildren();if(c.unavailable_reason)$('inspect-actions').append(node('p','unavailable-reason','Cannot play: '+c.unavailable_reason));if(playAction)$('inspect-actions').append(btn('Play this card',()=>{$('inspect').close();playAction()},'confirm'));$('inspect').showModal()}
$('inspect-close').onclick=()=>$('inspect').close();
function logText(){if(!game)return '';return ['KIMARITE — BOUT HISTORY',game.human.name+' vs '+game.opponent.name,'Turn '+game.turn+(game.finished?' — Bout over':'')+(sessionSetup&&Number.isSafeInteger(sessionSetup.seed)?' · Seed '+sessionSetup.seed:''),'',...(game.events||[])].join('\n')}
$('copy-history').onclick=async()=>{const value=logText();if(!value){$('copy-status').textContent='Start a bout first.';return}try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(value)}else{const field=document.createElement('textarea');field.value=value;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();if(!document.execCommand('copy'))throw new Error('Copy not supported');field.remove()}$('copy-status').textContent='Copied!'}catch(e){$('copy-status').textContent='Select and copy the log below.';const field=document.createElement('textarea');field.value=value;field.rows=8;field.className='log-copy-fallback';$('copy-status').after(field);field.focus();field.select()}};

function showDiscard(owner,person){$('discard-title').textContent=person+' — Discard pile ('+owner.discard.length+')';const list=$('discard-list');list.replaceChildren();if(!owner.discard.length)list.append(node('p','','Discard pile is empty.'));for(const [index,c] of owner.discard.entries()){const item=node('div','discard-entry');item.append(node('span','',String(index+1)+'. '+c.name),btn('Inspect',()=>{ $('discard-dialog').close();inspect(c) },'choice-inspect'));list.append(item)}$('discard-dialog').showModal()}
$('discard-close').onclick=()=>$('discard-dialog').close();

let management=null;
function managementSave(){try{sessionStorage.setItem('kimarite_management',JSON.stringify(management))}catch(e){}}
function activeTournamentBout(){
 if(!management||!sessionSetup)return null;
 if(Number.isInteger(sessionSetup.tournament_bout))return sessionSetup.tournament_bout;
 const m=management;
 // Migrate an in-progress tournament created before explicit bout tagging.
 if(sessionSetup.human===m.human&&sessionSetup.opponent===m.opponents[m.round]&&sessionSetup.seed===m.seed+m.round+1){
  sessionSetup.tournament_bout=m.round;rememberSession();return m.round;
 }
 return null;
}
function tournamentFinalText(m){
 const wins=m.results.filter(r=>r.won).length;
 const lines=['KIMARITE — TOURNAMENT RESULTS',m.human+' · '+wins+' wins, '+(m.results.length-wins)+' losses'];
 for(let i=0;i<m.results.length;i++){
  const r=m.results[i];
  lines.push('Bout '+(i+1)+' · '+(r.won?'WIN':'LOSS')+' vs '+(r.opponent_name||r.opponent)+' · '+r.finish+' · Turn '+r.turns);
 }
 return lines.join('\n');
}
function showTournamentFinal(){
 const m=management;
 if(!m||m.results.length!==15)return;
 const dialog=$('tournament-final');
 const wins=m.results.filter(r=>r.won).length;
 $('tournament-final-record').textContent=wins+'–'+(15-wins);
 $('tournament-final-player').textContent=m.human+' · 15 bouts completed';
 const rounds=$('tournament-final-rounds');
 rounds.replaceChildren();
 for(let i=0;i<5;i++){
  const results=m.results.slice(i*3,i*3+3);
  const section=node('section','tournament-final-round');
  const roundWins=results.filter(r=>r.won).length;
  section.append(node('h3','','Round '+(i+1)+' · '+roundWins+'–'+(3-roundWins)));
  for(let k=0;k<results.length;k++){
   const r=results[k];
   const line=node('div','tournament-final-bout');
   line.append(node('strong',r.won?'result-win':'result-loss','Bout '+(i*3+k+1)+' · '+(r.won?'WIN':'LOSS')),
    node('span','',r.opponent_name||r.opponent),
    node('small','',r.finish+' · Turn '+r.turns));
   section.append(line);
  }
  rounds.append(section);
 }
 if(!dialog.open)dialog.showModal();
}
$('management-summary').onclick=showTournamentFinal;
$('tournament-final-close').onclick=()=>$('tournament-final').close();
$('tournament-final-copy').onclick=async()=>{
 const summary=tournamentFinalText(management);
 try{await navigator.clipboard.writeText(summary);$('tournament-final-copy').textContent='Copied!'}
 catch(e){$('tournament-final-copy').textContent='Copy unavailable'}
};
function managementStatus(){if(!management)return;const m=management;const progress=$('management-progress');progress.hidden=false;if(game&&game.finished&&activeTournamentBout()===m.round&&m.results.length===m.round){m.results.push({human:m.human,opponent:m.opponents[m.round],opponent_style:m.opponents[m.round],opponent_name:null,won:game.winner==='A',turns:game.turn,finish:game.win_method||'Unknown',seed:sessionSetup?.seed??null});managementSave()}const wins=m.results.filter(r=>r.won).length;progress.replaceChildren(node('h3','','Tournament · Round '+(Math.floor(m.round/3)+1)+' of 5'));progress.append(node('p','','Completed '+m.results.length+'/15 · Record '+wins+'–'+(m.results.length-wins)));$('management-next').hidden=!(game&&game.finished&&activeTournamentBout()===m.round&&m.results.length===m.round+1&&m.round<14);$('management-next').textContent=m.round%3===2?'Deal next round of nine cards':'Next bout';const table=node('div','tournament-results');table.append(node('h3','',m.results.length===15?'Final results':'Bout results'));for(let round=0;round<5;round++){const subset=m.results.slice(round*3,round*3+3);if(!subset.length)continue;const section=node('section','tournament-round');section.append(node('h4','','Round '+(round+1)+' · '+subset.filter(r=>r.won).length+'–'+(subset.length-subset.filter(r=>r.won).length)));for(const [index,r] of subset.entries()){const row=node('div','tournament-result');row.append(node('strong',r.won?'result-win':'result-loss','Bout '+(round*3+index+1)+' · '+(r.won?'Win':'Loss')));row.append(node('span','',r.opponent_name? r.opponent_name+' ('+(r.opponent_style||r.opponent)+')':(r.opponent_style||r.opponent)));row.append(node('span','',r.turns!=null?'Turn '+r.turns:'Turns unavailable'));row.append(node('span','',r.finish||'Finisher unavailable'));section.append(row)}table.append(section)}progress.append(table);if(game?.finished&&activeTournamentBout()===m.round&&m.results.length!==m.round+1)progress.append(node('p','management-error','Tournament result could not be recorded. Keep this bout open and report the seed; do not start another bout.'));$('management-summary').hidden=m.results.length!==15;if(m.results.length===15){$('management-next').hidden=true;progress.prepend(node('strong','','Tournament complete: '+wins+'–'+(15-wins)))}}
const B11_BASE_STYLES={
 'Heavy Hitter':'power,spirit','Bulldozer':'power,spirit','Charger':'spirit,power','Pressure Fighter':'spirit,power',
 'Power Grappler':'power,technique','Unorthodox Powerhouse':'power,technique','The Technician':'technique,power',
 'The Arsenal':'technique,power','Mawashi Specialist':'technique,spirit','Opportunist':'technique,spirit',
 'Fast Grappler':'spirit,technique','Disruptor':'spirit,technique','Mountain':'power,power',
 'The Specialist':'technique,technique','Speed Demon':'spirit,spirit'};
const B11_BASE_PROXIES={
 'Dancer':'The Specialist','Momentum Twister':'The Technician','Hand-Size Specialist':'The Specialist',
 'Inside Fighter':'Mawashi Specialist','Outside Fighter':'The Technician','Double-Grip Wrestler':'Power Grappler',
 'Lifting Specialist':'Power Grappler','Arm Controller':'Disruptor','Pull-Down Specialist':'Opportunist',
 'Counter Wrestler':'The Specialist','Ring-Edge Defender':'Mountain','Power Finisher':'Heavy Hitter'};
function b11PreviewBase(name){
 const selected=(B11_BASE_STYLES[B11_BASE_PROXIES[name]||name]||'power,technique').split(',');
 const order=[...new Set([...selected,'power','technique','spirit'])];
 const base={power:0,technique:0,spirit:0};base[order[0]]=2;base[order[1]]=1;return base;
}
function b11PreviewTotals(cards){return ['power','technique','spirit'].map(k=>cards.reduce((n,c)=>n+Number(c[k]||0),0))}
function b11TachiaiPreview(m,group){
 const box=node('div','tachiai-preview');
 const slots=m.groups[group];
 if(slots.some(i=>i===null)){box.textContent='Select three cards to preview their all-committed Tachiai.';return box}
 const cards=slots.map(i=>m.cards.find(c=>c.deal_index===i));
 if(cards.some(c=>!c)){box.textContent='Card selection unavailable.';return box}
 const base=b11PreviewBase(m.human),orbs=b11PreviewTotals(cards);
 box.append(node('strong','','All three committed — projected Tachiai'));
 for(const [i,k] of ['power','technique','spirit'].entries()){
  box.append(node('p','',k[0].toUpperCase()+k.slice(1)+': '+(base[k]+1+orbs[i])+' (base '+base[k]+' + cards '+orbs[i]+' + 1)'));
 }
 box.append(node('small','','Before Oshi/Tsuki reveal-chain bonuses or opponent effects. Kept cards contribute no orbs.'));
 return box;
}
function managementBoard(){if(!management)return;const chosen=management.groups.flat().filter(x=>x!==null);const cards=$('management-cards');cards.replaceChildren();for(const c of management.cards){const selected=chosen.includes(c.deal_index);const wrapper=node('div','management-card');wrapper.append(card(c,()=>inspect(c)));wrapper.append(node('small','',selected?'Assigned to a bout':'Available'));cards.append(wrapper)}const groups=$('management-groups');groups.replaceChildren();for(let i=0;i<3;i++){const box=node('div','management-group');box.append(node('h3','','Round '+(Math.floor(management.round/3)+1)+' · Bout '+(i+1)+' vs '+management.opponents[Math.floor(management.round/3)*3+i]));for(let j=0;j<3;j++){const classic=management.opening_mode==='classic';const type=classic?(j===0?'Kimarite':j===1?'Prepared Tachiai':'First draw'):('Opening card '+(j+1));const select=node('select','');const blank=node('option','',type+' — choose');blank.value='';select.append(blank);for(const c of management.cards){if(classic&&(j===0?!c.is_kimarite:c.is_kimarite))continue;if(chosen.includes(c.deal_index)&&management.groups[i][j]!==c.deal_index)continue;const o=node('option','',c.name+' · '+(c.deal_index+1));o.value=c.deal_index;select.append(o)}select.value=management.groups[i][j]===null?'':String(management.groups[i][j]);select.onchange=()=>{management.groups[i][j]=select.value===''?null:Number(select.value);managementSave();managementBoard()};box.append(node('label','',type),select)}groups.append(box)}$('management-start').disabled=chosen.length!==9}
async function managementRound(){const m=management;if(!m)return;const i=m.round;const group=i%3;const take=k=>m.cards.find(c=>c.deal_index===m.groups[group][k]).name;if(m.results.length!==i)throw new Error('Tournament is out of sync: '+m.results.length+' completed, expected '+i+'. Cannot advance safely.');const request={human:m.human,opponent:m.opponents[i],seed:m.seed+i+1};if(m.opening_mode==='classic')request.opening={kimarite:take(0),prepared:take(1),top:take(2)};else {request.opening_mode='b11_live';request.opening_cards=[take(0),take(1),take(2)]}const r=await api('/api/session',request);sessionSetup={...request,tournament_bout:i};actionJournal=[];token=r.token;game=null;render(r.state);$('seed-used').textContent='Bout seed: '+request.seed;$('management-notice').textContent='Bout '+(i+1)+': '+request.human+' vs '+request.opponent;managementSave();document.querySelector('.arena').scrollIntoView({behavior:'smooth'})}
$('management-deal').onclick=async()=>{try{const human=$('management-deck').value;const seed=Math.floor(Math.random()*2147483647);const d=await api('/api/management/deal/'+encodeURIComponent(human)+'?seed='+seed);const roster=[...$('opponent').options].map(o=>o.value).filter(v=>v&&v!=='__random__'&&v!==human);for(let i=roster.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[roster[i],roster[j]]=[roster[j],roster[i]]}management={human,seed,opening_mode:$('management-opening-mode').value,cards:d.cards,groups:Array.from({length:3},()=>[null,null,null]),opponents:roster.slice(0,15),round:0,results:[]};$('management-opening-mode').disabled=true;$('management-board').hidden=false;$('management-progress').hidden=true;$('management-next').hidden=true;managementBoard();managementSave();$('management-notice').textContent='Opponents drawn: '+management.opponents.slice(0,3).map((name,i)=>'Bout '+(i+1)+' — '+name).join(' · ')+'. Assign each card once.'}catch(e){$('management-notice').textContent=e.message}};
$('management-start').onclick=()=>managementRound().catch(e=>$('management-notice').textContent=e.message);
$('management-next').onclick=async()=>{if(!management||management.round>=14||!game?.finished||activeTournamentBout()!==management.round||management.results.length!==management.round+1)return;management.round++;managementSave();if(management.round%3===0){try{const m=management;const d=await api('/api/management/deal/'+encodeURIComponent(m.human)+'?seed='+(m.seed+Math.floor(m.round/3)));m.cards=d.cards;m.groups=Array.from({length:3},()=>[null,null,null]);game=null;$('management-board').hidden=false;$('management-start').disabled=true;$('management-next').hidden=true;managementBoard();managementSave();$('management-notice').textContent='Round '+(Math.floor(m.round/3)+1)+': opponents '+m.opponents.slice(m.round,m.round+3).join(', ')+'. Allocate your nine new cards.';$('management-board').scrollIntoView({behavior:'smooth'})}catch(e){management.round--;managementSave();$('management-notice').textContent='Could not deal the next round: '+e.message}}else managementRound().catch(e=>{management.round--;managementSave();$('management-notice').textContent='Could not start next bout: '+e.message;managementStatus()})};

function renderPendingTachiai(g){
 game=g;picked=new Set();pendingPlay=null;rememberSession();if(management)managementStatus();
 $('round').textContent='CHOOSE TACHIAI';$('tracks').replaceChildren();
 $('score').replaceChildren(node('h2','','Your opening: '+g.human.name+' vs '+g.opponent.name));
 $('opening').replaceChildren(node('p','','Your opponent’s Tachiai cards remain hidden until you commit.'));
 $('choices').replaceChildren(node('h2','','Commit 0–3 cards to Tachiai'),node('p','','Committed cards contribute orbs and Tachiai effects; cards you keep will start in your Exchange hand.'));
 const strip=node('div','cards');
 g.tachiai_choice.cards.forEach((c,i)=>{const b=card(c,()=>{if(picked.has(i)){picked.delete(i);b.classList.remove('selected')}else{picked.add(i);b.classList.add('selected')}summary.textContent=picked.size+' committed · '+(3-picked.size)+' retained'});const inspectButton=btn('Inspect '+c.name,()=>inspect(c),'choice-inspect');const wrap=node('div','choice-card-wrap');wrap.append(b,inspectButton);strip.append(wrap)});
 $('choices').append(strip);const summary=node('p','zones','0 committed · 3 retained');$('choices').append(summary,btn('Confirm Tachiai commitment',()=>act({type:'commit_tachiai',indices:[...picked].sort()}),'confirm'));
 $('hand').replaceChildren();$('history').replaceChildren();$('end').disabled=true;$('notice').textContent='';
}
let lastPresentedResult=null;
function showBoutResult(g){
 const dialog=$('bout-result');
 if(!dialog||!g.finished||!g.winner||!sessionSetup||sessionSetup.opening_mode!=='b11_live')return;
 const key=[sessionSetup.seed,g.human.name,g.opponent.name,g.turn,g.winner,g.win_method].join('|');
 if(lastPresentedResult===key)return;
 lastPresentedResult=key;
 const won=g.winner==='A';
 $('result-banner').textContent=won?'VICTORY!':'DEFEAT';
 $('result-banner').className='result-banner '+(won?'result-victory':'result-defeat');
 $('result-method').textContent=g.win_method||'Bout ended';
 $('result-timing').textContent=(g.winner==='A'?g.human.name:g.opponent.name)+' wins · Turn '+g.turn;
 const info=g.victory_details;
 $('result-type').textContent=info?.source&&info.source!=='kimarite'?'WINNING METHOD':'WINNING KIMARITE';
 $('result-requirements').textContent=info?.requirement_text||'See the bout history for the winning conditions.';
 const values=$('result-values');values.replaceChildren();
 if(info){
  if(info.checks?.length){
   for(const check of info.checks){
    const row=node('div','result-value result-check');
    row.append(node('span','',check.label+' '+(check.met?'✓':'!')),node('strong','',check.actual+' (required '+check.required+')'));
    values.append(row);
   }
  }
  const fields=[['Grip',info.grip],['Effective Grip',info.effective_grip],['Power',info.power],['Momentum advantage',info.momentum_advantage],['Position advantage',info.position_advantage],['Hand advantage',info.hand_advantage]];
  for(const [name,value] of fields){const row=node('div','result-value');row.append(node('span','',name),node('strong','',String(value)));values.append(row)}
 }
 dialog.classList.remove('result-revealed');
 dialog.showModal();
 requestAnimationFrame(()=>dialog.classList.add('result-revealed'));
}
$('result-review').onclick=()=>{$('bout-result').close();$('history').scrollIntoView({behavior:'smooth',block:'start'})};
$('result-next').onclick=()=>{
 $('bout-result').close();
 if(management?.results.length===15){showTournamentFinal();return}
 const next=$('management-next');
 if(management&&next&&!next.hidden){next.click();return}
 $('start').scrollIntoView({behavior:'smooth',block:'start'});
};
function render(g){if(g.phase==='choose_tachiai'){renderPendingTachiai(g);return}game=g;picked=new Set();pendingPlay=null;rememberSession();if(management)managementStatus();$('round').textContent='TURN '+g.turn+' · '+(g.finished?'BOUT OVER':g.phase==='select_cards'?'SELECT CARDS':'EXCHANGE');$('tracks').replaceChildren(node('span','track','POSITION '+g.position),node('span','track','MOMENTUM '+g.momentum));$('score').replaceChildren();
 for(const [title,s,own] of [['YOUR RIKISHI',g.human,true],['OPPONENT',g.opponent,false]]){const box=node('div','rikishi-info');box.append(node('div','eyebrow',title),node('h2','',s.name),node('p','', 'Power '+s.power+'  ·  Grip '+s.grip.join('/')+'  ·  '+(own?'Plays '+s.plays_remaining:'Hand '+s.hand_count)));const zones=node('p','zones');zones.append(node('b','','Kimarite: '),document.createTextNode(names(s.kimarite)),node('br'),node('b','','Temporary: '),document.createTextNode(names(s.temporary)));box.append(zones);const discard=btn('Discard pile: '+s.discard_count+' · View cards',()=>showDiscard(s,own?'Your rikishi':'Opponent'),'discard-button');box.append(discard);for(const zoneName of ['kimarite','temporary']){const zone=node('div','zone-list');zone.append(node('div','eyebrow',zoneName.toUpperCase()));for(const c of s[zoneName]){const item=node('div','zone-entry');item.append(btn(c.name+' · Inspect',()=>inspect({...c,description:zoneEffect(c,zoneName),zone_only:true,timing:zoneName==='kimarite'?'Winning condition':'Active Temporary effect'}),'zone-card'));item.append(node('p','temporary-detail',zoneEffect(c,zoneName)));zone.append(item)}box.append(zone)}$('score').append(box)}
 const opening=$('opening');opening.replaceChildren();if(g.opening){for(const [side,label] of [['human','Your opening'],['opponent','Opponent opening']]){const o=g.opening[side];opening.append(node('h2','',label));opening.append(node('p','', 'Tachiai totals — Power '+o.tachiai_orbs[0]+' · Technique '+o.tachiai_orbs[1]+' · Spirit '+o.tachiai_orbs[2]));for(const [key,title] of [['starting_kimarite','Starting Kimarite'],['prepared_tachiai','Prepared Tachiai'],['top_of_deck','Top of deck']]){if(o[key])opening.append(btn(title+': '+o[key].name+' · Inspect',()=>inspect(o[key]),'zone-card'))}}opening.append(node('p','zones','Your selected opening cards are shown here. Choose cards before a new bout; automatic mode remains available for comparison.'))}
 $('choices').replaceChildren();if(g.selection){$('choices').append(node('h2','','Choose '+g.selection.keep+' cards to keep'));const strip=node('div','cards');g.selection.options.forEach((c,i)=>{const b=card({...c,name:(i+1)+'. '+c.name},()=>{if(picked.has(i)){picked.delete(i);b.classList.remove('selected')}else{picked.add(i);b.classList.add('selected')}confirm.disabled=picked.size!==g.selection.keep});const info=btn('Inspect '+c.name,()=>inspect(c),'choice-inspect');info.type='button';const wrap=node('div','choice-card-wrap');wrap.append(b,info);strip.append(wrap)});$('choices').append(strip);const confirm=btn('Keep selected cards',()=>act({type:'choose_cards',indices:[...picked]}),'confirm');confirm.disabled=g.selection.keep!==0;$('choices').append(confirm)}
 $('hand').replaceChildren();const legal=new Set(g.legal_plays.map(a=>a.hand_index));g.human.hand.forEach((c,i)=>$('hand').append(card(c,()=>inspect(c,legal.has(i)?()=>play(i):null),true)));const history=$('history');history.replaceChildren();const events=g.events||[];if(!events.length)history.append(node('p','','No actions recorded yet.'));for(const event of events.slice().reverse())history.append(node('p',event.includes(' plays ')?'history-line':'history-event',event));$('end').disabled=!g.can_end_turn;$('notice').textContent=g.finished?('Winner: '+(g.winner==='A'?g.human.name:g.winner==='B'?g.opponent.name:'Undecided')+' · '+(g.win_method||g.stopped_reason||'')):'';
 if(g.finished)showBoutResult(g);
}
async function play(hand_index){pendingPlay={type:'play_card',hand_index,choices:{}};await act(pendingPlay)}
async function act(command){try{let r;try{r=await api('/api/session/'+token+'/action',command)}catch(e){if(e.data&&e.data.code==='session_expired'){await recoverSession();r=await api('/api/session/'+token+'/action',command)}else throw e}actionJournal.push(JSON.parse(JSON.stringify(command)));render(r.state)}catch(e){if(e.data&&e.data.choice_required){choicePrompt(e.data);return}if(e.data&&e.data.state){render(e.data.state);$('notice').textContent=e.message+(e.data.state.selection?' — Card selection is still pending above.':'');return}$('notice').textContent=e.message}}
function choicePrompt(detail){$('choices').replaceChildren();$('choices').append(node('h2','','Choose for '+(detail.card||'card')));$('choices').append(node('p','',detail.choice_title||detail.choice_name||detail.message));const strip=node('div','cards');for(const option of detail.options||[]){const value=option.value;const wrap=node('div','choice-card-wrap');wrap.append(btn(String(option.label),()=>{if(!pendingPlay)return;pendingPlay.choices[detail.choice_name]=value;act(pendingPlay)},'card'));if(option.card)wrap.append(btn('Inspect '+option.card.name,()=>inspect(option.card),'choice-inspect'));strip.append(wrap)}$('choices').append(strip);$('choices').scrollIntoView({behavior:'smooth',block:'center'})}
async function loadOpening(){try{const d=await api('/api/opening/'+encodeURIComponent($('human').value));for(const [select,cards] of [['pick-kimarite',d.kimarite],['pick-prepared',d.ordinary],['pick-top',d.ordinary]]){$(select).replaceChildren();for(const c of cards){const o=node('option','',c.name);o.value=c.name;$(select).append(o)}}if(d.ordinary.length>1)$('pick-top').selectedIndex=1;const all=[...d.kimarite,...d.ordinary];for(let i=0;i<3;i++){const select=$('b11-card-'+i);select.replaceChildren();for(const c of all){const o=node('option','',c.name);o.value=c.name;select.append(o)}select.selectedIndex=i%all.length}}catch(e){$('notice').textContent=e.message}}
$('human').addEventListener('change',()=>{const random=$('human').value==='__random__';if(random){$('opening-mode').value='auto';$('opening-picks').hidden=true;$('b11-picks').hidden=true;$('opening-mode').querySelector('option[value="choose"]').disabled=true}else{$('opening-mode').querySelector('option[value="choose"]').disabled=false;$('b11-picks').hidden=$('opening-mode').value!=='b11_live';loadOpening()}});
$('opening-mode').addEventListener('change',()=>{$('opening-picks').hidden=$('opening-mode').value!=='choose'||$('human').value==='__random__';$('b11-picks').hidden=$('opening-mode').value!=='b11_live'||$('human').value==='__random__'});
$('seed-mode').addEventListener('change',()=>{$('seed-fixed-wrap').hidden=$('seed-mode').value!=='fixed'});
$('start').onclick=async()=>{try{const fixed=Number($('seed-fixed').value);if($('seed-mode').value==='fixed'&&(!Number.isSafeInteger(fixed)||fixed<0))throw new Error('Enter a non-negative whole-number seed.');const seed=$('seed-mode').value==='random'?Math.floor(Math.random()*2147483647):fixed;const roster=[...$('human').options].map(o=>o.value).filter(v=>v&&v!=='__random__');const choose=v=>v==='__random__'?roster[Math.floor(Math.random()*roster.length)]:v;const request={human:choose($('human').value),opponent:choose($('opponent').value),seed};if($('opening-mode').value==='b11_live'&&$('human').value!=='__random__'){request.opening_mode='b11_live';request.opening_cards=[0,1,2].map(i=>$('b11-card-'+i).value)}if($('opening-mode').value==='choose'&&$('human').value!=='__random__')request.opening={kimarite:$('pick-kimarite').value,prepared:$('pick-prepared').value,top:$('pick-top').value};const r=await api('/api/session',request);sessionSetup=request;actionJournal=[];token=r.token;$('human').value=request.human;$('opponent').value=request.opponent;$('seed-used').textContent='Bout seed: '+seed;render(r.state)}catch(e){$('notice').textContent=e.message}};
$('end').onclick=()=>{if(!game||!game.can_end_turn)return;const remaining=game.human.plays_remaining;if(remaining>0){$('end-confirm-message').textContent='You have '+remaining+' Play'+(remaining===1?'':'s')+' remaining. Continue playing?';$('end-confirm').showModal()}else act({type:'end_turn'})};
$('continue-playing').onclick=()=>$('end-confirm').close();
$('confirm-end-turn').onclick=()=>{$('end-confirm').close();if(game&&game.can_end_turn)act({type:'end_turn'})};
async function resume(){try{const saved=sessionStorage.getItem('kimarite_session');if(!saved)return;sessionSetup=JSON.parse(sessionStorage.getItem('kimarite_setup')||'null');actionJournal=JSON.parse(sessionStorage.getItem('kimarite_actions')||'[]');token=saved;if(sessionSetup&&Number.isSafeInteger(sessionSetup.seed))$('seed-used').textContent='Bout seed: '+sessionSetup.seed;let state;try{state=await api('/api/session/'+saved)}catch(e){if(e.data&&e.data.code==='session_expired'){state=await recoverSession()}else throw e}render(state)}catch(e){$('notice').textContent='Unable to restore the previous bout: '+e.message}}
resume();
api('/api/roster').then(r=>{for(const name of r.roster){const o=node('option','',name);o.value=name;$('management-deck').append(o)}for(const id of ['human','opponent']){const random=node('option','','Random Wrestler');random.value='__random__';$(id).append(random);for(const name of r.roster){const o=node('option','',name);o.value=name;$(id).append(o)}}$('human').value='Arm Controller';$('opponent').value='The Technician';loadOpening();try{const saved=JSON.parse(sessionStorage.getItem('kimarite_management')||'null');if(saved&&Array.isArray(saved.cards)&&saved.groups){management=saved;$('management-opening-mode').value=saved.opening_mode||'classic';$('management-opening-mode').disabled=true;$('management-deck').value=saved.human;$('management-board').hidden=false;managementBoard();managementStatus()}}catch(e){} }).catch(e=>$('notice').textContent=e.message);
