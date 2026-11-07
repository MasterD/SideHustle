/* Caption Cleanup Kit 1.0. Original implementation; no external dependencies. */
(function (root) {
  'use strict';
  const MAX_BYTES = 2 * 1024 * 1024;
  function timestamp(value) {
    const m = value.match(/^(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})$/);
    if (!m || +m[2] > 59 || +m[3] > 59) throw new Error('Invalid timestamp: ' + value);
    return ((+(m[1] || 0) * 3600 + +m[2] * 60 + +m[3]) * 1000) + +m[4];
  }
  function clock(ms, vtt = false) {
    if (!Number.isSafeInteger(ms) || ms < 0) throw new Error('Invalid output time.');
    const pad = (n, size = 2) => String(n).padStart(size, '0');
    return pad(Math.floor(ms / 3600000)) + ':' + pad(Math.floor(ms / 60000) % 60) + ':' +
      pad(Math.floor(ms / 1000) % 60) + (vtt ? '.' : ',') + pad(ms % 1000, 3);
  }
  function parse(input) {
    if (new TextEncoder().encode(input).length > MAX_BYTES) throw new Error('File exceeds the 2 MB limit.');
    const text = input.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
    if (!text) throw new Error('The file is empty.');
    const isVtt = /^WEBVTT(?:[ \t]|\n|$)/.test(text);
    const blocks = text.split(/\n[ \t]*\n/);
    const cues = [], warnings = [];
    for (let b = 0; b < blocks.length; b++) {
      const lines = blocks[b].split('\n');
      if (b === 0 && isVtt && /^WEBVTT/.test(lines[0])) {
        lines.shift();
        if (!lines.some(line => line.includes('-->'))) continue;
      }
      if (isVtt && /^(NOTE(?:[ \t]|$)|STYLE$|REGION$)/.test(lines[0])) {
        warnings.push('A WebVTT note, style or region block was omitted.');
        continue;
      }
      let timeIndex = lines[0]?.includes('-->') ? 0 : 1;
      const timing = lines[timeIndex]?.match(/^\s*(\S+)\s+-->\s+(\S+)(.*)$/);
      if (!timing) throw new Error('Block ' + (b + 1) + ' has no valid timing line.');
      if (timeIndex === 1 && !isVtt && !/^\d+$/.test(lines[0].trim())) {
        throw new Error('Block ' + (b + 1) + ' has an invalid SRT cue number.');
      }
      const start = timestamp(timing[1]), end = timestamp(timing[2]);
      if (end <= start) throw new Error('Block ' + (b + 1) + ' must end after it starts.');
      if (timing[3].trim()) warnings.push('Position settings on cue ' + (cues.length + 1) + ' were omitted.');
      const body = lines.slice(timeIndex + 1).join('\n').trim();
      if (!body) throw new Error('Block ' + (b + 1) + ' has no caption text.');
      cues.push({start, end, text: body});
    }
    if (!cues.length) throw new Error('No subtitle cues were found.');
    if (cues.length > 20000) throw new Error('The file exceeds the 20,000 cue limit.');
    return {cues, warnings: [...new Set(warnings)], source: isVtt ? 'vtt' : 'srt'};
  }
  function plain(value) {
    const entities = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' '};
    return value.replace(/<[^>]*>/g, '').replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi,
      (whole, key) => {
        if (key[0] !== '#') return entities[key.toLowerCase()];
        const n = key[1].toLowerCase() === 'x' ? parseInt(key.slice(2), 16) : +key.slice(1);
        return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : whole;
      });
  }
  function wrap(value, width) {
    if (!width) return value;
    const lines = [], words = value.replace(/\s+/g, ' ').trim().split(' ');
    let line = '';
    for (const word of words) {
      if (line && [...line + ' ' + word].length > width) { lines.push(line); line = word; }
      else line += (line ? ' ' : '') + word;
    }
    if (line) lines.push(line);
    return lines.join('\n');
  }
  function transform(cues, options = {}) {
    const offset = options.offset ?? 0, width = options.width ?? 0;
    if (!Number.isFinite(offset) || Math.abs(offset) > 86400) throw new Error('Offset must be within 24 hours.');
    if (!Number.isInteger(width) || (width !== 0 && (width < 10 || width > 100))) throw new Error('Line width must be 10–100, or 0 to preserve lines.');
    const shift = Math.round(offset * 1000);
    return cues.map((cue, index) => {
      const start = cue.start + shift, end = cue.end + shift;
      if (start < 0) throw new Error('Offset moves cue ' + (index + 1) + ' before 00:00. Reduce the negative offset.');
      let text = options.strip ? plain(cue.text) : cue.text;
      if (options.tidy) text = text.split('\n').map(line => line.replace(/[ \t]+/g, ' ').trim()).join('\n');
      text = wrap(text, width);
      return {start, end, text};
    });
  }
  function csvCell(value) {
    let text = String(value);
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function render(cues, format) {
    if (format === 'srt' || format === 'vtt') {
      return (format === 'vtt' ? 'WEBVTT\n\n' : '') + cues.map((c, i) =>
        (format === 'srt' ? (i + 1) + '\n' : '') + clock(c.start, format === 'vtt') + ' --> ' +
        clock(c.end, format === 'vtt') + '\n' + c.text).join('\n\n') + '\n';
    }
    if (format === 'txt') return cues.map(c => plain(c.text).replace(/\s+/g, ' ').trim()).join('\n') + '\n';
    if (format === 'timed') return cues.map(c => '[' + clock(c.start, true).slice(0, -4) + '] ' + plain(c.text).replace(/\s+/g, ' ').trim()).join('\n') + '\n';
    if (format === 'csv') return '\uFEFFcue,start,end,text\r\n' + cues.map((c, i) =>
      [i + 1, clock(c.start, true), clock(c.end, true), plain(c.text)].map(csvCell).join(',')).join('\r\n') + '\r\n';
    throw new Error('Unknown output format.');
  }
  function inspect(cues) {
    const issues = [];
    for (let i = 0; i < cues.length; i++) {
      const c = cues[i], text = plain(c.text), chars = [...text.replace(/\s/g, '')].length;
      if (i && c.start < cues[i - 1].start) issues.push('Cue ' + (i + 1) + ': starts out of sequence.');
      if (i && c.start < cues[i - 1].end) issues.push('Cue ' + (i + 1) + ': overlaps the previous cue.');
      if (chars / ((c.end - c.start) / 1000) > 20) issues.push('Cue ' + (i + 1) + ': more than 20 characters per second.');
      if (text.split('\n').length > 2) issues.push('Cue ' + (i + 1) + ': more than two lines.');
      if (text.split('\n').some(line => [...line].length > 42)) issues.push('Cue ' + (i + 1) + ': a line exceeds 42 characters.');
    }
    return issues;
  }
  function safeName(value) { return value.replace(/\.[^.]*$/, '').replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80) || 'captions'; }
  // Standard ZIP store records, UTF-8 names; browsers need no zip library or network.
  function zip(entries) {
    const encoder = new TextEncoder(), chunks = [], central = [], names = new Set();
    let offset = 0, centralSize = 0;
    const record = size => { const bytes = new Uint8Array(size); return {bytes, view: new DataView(bytes.buffer)}; };
    const crc = bytes => { let n = -1; for (const byte of bytes) {n ^= byte; for (let k = 0; k < 8; k++) n = (n >>> 1) ^ (0xedb88320 & -(n & 1));} return (n ^ -1) >>> 0; };
    if (entries.length > 65535) throw new Error('Too many ZIP entries.');
    for (const entry of entries) {
      if (names.has(entry.name) || /(^\/|\\|(?:^|\/)\.\.(?:\/|$))/.test(entry.name)) throw new Error('Unsafe or duplicate archive filename.');
      names.add(entry.name);
      const name = encoder.encode(entry.name), data = encoder.encode(entry.text), checksum = crc(data);
      if (name.length > 65535 || offset + data.length > 0xffffffff) throw new Error('Archive too large.');
      const local = record(30 + name.length), l = local.view;
      l.setUint32(0, 0x04034b50, true); l.setUint16(4, 20, true); l.setUint16(6, 0x0800, true);
      l.setUint16(12, 0x0021, true); l.setUint32(14, checksum, true); l.setUint32(18, data.length, true);
      l.setUint32(22, data.length, true); l.setUint16(26, name.length, true); local.bytes.set(name, 30);
      chunks.push(local.bytes, data);
      const header = record(46 + name.length), v = header.view;
      v.setUint32(0, 0x02014b50, true); v.setUint16(4, 20, true); v.setUint16(6, 20, true);
      v.setUint16(8, 0x0800, true); v.setUint16(14, 0x0021, true); v.setUint32(16, checksum, true);
      v.setUint32(20, data.length, true); v.setUint32(24, data.length, true); v.setUint16(28, name.length, true);
      v.setUint32(42, offset, true); header.bytes.set(name, 46); central.push(header.bytes);
      offset += local.bytes.length + data.length; centralSize += header.bytes.length;
    }
    const end = record(22), e = end.view;
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, entries.length, true); e.setUint16(10, entries.length, true);
    e.setUint32(12, centralSize, true); e.setUint32(16, offset, true);
    const result = new Uint8Array(offset + centralSize + 22);
    let pos = 0; for (const chunk of [...chunks, ...central, end.bytes]) {result.set(chunk, pos); pos += chunk.length;}
    return result;
  }
  const api = {parse, timestamp, clock, transform, render, inspect, plain, wrap, zip, safeName, MAX_BYTES};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CaptionKit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
