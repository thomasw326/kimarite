// Bilingual card labels preserve the original language first in the UI.
// Preserve established Card Library labels. Use concise English glosses
// for the other Japanese names in the live catalogue.
const CARD_ENGLISH_NAMES=Object.freeze({
 'Oshi':"Push",
 'Tsuki':"Thrust",
 'Tsuppari':"Repeated Thrusts",
 'Nodowa':"Throat Grab",
 'Harite':"Open-Handed Slap",
 'Tsuri':"Lift",
 'Yori':"Tighten the Grip",
 'Henka':"Sidestep or Evasive Shift",
 'Yorikiri':"Force Out",
 'Oshidashi':"Push Out",
 'Tsukidashi':"Thrust Out",
 'Oshitaoshi':"Push Down",
 'Yoritaoshi':"Crush Out",
 'Hatakikomi':"Slap Down",
 'Tsukiotoshi':"Thrust Down",
 'Uwatenage':"Overarm Throw",
 'Shitatenage':"Underarm Throw",
 'Hikiotoshi':"Pull Down",
 'Okuridashi':"Rear Push Out",
 'Kotenage':"Arm-Lock Throw",
 'Uwatedashinage':"Pulling Overarm Throw",
 'Katasukashi':"Under-Shoulder Swing Down",
 'Sukuinage':"Beltless Arm Throw",
 'Tsukitaoshi':"Thrust Down",
 'Abisetaoshi':"Crush Down",
 'Tsuridashi':"Lift Out",
 'Kirikaeshi':"Reversal Leg Trip",
 'Okuritaoshi':"Rear Push Down",
 'Tottari':"Arm Bar Throw",
 'Utchari':"Edge Pivot Throw",
 'Uwate':"Outside Grip",
 'Shitate':"Inside Grip",
 'Sonkyo':"Defensive Crouch",
 'Gaburi':"Belly Drive",
 'Ottsuke':"Arm Clamp",
 'Use the Tawara':"Ring Bales",
 'Kannuki':"Double Arm Clamp",
 'Morozashi':"Double Inside Grip",
 'Morotezuki':"Two-Handed Thrust",
 'Kachiage':"Rising Forearm Strike",
 'Nekodamashi':"Clap Feint",
 'Maesabaki':"Fight for Inside Position",
 'Deashi':"Quick First Step",
 'Butsukari':"Charging Drill",
 'Denshamichi':"Straight-Line Drive",
 'Ankogata':"Heavyset Build",
 'Tsuriotoshi':"Lift and Drop",
 'Shitatedashinage':"Pulling Underarm Throw",
 'Shitatehineri':"Twisting Underarm Throw",
 'Renzoku':"Chain Attacks",
 'Meguri':"Cycle",
 'Nokotta!':"Still In!",
 'Hakkeyoi!':"Get Moving!",
 'Hazuoshi':"Underarm Push",
 'Inashi':"Redirect the Charge",
 'Chiri-chozu':"Purification Ritual",
 'Shikiri':"Pre-Bout Face-Off",
 'Kubinage':"Headlock Throw",
 'Kimedashi':"Arm-Lock Force Out",
 'Kimetaoshi':"Arm-Lock Force Down"
});
const CARD_DISPLAY_TITLES=Object.freeze({
 'Driving Force — Power Payoff':'Driving Force',
 'Crushing Pressure — Power Crusher':'Crushing Pressure',
 'Explosive Step — Fumikomi':'Explosive Step (Fumikomi)',
 'Power Water':'Power Water (力水)',
 'Salt Throw':'Salt Throw (塩まき)',
 'Shiko Stomp':'Shiko Stomp (四股)'
});
function displayCardName(name){
 if(typeof name!=='string')return name||'';
 const english=CARD_ENGLISH_NAMES[name];
 return CARD_DISPLAY_TITLES[name]??(english?name+' ('+english+')':name);
}
const $=id=>document.getElementById(id);let token=null,game=null,picked=new Set(),pendingPlay=null,sessionSetup=null,actionJournal=[];
function setGameLocation(location){
 // Location is the current gameplay phase, not free navigation from an active bout.
 if(location!=='heya'&&location!=='dohyo')throw new Error('Unknown game location.');
 const changed=document.body.dataset.phase!==location;
 $('heya-view').hidden=location!=='heya';
 $('dohyo-view').hidden=location!=='dohyo';
 document.body.dataset.phase=location;
 $('phase-heading').textContent=location==='heya'?'Heya · The Stable':'Dohyō · The Ring';
 $('phase-subtitle').textContent=location==='heya'
  ?'Plan, draft, and prepare your wrestler for the next bout.'
  :'Commit your Tachiai and fight on the clay.';
 gameSaveSet('kimarite_ui_phase',location);
 if(changed)window.scrollTo(0,0);
}
// This scenario is deployed from the dedicated rematch playtest branch.
const rematchScenario=new URLSearchParams(window.location.search).get('rematch');
const playtestSavePrefix=['loss','win','review'].includes(rematchScenario)?'playtest_player_rematch_'+rematchScenario+'_':'';

function gameSaveGet(key){
 key=playtestSavePrefix+key;
 try{const current=sessionStorage.getItem(key);if(current!==null)return current}catch(e){}
 try{return localStorage.getItem(key)}catch(e){return null}
}
function gameSaveSet(key,value){
 key=playtestSavePrefix+key;
 try{sessionStorage.setItem(key,value)}catch(e){}
 try{localStorage.setItem(key,value)}catch(e){}
}
function gameSaveRemove(key){
 key=playtestSavePrefix+key;
 try{sessionStorage.removeItem(key)}catch(e){}
 try{localStorage.removeItem(key)}catch(e){}
}
function shouldShowGameGuide(){
 // Do not interrupt a returning wrestler's saved draft, bout or tournament.
 const savedManagement=gameSaveGet('kimarite_management');
 const savedDraft=gameSaveGet('kimarite_active_draft');
 return !gameSaveGet('kimarite_guide_seen')
  &&(!savedManagement||savedManagement==='null')
  &&(!savedDraft||savedDraft==='null')
  &&!gameSaveGet('kimarite_session');
}
function installGameGuide(){
 const guide=$('game-guide');
 $('open-game-guide').onclick=()=>{if(!guide.open)guide.showModal()};
 $('guide-dismiss').onclick=()=>guide.close();
 guide.addEventListener('close',()=>gameSaveSet('kimarite_guide_seen','1'));
 if(shouldShowGameGuide())guide.showModal();
}
function clearBoutSession(){
 token=null;game=null;sessionSetup=null;actionJournal=[];
 for(const key of ['kimarite_session','kimarite_setup','kimarite_actions'])gameSaveRemove(key);
}
function returnedToHeyaAfterBout(g){
 // Preserve a completed bout's return-to-Heya choice across page reloads.
 if(!g.finished||gameSaveGet('kimarite_ui_phase')!=='heya')return false;
 try{
  const m=management||JSON.parse(gameSaveGet('kimarite_management')||'null');
  return !!(m&&Array.isArray(m.results)&&sessionSetup
   &&sessionSetup.tournament_bout===m.round
   &&m.results.length===m.round+1);
 }catch(e){return false}
}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok){const e=new Error(v.message||v.error||'Request failed');e.data=v;throw e}return v}
// Clear only this game's browser saves, in BOTH stores. Keeping the guide
// preference avoids interrupting players who repeatedly run B12 playtests.
const RESET_PROGRESS_KEYS=Object.freeze([
 'kimarite_management','kimarite_active_draft','kimarite_session',
 'kimarite_setup','kimarite_actions','kimarite_ui_phase'
]);
function clearSavedProgress(){
 for(const key of RESET_PROGRESS_KEYS)gameSaveRemove(key);
}
function resetFromCleanLink(){
 // A deliberately shared fresh-start URL also works when old progress was
 // stored by a previous version of the client. Run BEFORE resume/restore.
 const params=new URLSearchParams(window.location.search);
 if(params.get('fresh')!=='1')return false;
 clearSavedProgress();
 params.delete('fresh');
 const remainder=params.toString();
 window.history.replaceState(null,'',window.location.pathname+
  (remainder?'?'+remainder:'')+window.location.hash);
 return true;
}
resetFromCleanLink();
$('reset-progress').onclick=()=>$('reset-progress-confirm').showModal();
$('reset-cancel').onclick=()=>$('reset-progress-confirm').close();
$('reset-confirm').onclick=()=>{
 $('reset-progress-confirm').close();
 clearSavedProgress();
 // Reload the entire app, not merely the Heya panel, to clear in-memory bout
 // tokens, selected cards, the session journal and the old scheduled AI world.
 const params=new URLSearchParams(window.location.search);
 params.set('fresh','1');
 window.location.replace(window.location.pathname+'?'+params);
};
function rememberSession(){if(token)gameSaveSet('kimarite_session',token);if(sessionSetup)gameSaveSet('kimarite_setup',JSON.stringify(sessionSetup));gameSaveSet('kimarite_actions',JSON.stringify(actionJournal))}
async function recoverSession(){if(!sessionSetup)throw new Error('This bout expired and has no recovery data. Please start a new bout.');const restored=await api('/api/session',sessionSetup);let state=restored.state;for(const command of actionJournal){const next=await api('/api/session/'+restored.token+'/action',command);state=next.state}token=restored.token;rememberSession();return state}
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function btn(text,fn,cls=''){const b=node('button',cls,text);b.onclick=fn;return b}
function card(c,fn,enabled=true){const b=btn(displayCardName(c.name),fn,'card'+(c.is_kimarite?' kimarite':''));const o=node('div','orb','POWER '+c.power+'  ·  TECH '+c.technique+'  ·  SPIRIT '+c.spirit);b.append(o);b.disabled=!enabled;return b}
function names(cards){return cards.map(c=>displayCardName(c.name)).join(', ')||'—'}
function signedPosition(p){return Number.isInteger(p)?(p>0?'+':'')+p:'—'}
function sideBySideSummary(g){
 const side=g?.side_by_side;
 if(!side)return '';
 const resolve=signedPosition(side.resolution_position);
 const removal=signedPosition(side.removal_position);
 const favorable=side.favorable==='human'?'you':'opponent';
 const extra=side.card==='Spin Away'?' If disrupted, your opponent gains Okuritaoshi if you own Spin Away (or you gain it if your opponent owns Spin Away).':'';
 return side.card+' · '+side.owner_name+' owns Side-by-Side. Position NOW '+signedPosition(side.current_position)+
  ' (stored distance '+side.saved_distance+'). All Push is suppressed. If it survives to its owner’s next turn: Position '+resolve+
  ' (currently favors '+favorable+'). If removed early: Position '+removal+
  ' (no saved Position restored). The survival prediction changes if Momentum changes.'+extra;
}
function sideBySideOnPlayPreview(g,name){
 if(!g||!Number.isInteger(g.position)||!Number.isInteger(g.momentum))return '';
 if(g.side_by_side)return sideBySideSummary(g);
 const distance=Math.abs(g.position),resolve=g.momentum>=0?distance:-distance;
 const caveat=name==='Spin Away'?' Spin Away gains 1 Momentum first; that can change the orientation, and Momentum overflow can change the stored distance.':'';
 return 'If played now: Position '+signedPosition(g.position)+' → 0 (stored distance '+distance+
  '). While active all Push is suppressed. If it survives with current Momentum: Position '+
  signedPosition(resolve)+'. If removed early: Position 0 (no distance restored).'+caveat;
}
function zoneEffect(c,zone){
 const d=c.description||'';
 if(zone==='kimarite')return (d.match(/Win:\s*(.*?)(?=\s*On play:|$)/)||[])[1]||'Winning condition not available';
 if(['Gain Left Grip','Gain Right Grip','Uwate','Shitate'].includes(c.name))return 'Blocks 1 incoming Push; consumed when used, otherwise expires at the start of your next turn.';
 if(c.name==='Sonkyo')return 'Prevents the next negative effect against you; persists until consumed.';
 if(c.name==='Kannuki')return 'While active: suppresses opponent Grip benefits and Grip-building cards. Next turn: reduce both opposing Grips one level and make opponent Unstable (subject to prevention).';
 if(c.name==='Henka')return 'Blocks the first incoming Push. If it survives: gain 1 Momentum and make opponent Unstable. If disrupted: you become Unstable.';
 if(c.name==='Sidestep')return 'On survival: opponent becomes Unstable. '+(game?.side_by_side?.card===c.name?sideBySideSummary(game):'While Side-by-Side, all Push is suppressed.');
 if(c.name==='Spin Away')return 'On disruption: opponent gains Okuritaoshi. '+(game?.side_by_side?.card===c.name?sideBySideSummary(game):'While Side-by-Side, all Push is suppressed.');
 const m=d.match(/(?:Temporary(?: \([^)]*\))?|While active:|Next turn:|On each later turn:|At the start of your next turn:)[\s:]*(.*)$/i);
 return m?m[0]:d.replace(/^.*?Exchange:\s*/,'')||'Active effect unavailable';
}

