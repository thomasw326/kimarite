/* B11 uses audited sheet translations only for visible names, never engine keys. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/client.js','utf8');
const start=source.indexOf('const CARD_ENGLISH_NAMES=');
const end=source.indexOf('const $=id=>',start);
assert(start>=0&&end>start);
const english=vm.runInNewContext(source.slice(start,end)+';displayCardName');
assert.equal(english('Yorikiri'),'Force Out (Yorikiri)');
assert.equal(english('Oshidashi'),'Push Out (Oshidashi)');
assert.equal(english('Yoritaoshi'),'Crush Out (Yoritaoshi)');
assert.equal(english('Hikiotoshi'),'Pull Down (Hikiotoshi)');
assert.equal(english('Utchari'),'Edge Pivot Throw (Utchari)');
assert.equal(english('Tsukitaoshi'),'Thrust Down (Tsukitaoshi)');
assert.equal(english('Tsukiotoshi'),'Thrust Down (Tsukiotoshi)');
assert.equal(english('Nodowa'),'Throat Grab (Nodowa)');
assert.equal(english('Tsuppari'),'Repeated Thrusts (Tsuppari)');
assert.equal(english('Tsuriotoshi'),'Tsuriotoshi'); // No approved translation in the audited tabs.
assert(source.includes('o.value=c.name'),'native select values remain canonical');
assert(source.includes('d.picks.push(c.name)'),'draft choices remain canonical');
assert(source.includes("const b=card(c,()=>{if(picked.has(i))"),'kept-card choices retain original card identity');
console.log('Audited B11 English display names and canonical engine keys passed.');
