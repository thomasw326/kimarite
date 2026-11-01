/* Regression checks for tournament record diversity on equal raw counts. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/client.js','utf8');
const start=source.indexOf('function calculateCardRecords(m){');
const end=source.indexOf('function completedRewards(m){',start);
assert(start!==-1&&end>start,'card records implementation missing');
const calculate=vm.runInNewContext(source.slice(start,end)+';calculateCardRecords');

function tournament(results,kimarite_names=['Oshidashi','Yorikiri']){
 return {results,kimarite_names};
}
function bout(won,...cards){return {won,human_card_plays:cards}}

// Oshidashi: 5 plays, 4 winning bouts. Yorikiri: 4 plays, 4 winning bouts.
// Both tie on raw winning count; prefer Yorikiri to avoid repeating Oshidashi.
const sample=tournament([
 bout(true,'Oshidashi','Yorikiri'),
 bout(true,'Oshidashi','Yorikiri'),
 bout(true,'Oshidashi','Yorikiri'),
 bout(true,'Oshidashi','Yorikiri'),
 bout(false,'Oshidashi')
]);
const s=calculate(sample);
assert.equal(s.most_played_card.name,'Oshidashi');
assert.equal(s.most_played_card.count,5);
assert.equal(s.most_winning_card.name,'Yorikiri');
assert.equal(s.most_winning_card.count,4);

// Four tied cards should yield four distinct records when possible.
// Two of the tied cards are Kimarite.
const four=tournament(Array.from({length:4},()=>bout(true,'Oshidashi','Yorikiri','Oshi','Tsuki')));
const f=calculate(four);
assert.equal(new Set(Object.values(f).map(v=>v.name)).size,4);
assert(Object.values(f).every(v=>v.count===4));
assert(['Oshidashi','Yorikiri'].includes(f.most_played_kimarite.name));
assert(['Oshidashi','Yorikiri'].includes(f.most_winning_kimarite.name));

// A sole leader stays the leader even if this necessarily repeats the name.
const solo=calculate(tournament([bout(true,'Oshidashi'),bout(true,'Oshidashi'),bout(false,'Oshidashi')]));
assert(Object.values(solo).every(v=>v.name==='Oshidashi'));
assert.equal(solo.most_played_card.count,3);
assert.equal(solo.most_winning_card.count,2);

// Winning counts credit a card only once per winning bout; losing uses do not count.
const counted=calculate(tournament([bout(true,'Oshi','Oshi'),bout(false,'Oshi','Oshi')],[]));
assert.equal(counted.most_played_card.count,4);
assert.equal(counted.most_winning_card.count,1);
assert.equal(counted.most_played_kimarite,null);
assert.equal(counted.most_winning_kimarite,null);
console.log('B11 card records: tied-leader diversity, sole leaders and raw counts passed.');