function inspect(c,playAction){$('inspect-name').textContent=displayCardName(c.name);$('inspect-orbs').textContent=c.zone_only?'':('Power '+(c.power??0)+' · Technique '+(c.technique??0)+' · Spirit '+(c.spirit??0));const desc=c.description||'This card needs a B10 wording audit before its full rules can be shown.';const preview=(!c.zone_only&&['Sidestep','Spin Away'].includes(c.name))?sideBySideOnPlayPreview(game,c.name):'';const effect=$('inspect-effect');effect.replaceChildren();const terms=Object.keys((game&&game.glossary)||{}).sort((a,b)=>b.length-a.length);const split=terms.length?new RegExp('\\b('+terms.join('|')+')\\b','gi'):null;const chunks=split?desc.split(split):[desc];for(const chunk of chunks){const key=terms.find(t=>t.toLowerCase()===chunk.toLowerCase());if(key){const link=btn(chunk,()=>{const old=$('glossary-detail');if(old)old.remove();const panel=node('p','glossary-detail',key+': '+game.glossary[key]);panel.id='glossary-detail';effect.after(panel)},'term-link');link.type='button';effect.append(link)}else effect.append(document.createTextNode(chunk))}if(preview)effect.append(node('p','side-by-side-preview',preview));$('inspect-orbs').textContent+=' · '+(c.timing||'')+(c.description_status==='needs_audit'?' · TEXT PENDING AUDIT':'');$('inspect-actions').replaceChildren();if(c.unavailable_reason)$('inspect-actions').append(node('p','unavailable-reason','Cannot play: '+c.unavailable_reason));if(playAction)$('inspect-actions').append(btn('Play this card',()=>{$('inspect').close();playAction()},'confirm'));$('inspect').showModal()}
$('inspect-close').onclick=()=>$('inspect').close();
function logText(){if(!game)return '';return ['KIMARITE — BOUT HISTORY',game.human.name+' vs '+game.opponent.name,'Turn '+game.turn+(game.finished?' — Bout over':'')+(sessionSetup&&Number.isSafeInteger(sessionSetup.seed)?' · Seed '+sessionSetup.seed:''),'',...(game.events||[])].join('\n')}
$('copy-history').onclick=async()=>{const value=logText();if(!value){$('copy-status').textContent='Start a bout first.';return}try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(value)}else{const field=document.createElement('textarea');field.value=value;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();if(!document.execCommand('copy'))throw new Error('Copy not supported');field.remove()}$('copy-status').textContent='Copied!'}catch(e){$('copy-status').textContent='Select and copy the log below.';const field=document.createElement('textarea');field.value=value;field.rows=8;field.className='log-copy-fallback';$('copy-status').after(field);field.focus();field.select()}};

function showDiscard(owner,person){$('discard-title').textContent=person+' — Discard pile ('+owner.discard.length+')';const list=$('discard-list');list.replaceChildren();if(!owner.discard.length)list.append(node('p','','Discard pile is empty.'));for(const [index,c] of owner.discard.entries()){const item=node('div','discard-entry');item.append(node('span','',String(index+1)+'. '+displayCardName(c.name)),btn('Inspect',()=>{ $('discard-dialog').close();inspect(c) },'choice-inspect'));list.append(item)}$('discard-dialog').showModal()}
$('discard-close').onclick=()=>$('discard-dialog').close();

