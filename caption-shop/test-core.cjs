'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const C = require('./core.js');
let passed = 0;
function test(name, fn) { fn(); passed++; console.log('PASS ' + name); }
const sample = '\uFEFF1\r\n00:00:00,500 --> 00:00:03,500\r\n<i>Hello &amp; welcome.</i>\r\n\r\n2\r\n00:00:04,000 --> 00:00:05,000\r\nSecond line.\r\n';
test('SRT accepts BOM and Windows line endings without dropping cues', () => {
  const p = C.parse(sample); assert.equal(p.cues.length, 2); assert.equal(p.cues[0].start, 500); assert.equal(p.cues[1].end, 5000);
});
test('SRT → VTT → SRT retains times and text', () => {
  const a = C.parse(sample).cues, b = C.parse(C.render(a, 'vtt')).cues;
  assert.deepEqual(b, a); assert.deepEqual(C.parse(C.render(b, 'srt')).cues, a);
});
test('VTT identifiers, settings and metadata are handled explicitly', () => {
  const p = C.parse('WEBVTT\nKind: captions\n\nNOTE a comment\nignored\n\nvoice-1\n00:00.100 --> 00:02.100 align:start\n<v Alex>Hello</v>');
  assert.equal(p.cues.length, 1); assert.equal(p.warnings.length, 2); assert.equal(C.render(p.cues, 'txt'), 'Hello\n');
});
test('Malformed blocks and invalid durations cannot produce partial results', () => {
  for (const text of ['1\n00:61:00,000 --> 00:62:00,000\ntext', '1\n00:00:02,000 --> 00:00:01,000\ntext', sample + '\n\nbroken block', 'WEBVTT\n\nNOTE only metadata']) assert.throws(() => C.parse(text));
});
test('Positive offsets preserve durations and negative times are rejected', () => {
  const a = C.parse(sample).cues, b = C.transform(a, {offset: 1.25});
  assert.equal(b[0].start, 1750); assert.equal(b[0].end - b[0].start, 3000); assert.throws(() => C.transform(a, {offset: -1})); assert.throws(() => C.transform(a, {offset: NaN}));
});
test('Transcript strips markup and safely decodes entities', () => {
  assert.equal(C.render(C.parse(sample).cues, 'txt'), 'Hello & welcome.\nSecond line.\n');
  assert.equal(C.plain('&#x1f600; &#128512; &#99999999;'), '😀 😀 &#99999999;');
});
test('Line wrapping preserves words and Unicode codepoints', () => {
  assert.equal(C.wrap('one two three four', 10), 'one two\nthree four'); assert.equal(C.wrap('😀😀 😀😀', 5), '😀😀 😀😀');
  assert.throws(() => C.transform(C.parse(sample).cues, {width: 2}));
});
test('CSV quotes embedded newlines and neutralizes formula prefixes', () => {
  const csv = C.render([{start:0,end:1000,text:'=SUM(1,2)\n"quoted"'}], 'csv');
  assert.ok(csv.includes('"\'=SUM(1,2)\n""quoted"""')); assert.ok(csv.startsWith('\uFEFFcue,start,end,text'));
});
test('Review flags overlapping cues and reading speed', () => {
  const issues = C.inspect([{start:0,end:1000,text:'a'.repeat(45)},{start:500,end:1500,text:'word'}]);
  assert.ok(issues.some(x => x.includes('overlaps'))); assert.ok(issues.some(x => x.includes('per second')));
});
test('ZIP names reject traversal and duplicate members', () => {
  assert.throws(() => C.zip([{name:'../bad.txt',text:'x'}])); assert.throws(() => C.zip([{name:'a.txt',text:'1'},{name:'a.txt',text:'2'}]));
});
test('ZIP exports UTF-8 bytes for independent validation', () => {
  fs.mkdirSync(path.join(__dirname, 'dist'), {recursive:true});
  fs.writeFileSync(path.join(__dirname, 'dist', 'test-batch.zip'), C.zip([{name:'captions.srt',text:C.render(C.parse(sample).cues,'srt')},{name:'café.txt',text:'Hello 😀\n'}]));
});
console.log(passed + ' tests passed.');