let management=null;
function managementSave(){gameSaveSet('kimarite_management',JSON.stringify(management))}
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
function completedBlock(m){
 return m.results.length>0&&m.results.length%3===0;
}
function unresolvedRewards(m){
 if(!m||m.opening_mode!=='b11_live'||!m.draft_picks||!completedBlock(m))return [];
 return m.results.slice(-3).filter(r=>r.won
  ?!r.duplication_resolved
  :r.won===false&&isB12Campaign(m)&&r.opponent_id&&r.assigned_cards?.length===3&&!r.rematch_top_card);
}
function availableRewardCards(m,result){
 if((m.duplicated_indices||[]).length>=12)return [];
 return (result.assigned_cards||[]).filter(c=>{
  if(!c.instance_id?.startsWith('original:'))return false;
  const i=Number(c.instance_id.slice(9));
  return Number.isInteger(i)&&i>=0&&i<28&&!(m.duplicated_indices||[]).includes(i);
 });
}
function calculateCardRecords(m){
 const plays=new Map(),wins=new Map(),kims=new Set(m.kimarite_names||[]);
 for(const r of m.results){
  const seen=new Set();
  for(const name of r.human_card_plays||[]){
   plays.set(name,(plays.get(name)||0)+1);seen.add(name);
  }
  if(r.won)for(const name of seen)wins.set(name,(wins.get(name)||0)+1);
 }
 // Only cards tied for the highest raw count are eligible for a category.
 // Find distinct category winners wherever possible; a sole count leader
 // cannot be displaced merely to make the results more varied.
 const categories=[
  ['most_played_card',plays,false],
  ['most_played_kimarite',plays,true],
  ['most_winning_card',wins,false],
  ['most_winning_kimarite',wins,true]
 ];
 const candidates=new Map();
 for(const [key,counts,kimariteOnly] of categories){
  const eligible=[...counts.entries()].filter(([name,n])=>n>0&&(!kimariteOnly||kims.has(name)));
  const best=eligible.length?Math.max(...eligible.map(([,n])=>n)):0;
  candidates.set(key,eligible.filter(([,n])=>n===best).map(([name])=>name).sort((a,b)=>a.localeCompare(b)));
 }
 const keys=categories.map(([key])=>key);
 // Maximum bipartite matching: first reserve sole leaders, then use
 // augmenting paths to maximize the number of different displayed cards.
 const order=[...keys].sort((a,b)=>candidates.get(a).length-candidates.get(b).length||keys.indexOf(a)-keys.indexOf(b));
 const cardOwner=new Map();
 function match(key,seen){
  for(const name of candidates.get(key)){
   if(seen.has(name))continue;
   seen.add(name);
   const previous=cardOwner.get(name);
   if(previous===undefined||match(previous,seen)){
    cardOwner.set(name,key);return true;
   }
  }
  return false;
 }
 for(const key of order)match(key,new Set());
 const selected=new Map([...cardOwner].map(([name,key])=>[key,name]));
 // When overlap cannot be avoided, still report the true leader.
 for(const key of keys){
  if(!selected.has(key)&&candidates.get(key).length)selected.set(key,candidates.get(key)[0]);
 }
 const records={};
 for(const [key,counts] of categories){
  const name=selected.get(key);
  records[key]=name?{name,count:counts.get(name)}:null;
 }
 return records;
}
function completedRewards(m){
 return !unresolvedRewards(m).length;
}
function updateTournamentLeaders(m){
 m.card_records=calculateCardRecords(m);
}
function openBlockRewards(){
 const m=management;if(!m||!completedBlock(m))return false;
 const pending=unresolvedRewards(m);
 if(!pending.length){
  $('management-rewards').hidden=true;
  return false;
 }
 const r=pending[0],i=m.results.indexOf(r);
 const choices=r.won?availableRewardCards(m,r):r.assigned_cards;
 if(!choices.length){
  r.duplication_resolved=true;managementSave();return openBlockRewards();
 }
 $('management-board').hidden=true;
 $('management-rewards').hidden=false;
 $('management-next').hidden=true;
 const rewards=$('management-rewards');
 rewards.dataset.result=r.won?'win':'loss';
 $('management-reward-progress').textContent=r.won
  ?'Bout '+(i+1)+' · Win. Duplicate one assigned original for your deck ('+
    (28+(m.duplicated_indices||[]).length)+'/40 cards).'
  :'Bout '+(i+1)+' · Loss to '+(r.opponent_name||r.opponent)+
    '. Choose one of your three opening cards to go on top of your deck when you next face this wrestler.';
 const panel=$('management-reward-cards');panel.replaceChildren();
 for(const choice of choices){
  // Older saved bout records only held name and identity. Recover the
  // detailed card rules from the current nine-card deal if available.
  const c={...(m.cards.find(card=>card.instance_id===choice.instance_id)||{}),...choice};
  const wrapper=node('div','management-card reward-card');
  wrapper.append(card(c,()=>inspect(c)));
  const description=c.description||'Detailed card effect unavailable. Inspect the card for any available rules.';
  wrapper.append(node('p','reward-effect',description));
  wrapper.append(btn('Inspect full card',()=>inspect(c),'reward-inspect'));
  const label=r.won?'Duplicate ':'Save for rematch: ';
  const select=btn(label+displayCardName(c.name),()=>{
   if(!management||!unresolvedRewards(management).includes(r))return;
   if(r.won){
    const originalIndex=Number(c.instance_id.slice(9));
    if(!Number.isInteger(originalIndex)||management.duplicated_indices.includes(originalIndex))return;
    management.duplicated_indices.push(originalIndex);
    r.duplicated_card=c.name;r.duplication_resolved=true;
   }else{
    r.rematch_top_card=c.name;
   }
   managementSave();
   if(!openBlockRewards()){
    $('management-notice').textContent='Round rewards resolved. Your deck now has '+(28+management.duplicated_indices.length)+' cards.';
    managementStatus();
    if(management.results.length===15)showTournamentFinal();
    else $('management-next').hidden=false;
   }
  });
  wrapper.append(select);panel.append(wrapper);
 }
 $('management-rewards').scrollIntoView({behavior:'smooth'});
 return true;
}
function yearHistory(m){
 return Array.isArray(m?.tournament_history)?m.tournament_history:[];
}
function tournamentSummary(m){
 if(!Array.isArray(m?.results)||m.results.length!==15){
  throw new Error('A tournament must finish 15 bouts before advancing the year.');
 }
 const results=m.results.map(r=>({
  won:!!r.won,opponent:r.opponent_name||r.opponent,finish:r.finish,
  turns:r.turns,duplicated_card:r.duplicated_card||null
 }));
 const wins=results.filter(r=>r.won).length;
 return {tournament:yearHistory(m).length+1,wins,losses:15-wins,results};
}
function showYearStatus(m){
 const h=yearHistory(m);
 const current=Array.isArray(m?.results)?m.results:[];
 const winCount=h.reduce((n,t)=>n+t.wins,0)+current.filter(r=>r.won).length;
 const lossCount=h.reduce((n,t)=>n+t.losses,0)+current.filter(r=>!r.won).length;
 if(m?.opening_mode==='classic'){
  $('year-record').textContent='Legacy practice tournament · no yearly progression';
  $('year-history').textContent='';
  return;
 }
 const number=Math.min(6,h.length+1);
 const completed=h.length+(current.length===15?1:0);
 $('year-record').textContent='Tournament '+number+' of 6 · Year record '+winCount+'–'+lossCount+
  ' · '+completed+' tournament'+(completed===1?'':'s')+' completed'+
  (completed===6?' · Year complete':'');
 const summaries=[...h];
 if(current.length===15)summaries.push(tournamentSummary(m));
 $('year-history').textContent=summaries.length?
  summaries.map(t=>'Tournament '+t.tournament+': '+t.wins+'–'+t.losses).join(' · '):
  'Your tournament results will appear here.';
}
function tournamentFinalText(m){
 const wins=m.results.filter(r=>r.won).length;
 const lines=['KIMARITE — TOURNAMENT RESULTS',m.human+' · Tournament '+(yearHistory(m).length+1)+' of 6 · '+wins+' wins, '+(m.results.length-wins)+' losses'];
 if(m.opening_mode!=='classic'){
  const history=[...yearHistory(m),tournamentSummary(m)];
  const totalWins=history.reduce((n,t)=>n+t.wins,0);
  lines.push('Sumo year: '+totalWins+'–'+(history.length*15-totalWins)+' over '+history.length+' tournament(s)');
  for(const result of history)lines.push('Tournament '+result.tournament+': '+result.wins+'–'+result.losses);
 }
 for(let i=0;i<m.results.length;i++){
  const r=m.results[i];
  lines.push('Bout '+(i+1)+' · '+(r.won?'WIN':'LOSS')+' vs '+(r.opponent_name||r.opponent)+' · '+displayCardName(r.finish)+' · Turn '+r.turns+(r.duplicated_card?' · Duplicated '+displayCardName(r.duplicated_card):''));
 }
 const stats=calculateCardRecords(m);
 for(const [key,label] of [['most_played_card','Most played card'],['most_played_kimarite','Most played Kimarite'],['most_winning_card','Most winning card'],['most_winning_kimarite','Most winning Kimarite']]){
  const v=stats[key];lines.push(label+': '+(v?displayCardName(v.name)+' ('+v.count+')':'None'));
 }
 return lines.join('\n');
}
function showTournamentFinal(){
 const m=management;
 if(!m||m.results.length!==15||!completedRewards(m))return;
 const dialog=$('tournament-final');
 const wins=m.results.filter(r=>r.won).length;
 $('tournament-final-record').textContent=wins+'–'+(15-wins);
 $('tournament-final-player').textContent=m.human+' · Tournament '+(yearHistory(m).length+1)+' of 6 · 15 bouts completed · '+(m.draft_picks?28+(m.duplicated_indices||[]).length+' cards in final deck':'Classic deck');
 if(m.opening_mode!=='classic'){
  const history=[...yearHistory(m),tournamentSummary(m)];
  const totalWins=history.reduce((n,t)=>n+t.wins,0);
  $('tournament-year-record').textContent='Year record: '+totalWins+'–'+(history.length*15-totalWins)+
   ' after '+history.length+' of 6 tournaments'+(history.length===6?' · Year complete!':'');
  $('tournament-year-history').textContent=history.map(t=>
   'Tournament '+t.tournament+': '+t.wins+'–'+t.losses).join(' · ');
 }else {
  $('tournament-year-record').textContent='Classic practice tournament';
  $('tournament-year-history').textContent='';
 }
 const records=$('tournament-card-records');records.replaceChildren();
 const stats=calculateCardRecords(m);m.card_records=stats;managementSave();
 const names=[['most_played_card','Most played card'],['most_played_kimarite','Most played Kimarite'],['most_winning_card','Most winning card'],['most_winning_kimarite','Most winning Kimarite']];
 records.append(node('h3','','Tournament card records (raw counts)'));
 for(const [key,title] of names){const result=stats[key];const line=node('div','tournament-final-bout');line.append(node('strong','',title),node('span','',result?displayCardName(result.name):'No qualifying plays'),node('small','',result?result.count+' '+(key.includes('winning')?'winning bouts':'plays'):'—'));records.append(line)}
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
    node('small','',displayCardName(r.finish)+' · Turn '+r.turns));
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
function managementStatus(){if(!management)return;const m=management;const progress=$('management-progress');progress.hidden=false;showB12Banzuke(m);if(!isB12Campaign(m)&&game&&game.finished&&activeTournamentBout()===m.round&&m.results.length===m.round){m.results.push({human:m.human,opponent:m.opponents[m.round],opponent_style:m.opponents[m.round],opponent_name:null,won:game.winner==='A',turns:game.turn,finish:game.win_method||'Unknown',seed:sessionSetup?.seed??null,human_card_plays:[...(game.opening?.human?.committed||[]).map(c=>c.name),...(game.human_card_plays||[])],assigned_cards:(m.groups[m.round%3]||[]).map(k=>m.cards.find(c=>c.deal_index===k)).filter(Boolean).map(c=>({...c})),duplication_resolved:false});updateTournamentLeaders(m);managementSave();managementBoard()}const wins=m.results.filter(r=>r.won).length;showYearStatus(m);progress.replaceChildren(node('h3','','Tournament '+(yearHistory(m).length+1)+' of 6 · Round '+(Math.floor(m.round/3)+1)+' of 5'));progress.append(node('p','','Completed '+m.results.length+'/15 · Record '+wins+'–'+(m.results.length-wins)));$('management-next').hidden=!(game&&game.finished&&activeTournamentBout()===m.round&&m.results.length===m.round+1&&(m.round<14||unresolvedRewards(m).length>0));$('management-next').textContent=m.round%3===2?'Resolve round rewards / Deal next nine':'Next bout';const table=node('div','tournament-results');table.append(node('h3','',m.results.length===15?'Final results':'Bout results'));for(let round=0;round<5;round++){const subset=m.results.slice(round*3,round*3+3);if(!subset.length)continue;const section=node('section','tournament-round');section.append(node('h4','','Round '+(round+1)+' · '+subset.filter(r=>r.won).length+'–'+(subset.length-subset.filter(r=>r.won).length)));for(const [index,r] of subset.entries()){const row=node('div','tournament-result '+(r.won?'tournament-win':'tournament-loss'));row.append(node('strong',r.won?'result-win':'result-loss','Bout '+(round*3+index+1)+' · '+(r.won?'Win':'Loss')));row.append(node('span','',r.opponent_name? r.opponent_name+' ('+(r.opponent_style||r.opponent)+(r.opponent_rank?' · '+banzukeRankLabel(r.opponent_rank):'')+')':(r.opponent_style||r.opponent)));row.append(node('span','',r.turns!=null?'Turn '+r.turns:'Turns unavailable'));row.append(node('span','',displayCardName(r.finish||'Finisher unavailable')));if(r.duplicated_card)row.append(node('small','','Duplicated: '+displayCardName(r.duplicated_card)));section.append(row)}table.append(section)}progress.append(table);if(game?.finished&&activeTournamentBout()===m.round&&m.results.length!==m.round+1)progress.append(node('p','management-error','Tournament result could not be recorded. Keep this bout open and report the seed; do not start another bout.'));$('management-summary').hidden=m.results.length!==15||!completedRewards(m);$('management-new').hidden=m.results.length!==15||m.opening_mode==='classic'||!completedRewards(m)||yearHistory(m).length>=5;$('new-wrestler').hidden=m.opening_mode!=='b11_live'||m.results.length!==15||!completedRewards(m)||yearHistory(m).length<5;if(m.results.length===15){$('management-next').hidden=unresolvedRewards(m).length===0;progress.prepend(node('strong','','Tournament complete: '+wins+'–'+(15-wins)))}}
let playerShikonaPool=null;
async function randomPlayerShikona(){
 const field=$('wrestler-name'),notice=$('random-name-status'),button=$('random-wrestler-name');
 button.disabled=true;
 notice.textContent='';
 try{
  if(!playerShikonaPool){
   const response=await api('/api/shikona');
   if(!Array.isArray(response.names)||response.names.length<60)throw new Error('Fictional name list is unavailable.');
   playerShikonaPool=response.names;
  }
  const previous=field.value.trim().toLocaleLowerCase();
  const choices=playerShikonaPool.filter(name=>
   typeof name==='string'&&name.length>0&&name.length<=32&&name.toLocaleLowerCase()!==previous);
  if(!choices.length)throw new Error('No alternative fictional names are available.');
  field.value=choices[Math.floor(Math.random()*choices.length)];
  notice.textContent='Random shikona selected. You can still edit it.';
 }catch(error){
  notice.textContent='Could not choose a random name. You can enter one yourself.';
 }finally{
  button.disabled=false;
 }
}
$('random-wrestler-name').onclick=randomPlayerShikona;

const CREATED_STAT_NAMES={power:'Power',technique:'Technique',spirit:'Spirit'};
function creationChoices(){
 const food=$('create-food').value,training=$('create-training').value;
 const allowed=food===training?Object.keys(CREATED_STAT_NAMES).filter(k=>k!==food):[food,training];
 const final=$('create-final'),previous=final.value;
 final.replaceChildren();
 for(const k of allowed){const option=node('option','',CREATED_STAT_NAMES[k]);option.value=k;final.append(option)}
 if(allowed.includes(previous))final.value=previous;
 const result={power:0,technique:0,spirit:0};
 for(const k of [food,training,final.value])result[k]++;
 $('create-summary').textContent=Object.entries(result).map(([k,v])=>CREATED_STAT_NAMES[k]+' '+v).join(' · ');
 return result;
}
for(const id of ['create-food','create-training'])$(id).addEventListener('change',creationChoices);
$('create-final').addEventListener('change',creationChoices);
$('management-opening-mode').addEventListener('change',()=>{
 $('b11-creation').hidden=$('management-opening-mode').value!=='b11_live';
});
creationChoices();
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
function b11CommittedTachiaiTotals(cards,indices,base){
 const committed=cards.filter((_,i)=>indices.has(i));
 const orbs=b11PreviewTotals(committed);
 return ['power','technique','spirit'].map((k,i)=>Number(base[k]||0)+1+orbs[i]);
}
function b11TachiaiPreview(m,group){
 const box=node('div','tachiai-preview');
 const slots=m.groups[group];
 if(slots.some(i=>i===null)){box.textContent='Select three cards to preview their all-committed Tachiai.';return box}
 const cards=slots.map(i=>m.cards.find(c=>c.deal_index===i));
 if(cards.some(c=>!c)){box.textContent='Card selection unavailable.';return box}
 const base=m.created_stats||b11PreviewBase(m.human),orbs=b11PreviewTotals(cards);
 box.append(node('strong','','All three committed — projected Tachiai'));
 for(const [i,k] of ['power','technique','spirit'].entries()){
  box.append(node('p','',k[0].toUpperCase()+k.slice(1)+': '+(base[k]+1+orbs[i])+' (base '+base[k]+' + cards '+orbs[i]+' + 1)'));
 }
 box.append(node('small','','Before reveal-chain bonuses. AI starts with six base points plus two hidden opening cards; revealed only after commitment.'));
 return box;
}
// Every three-bout block deals nine physical cards. Once a bout starts its
// allocation is committed; only future bouts may exchange their cards.
let launchingTournamentBout=null;
function isB12Campaign(m){return !!(m?.division_roster&&m?.division_league)}
function assignB12Block(m,reply){
 const start=Math.floor(m.round/3)*3;
 if(!Array.isArray(reply.opponents)||reply.opponents.length!==3||reply.league?.day!==m.round)
  throw new Error('The next three opponents could not be planned safely.');
 m.division_league=reply.league;
 m.opponents??=Array(15).fill(null);
 m.b12_opponent_ids??=Array(15).fill(null);
 for(let j=0;j<3;j++){
  m.opponents[start+j]=reply.opponents[j].name;
  m.b12_opponent_ids[start+j]=reply.opponents[j].id;
 }
}
function b12Opponent(m,bout){
 const id=m?.b12_opponent_ids?.[bout];
 return id?m.division_league?.wrestlers?.find(w=>w.id===id):null;
}
function banzukeTitle(rank){
 if(!Number.isInteger(rank)||rank<1||rank>42)return '';
 const titles=['East Yokozuna','West Yokozuna','East Ozeki','West Ozeki','East Ozeki 2',
  'East Sekiwake','West Sekiwake','East Komusubi','West Komusubi'];
 if(rank<=titles.length)return titles[rank-1];
 const index=rank-titles.length-1;
 return (index%2===0?'East':'West')+' Maegashira '+(Math.floor(index/2)+1);
}
function banzukeRankLabel(rank){
 return '#'+rank+' · '+banzukeTitle(rank);
}
function b12OpponentLabel(m,bout){
 const foe=b12Opponent(m,bout);
 return foe?foe.name+' · '+banzukeRankLabel(foe.rank)+' · '+foe.style+' · '+foe.wins+'–'+foe.losses:
  (m.opponents[bout]||'Opponent not yet scheduled');
}
function showB12Banzuke(m){
 const panel=$('b12-banzuke');
 if(!panel)return;
 panel.hidden=!isB12Campaign(m);
 if(!isB12Campaign(m))return;
 const league=m.division_league;
 const people=[...league.wrestlers].sort((a,b)=>a.rank-b.rank);
 const you=people.find(w=>w.id==='player');
 $('b12-banzuke-heading').textContent='Banzuke · '+people.length+' wrestlers · Day '+league.day+'/15 · You: '+banzukeRankLabel(you.rank)+' ('+you.wins+'–'+you.losses+')';
 const entries=$('b12-banzuke-entries');entries.replaceChildren();
 for(const w of people){
  const row=node('div','banzuke-entry'+(w.id==='player'?' banzuke-player':''));
  const rank=node('div','banzuke-rank');
  rank.append(node('strong','','#'+w.rank),node('small','',banzukeTitle(w.rank)));
  row.append(rank,
   node('span','',w.name+(w.id==='player'?' · YOU':'')),
   node('small','',w.style),
   node('b','',''+w.wins+'–'+w.losses));
  entries.append(row);
 }
}

function currentBlockStart(m){return Math.floor(m.round/3)*3}
function allocationLockState(m,group){
 const bout=currentBlockStart(m)+group;
 if(m.results.length>bout)return 'completed';
 if(m.locked_bouts?.[bout])return 'started';
 // Recover old saved live bouts that predate the explicit lock field.
 if(m===management&&token&&activeTournamentBout()===bout)return 'started';
 return null;
}
function syncBoutLocks(m){
 if(!m.locked_bouts)m.locked_bouts={};
 let changed=false;
 for(let group=0;group<3;group++){
  const bout=currentBlockStart(m)+group,record=m.results[bout];
  if(record){
   const original=(record.assigned_cards||[]).map(c=>c.deal_index);
   const valid=original.length===3&&new Set(original).size===3&&original.every(id=>m.cards.some(c=>c.deal_index===id));
   if(valid&&JSON.stringify(m.locked_bouts[bout])!==JSON.stringify(original)){
    m.locked_bouts[bout]=[...original];changed=true;
   }else if(!valid&&!m.locked_bouts[bout]){
    m.locked_bouts[bout]=[...m.groups[group]];changed=true;
   }
  }
  const saved=m.locked_bouts[bout];
  if(Array.isArray(saved)&&saved.length===3&&saved.every(id=>m.cards.some(c=>c.deal_index===id))
     &&JSON.stringify(saved)!==JSON.stringify(m.groups[group])){
   m.groups[group]=[...saved];changed=true;
  }
 }
 // Older saves may have already reassigned a completed bout's card. Restore
 // its recorded opening and free any collision in future, editable slots.
 const reserved=new Set();
 for(let group=0;group<3;group++)if(allocationLockState(m,group))
  for(const id of m.groups[group])if(id!==null)reserved.add(id);
 for(let group=0;group<3;group++)if(!allocationLockState(m,group))
  for(let slot=0;slot<3;slot++)if(reserved.has(m.groups[group][slot])){
   m.groups[group][slot]=null;changed=true;
  }
 if(changed&&m===management)managementSave();
}
function slotAcceptsCard(m,slot,id){
 if(id===null||m.opening_mode!=='classic')return true;
 const card=m.cards.find(c=>c.deal_index===id);
 return !!card&&(slot===0?card.is_kimarite:!card.is_kimarite);
}
function allBoutCardsAssigned(m){
 if(!Array.isArray(m.groups)||m.groups.length!==3)return false;
 const slots=m.groups.flat();
 return slots.length===9&&slots.every((id,n)=>Number.isInteger(id)
  &&m.cards.some(c=>c.deal_index===id)&&slotAcceptsCard(m,n%3,id))
  &&new Set(slots).size===9;
}
function changeBoutAssignment(m,group,slot,id){
 if(!m.groups[group]||slot<0||slot>2||allocationLockState(m,group)||launchingTournamentBout!==null)return false;
 if(id!==null&&(!Number.isInteger(id)||!m.cards.some(c=>c.deal_index===id)||!slotAcceptsCard(m,slot,id)))return false;
 const previous=m.groups[group][slot];
 if(previous===id)return true;
 if(id!==null)for(let i=0;i<3;i++)for(let j=0;j<3;j++){
  if(i===group&&j===slot)continue;
  if(m.groups[i][j]!==id)continue;
  if(allocationLockState(m,i)||!slotAcceptsCard(m,j,previous))return false;
  m.groups[i][j]=previous; // Direct swap among upcoming bouts.
 }
 m.groups[group][slot]=id;
 return true;
}
function managementBoard(){
 if(!management)return;
 const m=management;
 syncBoutLocks(m);
 showB12Banzuke(m);
 const chosen=m.groups.flat().filter(id=>id!==null),lockedIDs=new Set();
 for(let group=0;group<3;group++)if(allocationLockState(m,group))
  for(const id of m.groups[group])if(id!==null)lockedIDs.add(id);
 const cards=$('management-cards');cards.replaceChildren();
 for(const c of m.cards){
  const wrapper=node('div','management-card');
  wrapper.append(card(c,()=>inspect(c)));
  wrapper.append(node('small','',lockedIDs.has(c.deal_index)?'Locked to completed / started bout'
   :chosen.includes(c.deal_index)?'Assigned to an upcoming bout':'Available'));
  cards.append(wrapper);
 }
 const groups=$('management-groups');groups.replaceChildren();
 for(let group=0;group<3;group++){
  const locked=allocationLockState(m,group);
  const bout=currentBlockStart(m)+group;
  const box=node('div','management-group'+(locked?' management-group-locked':''));
  box.append(node('h3','','Round '+(Math.floor(m.round/3)+1)+' · Bout '+(group+1)
   +' vs '+(isB12Campaign(m)?b12OpponentLabel(m,bout):m.opponents[bout])
   +(locked?' · '+(locked==='completed'?'COMPLETED':'STARTED')+' — LOCKED':' · editable')));
  const opponentInfo=isB12Campaign(m)?b12Opponent(m,bout):null;
  const rematchCard=opponentInfo&&!locked?savedRematchCard(m,opponentInfo.id):null;
  if(rematchCard)box.append(node('strong','rematch-draw-note',
   'Rematch · your first draw: '+displayCardName(rematchCard)));
  if(opponentInfo&&opponentInfo.format_description){
   const detail=node('details','opponent-deck-details');
   detail.append(node('summary','','Testing: opponent deck format'),
     node('p','',opponentInfo.format_description));
   box.append(detail);
  }
  if(locked)box.append(node('p','assignment-locked-note',locked==='completed'
   ?'Bout completed: its three original cards cannot be changed.'
   :'Bout already started: its three original cards are committed.'));
  for(let slot=0;slot<3;slot++){
   const classic=m.opening_mode==='classic';
   const type=classic?(slot===0?'Kimarite':slot===1?'Prepared Tachiai':'First draw'):('Opening card '+(slot+1));
   const select=node('select','');select.disabled=!!locked||launchingTournamentBout!==null;
   const blank=node('option','',type+' — choose');blank.value='';select.append(blank);
   for(const c of m.cards){
    if(!slotAcceptsCard(m,slot,c.deal_index))continue;
    const other=m.groups.findIndex(row=>row.includes(c.deal_index));
    const otherSlot=other<0?-1:m.groups[other].indexOf(c.deal_index);
    if(other>=0&&(other!==group||otherSlot!==slot)){
     if(allocationLockState(m,other)||!slotAcceptsCard(m,otherSlot,m.groups[group][slot]))continue;
    }
    const text=displayCardName(c.name)+' · '+(c.deal_index+1)
     +(other>=0&&(other!==group||otherSlot!==slot)?' · swap with Bout '+(other+1):'');
    const option=node('option','',text);option.value=c.deal_index;select.append(option);
   }
   select.value=m.groups[group][slot]===null?'':String(m.groups[group][slot]);
   select.onchange=()=>{
    const next=select.value===''?null:Number(select.value);
    if(changeBoutAssignment(m,group,slot,next))managementSave();
    else $('management-notice').textContent='Cannot change a card committed to a started or completed bout.';
    managementBoard();
   };
   box.append(node('label','',type),select);
  }
  if(m.opening_mode!=='classic')box.append(b11TachiaiPreview(m,group));
  groups.append(box);
 }
 const atStart=m.round%3===0&&m.results.length===m.round
  &&!allocationLockState(m,0)&&launchingTournamentBout===null;
 $('management-start').hidden=!atStart;
 $('management-start').disabled=!atStart||!allBoutCardsAssigned(m);
 $('management-start').textContent='Start Bout '+(m.round+1)+' · lock its three cards';
}
function savedRematchCard(m,opponentId){
 const results=[...yearHistory(m).flatMap(basho=>basho.results),...m.results];
 const last=results.findLast(result=>result.opponent_id===opponentId);
 return last?.won===false?last.rematch_top_card:null;
}
async function managementRound(){
 const m=management;if(!m)return;
 const i=m.round,group=i%3;
 if(launchingTournamentBout!==null)throw new Error('A bout is already being started.');
 syncBoutLocks(m);
 if(m.results.length!==i)throw new Error('Tournament is out of sync: '+m.results.length+' completed, expected '+i+'. Cannot advance safely.');
 if(allocationLockState(m,group))throw new Error('This bout has already started. Its cards are locked.');
 if(!allBoutCardsAssigned(m))throw new Error('Assign all nine distinct cards across the three upcoming bouts first.');
 const committed=[...m.groups[group]];
 const take=k=>m.cards.find(c=>c.deal_index===committed[k]).name;
 const request={human:m.human,opponent:m.opponents[i],seed:m.seed+i+1};
 if(m.opening_mode==='classic')request.opening={kimarite:take(0),prepared:take(1),top:take(2)};
 else {
  request.opening_mode='b11_live';request.opening_cards=[take(0),take(1),take(2)];
  if(m.created_stats)request.created_stats=m.created_stats;
  if(m.draft_picks){request.starting_cards=m.starting_cards;request.draft_picks=m.draft_picks;request.draft_seed=m.draft_seed;request.duplicated_indices=m.duplicated_indices||[]}
 }
 if(isB12Campaign(m)){
  if(m.division_league.day!==i||m.b12_opponent_ids?.[i]===undefined)
   throw new Error('The live banzuke is not synchronized with the upcoming bout.');
  const paired=await api('/api/b12/campaign/pair',{roster:m.division_roster,league:m.division_league});
  if(paired.opponent.id!==m.b12_opponent_ids[i]||paired.opponent.name!==request.opponent)
   throw new Error('Scheduled B12 opponent changed after card allocation.');
  m.division_league=paired.league;
  managementSave(); // Persist frozen 21-pair day before the player enters the ring.
  request.b12_opponent_ai=paired.opponent;
  const rematchCard=savedRematchCard(m,paired.opponent.id);
  if(rematchCard)request.b12_rematch_top_card=rematchCard;
  request.b12_player_rank=m.division_roster.player.rank;
  request.b12_campaign={seed:m.division_roster.seed,basho:m.division_roster.completed_basho||0,
   day:i,opponent_id:paired.opponent.id};
 }
 launchingTournamentBout=i;
 $('management-start').disabled=true;
 try{
  const r=await api('/api/session',request);
  // Lock after the server accepts the bout, before a result can be recorded.
  m.locked_bouts??={};m.locked_bouts[i]=committed;
  managementSave();managementBoard();
  sessionSetup={...request,tournament_bout:i};actionJournal=[];token=r.token;game=null;
  render(r.state);
  $('seed-used').textContent='Bout seed: '+request.seed;
  $('management-notice').textContent='Bout '+(i+1)+': '+request.human+' vs '+request.opponent;
  managementSave();document.querySelector('.arena').scrollIntoView({behavior:'smooth'});
 }finally{
  launchingTournamentBout=null;
  if(management===m)managementBoard();
 }
}
function earnedNextStartingCards(m){
 // Copy the physical originals selected as duplication rewards, in earned order.
 // All other cards leave the deck when the next tournament draft begins.
 const originals=[...m.starting_cards,...m.draft_picks];
 const indices=m.duplicated_indices||[];
 if(originals.length!==28||indices.length>12||new Set(indices).size!==indices.length){
  throw new Error('Unable to recover earned cards for the next tournament.');
 }
 return indices.map(i=>{
  if(!Number.isInteger(i)||i<0||i>=28)throw new Error('Invalid earned card index.');
  return originals[i];
 });
}
const B11_STARTER_SUITE=['Yorikiri','Oshidashi','Oshi','Tsuki','Gain Left Grip','Gain Right Grip','Give Ground','Sonkyo'];
let activeDraft=null;
function saveDraft(){if(activeDraft)gameSaveSet('kimarite_active_draft',JSON.stringify(activeDraft));else gameSaveRemove('kimarite_active_draft')}
async function offerDraft(){
 const d=activeDraft;if(!d)return;
 setGameLocation('heya');
 showYearStatus(d);
 showB12Banzuke(d.division_roster&&d.division_league?d:null);
 const owned=[...d.starting_cards,...d.picks];
 $('b11-draft').hidden=false;$('management-board').hidden=true;$('management-deal').hidden=true;
 $('management-opening-mode').disabled=true;$('management-deck').disabled=true;$('b11-creation').hidden=true;
 $('draft-progress').textContent=owned.length+' / 28 cards · '+d.picks.length+' drafted · '+owned.filter(name=>d.kimarite_names.includes(name)).length+' Kimarite';
 $('draft-owned').textContent='Owned: '+owned.map(displayCardName).join(', ');
 const offers=$('draft-offers');offers.replaceChildren();
 if(owned.length===28){await finishDraft();return}
 const response=await api('/api/b11/draft/offer',{starting_cards:d.starting_cards,picks:d.picks,seed:d.seed});
 const count=owned.filter(name=>d.kimarite_names.includes(name)).length;
 $('draft-instruction').textContent=count<3?'Choose a Kimarite (minimum three)':'Choose one of three cards'+(count>=8?' · Kimarite maximum reached':'');
 for(const c of response.choices){
  const wrap=node('div','management-card');
  const pick=card(c,async()=>{
   try{
    offers.querySelectorAll('button').forEach(x=>x.disabled=true);
    d.picks.push(c.name);saveDraft();await offerDraft();
   }catch(e){$('management-notice').textContent=e.message}
  });
  wrap.append(pick,node('small','',c.is_kimarite?'Kimarite':'Technique / support'),btn('Inspect',()=>inspect(c),'choice-inspect'));
  offers.append(wrap);
 }
}
async function finishDraft(){
 const d=activeDraft;
 const first=await api('/api/b11/draft/deal',{starting_cards:d.starting_cards,picks:d.picks,draft_seed:d.seed,seed:d.seed});
 // This is a new B12 season, or a saved continuation after the rank update.
 // Use the same unique 60-format world across all six tournaments.
 const division=d.division_roster
  ?await api('/api/b12/campaign/plan',{roster:d.division_roster,league:d.division_league})
  :await api('/api/b12/campaign/new',{player_name:d.human,seed:d.world_seed??d.seed});
 management={human:d.human,seed:d.seed,opening_mode:'b11_live',created_stats:d.created_stats,tournament_history:d.tournament_history||[],
   starting_cards:d.starting_cards,draft_picks:d.picks,draft_seed:d.seed,kimarite_names:d.kimarite_names,duplicated_indices:[],
   cards:first.cards,groups:Array.from({length:3},()=>[null,null,null]),
   opponents:Array(15).fill(null),b12_opponent_ids:Array(15).fill(null),
   division_roster:division.roster,division_league:division.league,round:0,results:[]};
 assignB12Block(management,division);
 activeDraft=null;saveDraft();
 clearBoutSession(); // Avoid resurrecting an earlier finished bout during the new tournament.
 $('b11-draft').hidden=true;$('management-board').hidden=false;$('management-progress').hidden=true;
 $('management-next').hidden=true;showYearStatus(management);managementBoard();managementSave();
 $('management-notice').textContent='Your 28-card deck is drafted. Assign the nine cards to the first three bouts.';
}
$('management-deal').onclick=async()=>{
 try{
  const standard=$('management-opening-mode').value==='b11_live';
  // Human-created wrestler names do not come from the developer test roster.
  const draftedName=$('wrestler-name').value.trim();
  const continuing=standard&&management?.opening_mode==='b11_live'&&management.results.length===15;
  const human=standard?(continuing?management.human:draftedName):$('management-deck').value;
  if(standard&&(!human||human.length>32||Array.from(human).some(ch=>ch.codePointAt(0)<32||ch.codePointAt(0)===127))){
   throw new Error('Enter a wrestler name (1–32 visible characters).');
  }
  const seed=Math.floor(Math.random()*2147483647);
  if(standard){
   const previous=continuing?management:null;
   if(previous&&yearHistory(previous).length>=5)throw new Error('Six tournaments complete: the sumo year has ended.');
   const tournament_history=previous?[...yearHistory(previous),tournamentSummary(previous)]:[];
   const starting=previous?(previous.next_starting_cards??earnedNextStartingCards(previous)):B11_STARTER_SUITE;
   const created=previous?.created_stats||creationChoices();
   // Rank changes and one-way promotions occur once BETWEEN basho, not
   // at the end of each 3-bout block. Preserve the resulting world in draft.
   const division=previous&&isB12Campaign(previous)
    ?await api('/api/b12/campaign/advance',{roster:previous.division_roster,league:previous.division_league})
    :null;
   // Preserve the finished tournament until the new draft can be initialized.
   const names=await api('/api/b11/draft/catalogue',{});
   activeDraft={human,seed,world_seed:division?.roster?.seed??seed,
     division_roster:division?.roster||null,division_league:division?.league||null,
     created_stats:created,tournament_history,starting_cards:[...starting],picks:[],
     kimarite_names:names.kimarite_names};
   saveDraft();
   management=null;managementSave();
   await offerDraft();return;
  }
  const d=await api('/api/management/deal/'+encodeURIComponent(human)+'?seed='+seed);
  const roster=[...$('opponent').options].map(o=>o.value).filter(v=>v&&v!=='__random__'&&v!==human);
  for(let i=roster.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[roster[i],roster[j]]=[roster[j],roster[i]]}
  management={human,seed,opening_mode:'classic',created_stats:null,cards:d.cards,groups:Array.from({length:3},()=>[null,null,null]),opponents:roster.slice(0,15),round:0,results:[]};
  $('management-opening-mode').disabled=true;$('b11-creation').hidden=true;
  $('management-board').hidden=false;$('management-progress').hidden=true;$('management-next').hidden=true;
  managementBoard();managementSave();
  $('management-notice').textContent='Assign the nine cards across the first three bouts.';
 }catch(e){$('management-notice').textContent=e.message}
};
$('management-new').onclick=()=>{
 if(!management||management.results.length!==15||!completedRewards(management)||yearHistory(management).length>=5)return;
 try{
  management.next_starting_cards=earnedNextStartingCards(management);
  managementSave();
  if($('tournament-final').open)$('tournament-final').close();
  $('management-deal').hidden=false;
  $('management-deal').click();
 }catch(e){$('management-notice').textContent=e.message}
};
$('new-wrestler').onclick=()=>{
 if(!management||management.opening_mode!=='b11_live'||management.results.length!==15||yearHistory(management).length<5)return;
 $('new-wrestler-confirm').showModal();
};
$('cancel-new-wrestler').onclick=()=>$('new-wrestler-confirm').close();
$('confirm-new-wrestler').onclick=()=>{
 if(!management||management.results.length!==15||yearHistory(management).length<5)return;
 $('new-wrestler-confirm').close();
 if($('tournament-final').open)$('tournament-final').close();
 management=null;managementSave();
 activeDraft=null;saveDraft();
 showB12Banzuke(null);
 clearBoutSession();
 lastPresentedResult=null;
 $('management-opening-mode').value='b11_live';
 $('management-opening-mode').disabled=false;
 $('management-deck').disabled=false;
 $('b11-creation').hidden=false;
 $('wrestler-name').value='Your Rikishi';
 $('create-food').value='power';
 $('create-training').value='technique';
 creationChoices();
 for(const id of ['b11-draft','management-board','management-rewards','management-progress','management-next','management-summary','management-new','new-wrestler'])$(id).hidden=true;
 $('management-deal').hidden=false;
 $('management-notice').textContent='New year: create your wrestler, then draft your first 28 cards.';
 showYearStatus({tournament_history:[],results:[]});
 setGameLocation('heya');
};
$('management-start').onclick=()=>managementRound().catch(e=>$('management-notice').textContent=e.message);
$('management-next').onclick=async()=>{
 const m=management;
 if(!m||!game?.finished||activeTournamentBout()!==m.round||m.results.length!==m.round+1)return;
 if(m.round%3===2&&m.draft_picks){
  if(openBlockRewards())return;
 }
 if(!allBoutCardsAssigned(m)){$('management-notice').textContent='Complete the nine card assignments before the next bout. Finished bout cards are locked.';return;}
 if(m.round>=14){
  if(completedRewards(m))showTournamentFinal();
  return;
 }
 m.round++;managementSave();
 if(m.round%3===0){
  try{
   if(isB12Campaign(m)){
    const planned=await api('/api/b12/campaign/plan',
     {roster:m.division_roster,league:m.division_league});
    assignB12Block(m,planned);managementSave();
   }
   const data=m.draft_picks
    ?await api('/api/b11/draft/deal',{starting_cards:m.starting_cards,picks:m.draft_picks,draft_seed:m.draft_seed,duplicated_indices:m.duplicated_indices||[],seed:m.seed+Math.floor(m.round/3)})
    :await api('/api/management/deal/'+encodeURIComponent(m.human)+'?seed='+(m.seed+Math.floor(m.round/3)));
   m.cards=data.cards;m.groups=Array.from({length:3},()=>[null,null,null]);clearBoutSession();
   $('management-rewards').hidden=true;$('management-board').hidden=false;
   $('management-start').disabled=true;$('management-next').hidden=true;
   managementBoard();managementSave();
   $('management-notice').textContent='Round '+(Math.floor(m.round/3)+1)+': deck '+(m.draft_picks?28+(m.duplicated_indices||[]).length:'roster')+' cards. Assign nine to the next three opponents.';
   $('management-board').scrollIntoView({behavior:'smooth'});
  }catch(e){
   m.round--;managementSave();$('management-notice').textContent='Could not deal the next round: '+e.message;
  }
 }else managementRound().catch(e=>{
  m.round--;managementSave();$('management-notice').textContent='Could not start next bout: '+e.message;managementStatus();
 });
};

function renderBoutHud(g){
 const hud=$('bout-hud');
 if(!hud)return;
 // Keep the strip hidden during drafting, between bouts and initial Tachiai.
 if(!g||g.phase==='choose_tachiai'||!g.opponent||g.position===undefined||g.momentum===undefined){
  hud.hidden=true;
  return;
 }
 hud.hidden=false;
 $('hud-turn').textContent='Turn '+(g.turn??'—');
 $('hud-position').textContent='Position '+signedPosition(g.position)+(g.side_by_side?' · Side-by-Side (stored '+g.side_by_side.saved_distance+')':'');
 $('hud-momentum').textContent='Momentum '+(Number(g.momentum)>0?'+':'')+g.momentum;
 const own=g.human;
 $('hud-human').textContent='You: '+(own?.name||'Rikishi')+' · Power '+(own?.power??'—')+' · Grip '+(Array.isArray(own?.grip)?own.grip.join('/'):'—');
 const foe=g.opponent;
 $('hud-opponent').textContent=(foe.name||'Opponent')+' · Power '+(foe.power??'—')+' · Grip '+(Array.isArray(foe.grip)?foe.grip.join('/'):'—');
 const list=$('hud-effects');
 list.replaceChildren();
 const entries=[...(foe.temporary||[]).map(c=>({card:c,zone:'temporary'})),...(foe.kimarite||[]).map(c=>({card:c,zone:'kimarite'}))];
 if(!entries.length){list.append(node('span','hud-no-effects','Opponent effects: none active'));return;}
 list.append(node('span','hud-effects-label','Opponent active:'));
 for(const {card:c,zone} of entries){
  const effect=zoneEffect(c,zone);
  const label=displayCardName(c.name);
  const entry=btn((zone==='kimarite'?'Kimarite · ':'Temporary · ')+label+' — '+effect,
    ()=>inspect({...c,description:effect,zone_only:true,timing:zone==='kimarite'?'Winning condition':'Active Temporary effect'}),
    'hud-effect');
  entry.title=label+': '+effect;
  list.append(entry);
 }
}
function updateDohyoPosition(g){
 // Position is the shared ring track, from the human player's perspective.
 // +4/-4 are still inside the tawara; crossing past 4 causes ring-out.
 const ring=$('dohyo-ring'),label=$('ring-position-label'),warning=$('ring-edge-warning');
 const activeSideBySide=$('side-by-side-status');
 activeSideBySide.hidden=!g?.side_by_side;
 activeSideBySide.textContent=g?.side_by_side?sideBySideSummary(g):'';
 const ready=Number.isInteger(g?.position)&&g.position>=-4&&g.position<=4;
 const position=ready?g.position:0;
 ring.style.setProperty('--ring-shift',(position*6)+'%');
 ring.classList.toggle('dohyo-edge',ready&&Math.abs(position)===4);
 warning.hidden=!ready||Math.abs(position)!==4||!!g.finished;
 if(!ready){
  label.textContent='Position: neutral · awaiting Tachiai';
  ring.setAttribute('aria-label','Dohyō showing the neutral starting positions; awaiting Tachiai');
  return;
 }
 const state=g.side_by_side?'Side-by-Side · previous distance stored':position===0?'Neutral':position>0?'Advancing toward the opponent’s edge':'Being pushed toward your edge';
 label.textContent='Position '+(position>0?'+':'')+position+' · '+state;
 ring.setAttribute('aria-label','Dohyō at Position '+(position>0?'+':'')+position+' of ±4. '+state+'.');
}
function renderPendingTachiai(g){
 updateDohyoPosition(g);
 setGameLocation('dohyo');
 $('return-heya').hidden=true;
 renderBoutHud(g);
 game=g;picked=new Set();pendingPlay=null;rememberSession();if(management)managementStatus();
 $('round').textContent='CHOOSE TACHIAI';$('tracks').replaceChildren();
 $('score').replaceChildren(node('h2','','Your opening: '+g.human.name+' vs '+g.opponent.name));
 $('opening').replaceChildren(node('p','','Your opponent’s Tachiai cards remain hidden until you commit.'));
 $('choices').replaceChildren(node('h2','','Commit 0–3 cards to Tachiai'),node('p','','Committed cards contribute orbs and Tachiai effects; cards you keep will start in your Exchange hand.'));
 const strip=node('div','cards');
 const summary=node('p','zones','');
 const preview=node('div','tachiai-preview');
 preview.setAttribute('role','status');
 preview.setAttribute('aria-live','polite');
 const base=sessionSetup?.created_stats||b11PreviewBase(g.human.name);
 const refreshPreview=()=>{
  summary.textContent=picked.size+' committed · '+(3-picked.size)+' retained';
  const totals=b11CommittedTachiaiTotals(g.tachiai_choice.cards,picked,base);
  preview.replaceChildren(
   node('strong','','Your projected Tachiai · '+picked.size+' committed'),
   node('p','','Power '+totals[0]+' · Technique '+totals[1]+' · Spirit '+totals[2]),
   node('small','','Each total = base + 1 + committed card orbs. Power helps opening strength/defense; Technique influences Exchange priority and card access; Spirit can grant opening Push/Momentum. Opponent totals stay hidden until you confirm.')
  );
 };
 g.tachiai_choice.cards.forEach((c,i)=>{const b=card(c,()=>{if(picked.has(i)){picked.delete(i);b.classList.remove('selected')}else{picked.add(i);b.classList.add('selected')}refreshPreview()});const inspectButton=btn('Inspect '+displayCardName(c.name),()=>inspect(c),'choice-inspect');const wrap=node('div','choice-card-wrap');wrap.append(b,inspectButton);strip.append(wrap)});
 $('choices').append(strip);
 $('choices').append(summary,preview,btn('Confirm Tachiai commitment',()=>act({type:'commit_tachiai',indices:[...picked].sort()}),'confirm'));
 refreshPreview();
 $('hand').replaceChildren();$('history').replaceChildren();$('end').disabled=true;$('end').classList.remove('end-turn-no-plays','end-turn-win');$('end').textContent='End turn';$('notice').textContent='';
}
let lastPresentedResult=null;
function showBoutResult(g){
 const dialog=$('bout-result');
 if(!dialog||!g.finished||!g.winner||!sessionSetup||sessionSetup.opening_mode!=='b11_live')return;
 const key=[sessionSetup.seed,g.human.name,g.opponent.name,g.turn,g.winner,g.win_method].join('|');
 if(lastPresentedResult===key)return;
 lastPresentedResult=key;
 const won=g.winner==='A';
 setB12MatchdayStatus('idle','');
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
  for(const [name,value] of fields){const row=node('div','result-value');row.append(node('span','',name),node('strong','',value??'—'));values.append(row)}
 }
 dialog.classList.remove('result-revealed');
 dialog.showModal();
 requestAnimationFrame(()=>dialog.classList.add('result-revealed'));
}
$('result-review').onclick=()=>{$('bout-result').close();$('bout-history-details').open=true;$('bout-history-details').scrollIntoView({behavior:'smooth',block:'start'})};
let resolvingB12Matchday=false;
let matchdayPrefetch=null;
let matchdayPrefetchKey=null;
function setB12MatchdayStatus(status,message){
 const ready=status==='ready';
 for(const id of ['result-next','return-heya']){
  const button=$(id);
  button.classList.toggle('heya-standings-ready',ready);
  button.classList.toggle('heya-standings-loading',status==='loading');
  button.title=ready?'All 21 bouts are recorded — return to Heya now':message||'';
 }
 $('result-next').textContent=ready?'Return to Heya · Ready':
  status==='loading'?'Return to Heya · Updating standings…':
  status==='error'?'Return to Heya · Retry':'Return to Heya';
 $('result-standings-status').textContent=message||'';
}
function startB12MatchdayPrefetch(g){
 const m=management;
 if(!g?.finished||!isB12Campaign(m)||activeTournamentBout()!==m.round)return null;
 const key=[m.division_roster.seed,m.division_roster.completed_basho||0,m.round,
  sessionSetup?.seed].join('|');
 if(m.results.length===m.round+1){
  setB12MatchdayStatus('ready','All 21 match results recorded. Standings ready.');
  return Promise.resolve(true);
 }
 if(matchdayPrefetch&&matchdayPrefetchKey===key)return matchdayPrefetch;
 matchdayPrefetchKey=key;
 setB12MatchdayStatus('loading','Simulating the other 20 bouts while you review this result…');
 // The server does the actual gameplay; the result screen renders immediately.
 // Reusing this promise prevents a second batch if Return is clicked early.
 const pending=commitB12PlayerResult(m).then(()=>{
  if(matchdayPrefetchKey===key)
   setB12MatchdayStatus('ready','All 21 matches finished. Return to Heya is ready.');
  return true;
 }).catch(error=>{
  if(matchdayPrefetchKey===key){
   matchdayPrefetch=null;
   setB12MatchdayStatus('error','Standings update failed: '+error.message+
    '. Select Return to Heya to retry.');
  }
  throw error;
 });
 matchdayPrefetch=pending;
 // The result opens before the user clicks anything. Handle an async rejection
 // here as well, so a server failure does not create an unhandled rejection.
 void pending.catch(()=>{});
 return pending;
}
async function commitB12PlayerResult(m){
 const i=m.round;
 if(!isB12Campaign(m)||!game?.finished||activeTournamentBout()!==i)
  throw new Error('The finished player bout is not part of this ranked matchday.');
 if(m.results.length===i+1)return; // Saved result is authoritative after refresh.
 if(m.results.length!==i||m.division_league.day!==i)
  throw new Error('Matchday results are out of sync. No standings were changed.');
 const opponent=b12Opponent(m,i);
 if(!opponent||!m.division_league.pending_matches?.length)
  throw new Error('The B12 opponent or frozen matchday is missing.');
 const request={roster:m.division_roster,league:m.division_league,token};
 let resolved;
 try{
  resolved=await api('/api/b12/campaign/resolve',request);
 }catch(error){
  // A Render restart/idle expiry may discard only the live bout token.
  // Recreate it from the already saved player-action journal, then retry.
  if(/restored|finished player bout|expired|session/i.test(error.message)){
   const recovered=await recoverSession();
   if(!recovered.finished)throw new Error('Recovered bout is not finished yet.');
   request.token=token;
   resolved=await api('/api/b12/campaign/resolve',request);
  }else throw error;
 }
 const expectedWinner=game.winner==='A'?'player':opponent.id;
 if(resolved.league?.day!==i+1||resolved.ai_matches!==20||
    resolved.player_winner!==expectedWinner)
  throw new Error('Real AI matchday was not completed correctly.');
 // Update all 42 standings and the player bout record in a single save.
 // No synthetic AI wins or repeated AI simulations on subsequent Heya views.
 const record={human:m.human,opponent:m.opponents[i],opponent_style:opponent.style,
  opponent_name:opponent.name,opponent_rank:opponent.rank,opponent_id:opponent.id,
  won:game.winner==='A',turns:game.turn,finish:game.win_method||'Unknown',
  seed:sessionSetup?.seed??null,
  human_card_plays:[...(game.opening?.human?.committed||[]).map(c=>c.name),
    ...(game.human_card_plays||[])],
  assigned_cards:(m.groups[i%3]||[]).map(k=>m.cards.find(c=>c.deal_index===k))
   .filter(Boolean).map(c=>({...c})),
  duplication_resolved:false};
 m.division_league=resolved.league;
 m.results.push(record);
 updateTournamentLeaders(m);managementSave();
}
async function returnToHeya(){
 if(!game?.finished||resolvingB12Matchday)return; // No retreat from a live bout.
 resolvingB12Matchday=true;
 try{
  if(isB12Campaign(management)&&activeTournamentBout()===management.round&&
     management.results.length===management.round){
   $('result-next').disabled=true;$('return-heya').disabled=true;
   $('notice').textContent='Completing the remaining matches and standings…';
   await startB12MatchdayPrefetch(game);
  }
 }catch(error){
  $('notice').textContent='Could not complete the matchday: '+error.message+' — Retry Return to Heya.';
  $('management-notice').textContent=$('notice').textContent;
  return;
 }finally{
  resolvingB12Matchday=false;
  $('result-next').disabled=false;$('return-heya').disabled=false;
 }
 if($('bout-result').open)$('bout-result').close();
 $('return-heya').hidden=true;
 setGameLocation('heya');
 if(management){
  managementStatus();
  if(isB12Campaign(management))managementBoard();
  if(completedBlock(management)&&unresolvedRewards(management).length){
   openBlockRewards();return;
  }
  if(management?.results.length===15){showTournamentFinal();return}
  $('management-notice').textContent='Bout recorded. Review your plan in the Heya before the next match.';
 }
}
$('result-next').onclick=returnToHeya;
$('return-heya').onclick=returnToHeya;
function kimariteTurnCues(g){
 const canEnd=!!g?.can_end_turn&&!g.finished;
 const readyNames=canEnd?[...new Set(g.human?.ready_kimarite||[])]:[];
 return {
  noPlays:canEnd&&(g.human?.plays_remaining===0||(Array.isArray(g.legal_plays)&&g.legal_plays.length===0)),
  readyNames,
  winReady:readyNames.length>0,
 };
}
function render(g){if(g.phase==='choose_tachiai'){renderPendingTachiai(g);return}updateDohyoPosition(g);const alreadyInHeya=returnedToHeyaAfterBout(g);if(!alreadyInHeya)setGameLocation('dohyo');$('return-heya').hidden=!g.finished||alreadyInHeya;renderBoutHud(g);game=g;picked=new Set();pendingPlay=null;rememberSession();if(management){managementStatus();if(alreadyInHeya&&unresolvedRewards(management).length)openBlockRewards()}$('round').textContent='TURN '+g.turn+' · '+(g.finished?'BOUT OVER':g.phase==='select_cards'?'SELECT CARDS':'EXCHANGE');$('tracks').replaceChildren(node('span','track','POSITION '+g.position),node('span','track','MOMENTUM '+g.momentum));$('score').replaceChildren();const turnCues=kimariteTurnCues(g);const readyNames=new Set(turnCues.readyNames);
 for(const [title,s,own] of [['YOUR RIKISHI',g.human,true],['OPPONENT',g.opponent,false]]){const box=node('div','rikishi-info');box.append(node('div','eyebrow',title),node('h2','',s.name),node('p','', 'Power '+s.power+'  ·  Grip '+s.grip.join('/')+'  ·  '+(own?'Plays '+s.plays_remaining:'Hand '+s.hand_count)));const zones=node('p','zones');zones.append(node('b','','Kimarite: '),document.createTextNode(names(s.kimarite)),node('br'),node('b','','Temporary: '),document.createTextNode(names(s.temporary)));box.append(zones);const discard=btn('Discard pile: '+s.discard_count+' · View cards',()=>showDiscard(s,own?'Your rikishi':'Opponent'),'discard-button');box.append(discard);for(const zoneName of ['kimarite','temporary']){const zone=node('div','zone-list');zone.append(node('div','eyebrow',zoneName.toUpperCase()));for(const c of s[zoneName]){const item=node('div','zone-entry');const ready=own&&zoneName==='kimarite'&&readyNames.has(c.name);item.append(btn(displayCardName(c.name)+(ready?' · READY TO WIN':' · Inspect'),()=>inspect({...c,description:zoneEffect(c,zoneName),zone_only:true,timing:zoneName==='kimarite'?'Winning condition':'Active Temporary effect'}),'zone-card'+(ready?' kimarite-ready':'')));if(ready)item.append(node('span','kimarite-ready-cue','End turn to win'));item.append(node('p','temporary-detail',zoneEffect(c,zoneName)));zone.append(item)}box.append(zone)}$('score').append(box)}
 const opening=$('opening');opening.replaceChildren();if(g.opening){for(const [side,label] of [['human','Your opening'],['opponent','Opponent opening']]){const o=g.opening[side];opening.append(node('h2','',label));opening.append(node('p','', 'Tachiai totals — Power '+o.tachiai_orbs[0]+' · Technique '+o.tachiai_orbs[1]+' · Spirit '+o.tachiai_orbs[2]));for(const [key,title] of [['starting_kimarite','Starting Kimarite'],['prepared_tachiai','Prepared Tachiai'],['top_of_deck','Top of deck']]){if(o[key])opening.append(btn(title+': '+o[key].name+' · Inspect',()=>inspect(o[key]),'zone-card'))}}opening.append(node('p','zones','Your selected opening cards are shown here. Choose cards before a new bout; automatic mode remains available for comparison.'))}
 $('choices').replaceChildren();if(g.selection){$('choices').append(node('h2','','Choose '+g.selection.keep+' cards to keep'));const strip=node('div','cards');g.selection.options.forEach((c,i)=>{const b=card(c,()=>{if(picked.has(i)){picked.delete(i);b.classList.remove('selected')}else{picked.add(i);b.classList.add('selected')}confirm.disabled=picked.size!==g.selection.keep});b.firstChild.textContent=(i+1)+'. '+displayCardName(c.name);const info=btn('Inspect '+displayCardName(c.name),()=>inspect(c),'choice-inspect');info.type='button';const wrap=node('div','choice-card-wrap');wrap.append(b,info);strip.append(wrap)});$('choices').append(strip);const confirm=btn('Keep selected cards',()=>act({type:'choose_cards',indices:[...picked]}),'confirm');confirm.disabled=g.selection.keep!==0;$('choices').append(confirm)}
 $('hand').replaceChildren();const legal=new Set(g.legal_plays.map(a=>a.hand_index));g.human.hand.forEach((c,i)=>$('hand').append(card(c,()=>inspect(c,legal.has(i)?()=>play(i):null),true)));const history=$('history');history.replaceChildren();const events=g.events||[];if(!events.length)history.append(node('p','','No actions recorded yet.'));for(const event of events.slice().reverse())history.append(node('p',event.includes(' plays ')?'history-line':'history-event',event));const endButton=$('end');endButton.disabled=!g.can_end_turn;const canFinish=turnCues.winReady;endButton.classList.toggle('end-turn-no-plays',turnCues.noPlays);endButton.classList.toggle('end-turn-win',canFinish);endButton.textContent=canFinish?'End turn to win':'End turn';endButton.title=canFinish?'End turn to win with '+[...readyNames].join(', '):g.can_end_turn&&g.human.plays_remaining===0?'No Plays remaining — end your turn':'';$('notice').textContent=g.finished?('Winner: '+(g.winner==='A'?g.human.name:g.winner==='B'?g.opponent.name:'Undecided')+' · '+(g.win_method||g.stopped_reason||'')):'';
 if(g.finished&&!alreadyInHeya){
  showBoutResult(g);
  startB12MatchdayPrefetch(g);
 }
}
async function play(hand_index){pendingPlay={type:'play_card',hand_index,choices:{}};await act(pendingPlay)}
async function act(command){try{let r;try{r=await api('/api/session/'+token+'/action',command)}catch(e){if(e.data&&e.data.code==='session_expired'){await recoverSession();r=await api('/api/session/'+token+'/action',command)}else throw e}actionJournal.push(JSON.parse(JSON.stringify(command)));render(r.state)}catch(e){if(e.data&&e.data.choice_required){choicePrompt(e.data);return}if(e.data&&e.data.state){render(e.data.state);$('notice').textContent=e.message+(e.data.state.selection?' — Card selection is still pending above.':'');return}$('notice').textContent=e.message}}
function choicePrompt(detail){
 const panel=$('choices');panel.replaceChildren();
 const source=displayCardName(detail.card||'card');
 panel.append(node('h2','',source+' — '+(detail.choice_title||'Choose an option')));
 if(detail.choice_help)panel.append(node('p','choice-help',detail.choice_help));
 const strip=node('div','cards');
 for(const option of detail.options||[]){
  const value=option.value;
  const wrap=node('div','choice-card-wrap');
  const text=option.card?displayCardName(option.card.name):String(option.label);
  const choose=btn('',()=>{if(!pendingPlay)return;pendingPlay.choices[detail.choice_name]=value;act(pendingPlay)},'card choice-action-button');
  if(detail.choice_verb&&detail.choice_verb!=='Choose')choose.append(node('strong','choice-action-verb',detail.choice_verb));
  choose.append(node('span','choice-action-target',text));
  choose.setAttribute('aria-label',(detail.choice_verb&&detail.choice_verb!=='Choose'?detail.choice_verb+': ':'')+text);
  wrap.append(choose);
  if(option.card)wrap.append(btn('Inspect '+displayCardName(option.card.name),()=>inspect(option.card),'choice-inspect'));
  strip.append(wrap);
 }
 panel.append(strip);panel.scrollIntoView({behavior:'smooth',block:'center'});
}
async function loadOpening(){try{const d=await api('/api/opening/'+encodeURIComponent($('human').value));for(const [select,cards] of [['pick-kimarite',d.kimarite],['pick-prepared',d.ordinary],['pick-top',d.ordinary]]){$(select).replaceChildren();for(const c of cards){const o=node('option','',displayCardName(c.name));o.value=c.name;$(select).append(o)}}if(d.ordinary.length>1)$('pick-top').selectedIndex=1;const all=[...d.kimarite,...d.ordinary];for(let i=0;i<3;i++){const select=$('b11-card-'+i);select.replaceChildren();for(const c of all){const o=node('option','',displayCardName(c.name));o.value=c.name;select.append(o)}select.selectedIndex=i%all.length}}catch(e){$('notice').textContent=e.message}}
$('human').addEventListener('change',()=>{const random=$('human').value==='__random__';if(random){$('opening-mode').value='auto';$('opening-picks').hidden=true;$('b11-picks').hidden=true;$('opening-mode').querySelector('option[value="choose"]').disabled=true}else{$('opening-mode').querySelector('option[value="choose"]').disabled=false;$('b11-picks').hidden=$('opening-mode').value!=='b11_live';loadOpening()}});
$('opening-mode').addEventListener('change',()=>{$('opening-picks').hidden=$('opening-mode').value!=='choose'||$('human').value==='__random__';$('b11-picks').hidden=$('opening-mode').value!=='b11_live'||$('human').value==='__random__'});
$('seed-mode').addEventListener('change',()=>{$('seed-fixed-wrap').hidden=$('seed-mode').value!=='fixed'});
$('start').onclick=async()=>{try{const fixed=Number($('seed-fixed').value);if($('seed-mode').value==='fixed'&&(!Number.isSafeInteger(fixed)||fixed<0))throw new Error('Enter a non-negative whole-number seed.');const seed=$('seed-mode').value==='random'?Math.floor(Math.random()*2147483647):fixed;const roster=[...$('human').options].map(o=>o.value).filter(v=>v&&v!=='__random__');const choose=v=>v==='__random__'?roster[Math.floor(Math.random()*roster.length)]:v;const request={human:choose($('human').value),opponent:choose($('opponent').value),seed};if($('opening-mode').value==='b11_live'&&$('human').value!=='__random__'){request.opening_mode='b11_live';request.opening_cards=[0,1,2].map(i=>$('b11-card-'+i).value)}if($('opening-mode').value==='choose'&&$('human').value!=='__random__')request.opening={kimarite:$('pick-kimarite').value,prepared:$('pick-prepared').value,top:$('pick-top').value};const r=await api('/api/session',request);sessionSetup=request;actionJournal=[];token=r.token;$('human').value=request.human;$('opponent').value=request.opponent;$('seed-used').textContent='Bout seed: '+seed;render(r.state)}catch(e){$('notice').textContent=e.message}};
$('end').onclick=()=>{if(!game||!game.can_end_turn)return;const remaining=game.human.plays_remaining;if(remaining>0){$('end-confirm-message').textContent='You have '+remaining+' Play'+(remaining===1?'':'s')+' remaining. Continue playing?';$('end-confirm').showModal()}else act({type:'end_turn'})};
$('continue-playing').onclick=()=>$('end-confirm').close();
$('confirm-end-turn').onclick=()=>{$('end-confirm').close();if(game&&game.can_end_turn)act({type:'end_turn'})};
async function resume(){try{if(JSON.parse(gameSaveGet('kimarite_active_draft')||'null')){setGameLocation('heya');return}const saved=gameSaveGet('kimarite_session');if(!saved)return;sessionSetup=JSON.parse(gameSaveGet('kimarite_setup')||'null');actionJournal=JSON.parse(gameSaveGet('kimarite_actions')||'[]');token=saved;if(sessionSetup&&Number.isSafeInteger(sessionSetup.seed))$('seed-used').textContent='Bout seed: '+sessionSetup.seed;let state;try{state=await api('/api/session/'+saved)}catch(e){if(e.data&&e.data.code==='session_expired'){state=await recoverSession()}else throw e}render(state)}catch(e){$('notice').textContent='Unable to restore the previous bout: '+e.message}}
resume();
api('/api/roster').then(r=>{for(const name of r.roster){const o=node('option','',name);o.value=name;$('management-deck').append(o)}for(const id of ['human','opponent']){const random=node('option','','Random Wrestler');random.value='__random__';$(id).append(random);for(const name of r.roster){const o=node('option','',name);o.value=name;$(id).append(o)}}$('human').value='Arm Controller';$('opponent').value='The Technician';loadOpening();try{const saved=JSON.parse(gameSaveGet('kimarite_management')||'null');if(saved&&Array.isArray(saved.cards)&&saved.groups){management=saved;$('management-opening-mode').value=saved.opening_mode||'classic';$('management-opening-mode').disabled=true;$('b11-creation').hidden=true;$('management-deck').value=saved.human;$('wrestler-name').value=saved.human;$('management-board').hidden=false;managementBoard();managementStatus();if(gameSaveGet('kimarite_ui_phase')==='heya'&&unresolvedRewards(management).length)openBlockRewards()}else{const pending=JSON.parse(gameSaveGet('kimarite_active_draft')||'null');if(pending){activeDraft=pending;$('management-deck').value=pending.human;$('wrestler-name').value=pending.human;offerDraft().catch(e=>$('management-notice').textContent=e.message)}}}catch(e){} }).catch(e=>$('notice').textContent=e.message);
async function startRematchPlaytest(){
 setGameLocation('heya');
 const human='Playtest Rikishi',seed=117;
 const starting_cards=[...B11_STARTER_SUITE],picks=[];
 $('management-deal').disabled=true;
 $('management-notice').textContent='Preparing the seeded rematch…';
 try{
  const catalogue=await api('/api/b11/draft/catalogue',{});
  while(starting_cards.length+picks.length<28){
   const offer=await api('/api/b11/draft/offer',{starting_cards,picks,seed});
   picks.push(offer.choices[0].name);
  }
  activeDraft={human,seed,starting_cards,picks,kimarite_names:catalogue.kimarite_names,
   created_stats:{power:2,technique:1,spirit:0}};
  await finishDraft();
  const m=management;
  const won=rematchScenario==='win';
  m.tournament_history=[{tournament:1,wins:won?1:0,losses:won?0:1,results:[{opponent_id:m.b12_opponent_ids[0],
   opponent:m.opponents[0],won,rematch_top_card:won?null:'Oshi'}]}];
  m.groups=m.groups.map((group,index)=>m.cards.slice(index*3,index*3+3).map(card=>card.deal_index));
  if(rematchScenario==='review'){
   m.tournament_history=[];
   m.round=2;
   m.results=m.groups.map((group,index)=>({
    opponent:m.opponents[index],opponent_id:m.b12_opponent_ids[index],won:index===1,
    assigned_cards:group.map(id=>m.cards.find(card=>card.deal_index===id))
   }));
  }
  $('wrestler-name').value=human;
  $('management-opening-mode').disabled=true;
  $('b11-creation').hidden=true;
  managementSave();
  managementBoard();
  managementStatus();
  if(rematchScenario==='review'){
   openBlockRewards();
   $('management-notice').textContent='Round review playtest · two losses and one win.';
  }else{
   $('management-notice').textContent='Seeded playtest · your last bout against '+m.opponents[0]+
    (won?' was a win.':' was a loss. You saved Oshi for the rematch.')+' Start Bout 1 to test your opening.';
  }
 }catch(e){
  $('management-notice').textContent='Could not set up the rematch playtest: '+e.message;
 }finally{
  $('management-deal').disabled=false;
 }
}
if(playtestSavePrefix){
 gameSaveSet('kimarite_guide_seen','1');
 if(!gameSaveGet('kimarite_management'))startRematchPlaytest();
}
installGameGuide();
