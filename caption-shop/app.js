'use strict';
(() => {
  const $ = id => document.getElementById(id), C = CaptionKit;
  const sample = '1\n00:00:00,500 --> 00:00:03,500\nWelcome to your next creative project.\n\n2\n00:00:04,000 --> 00:00:07,000\n<i>Good captions make every word easier to follow.</i>\n\n3\n00:00:07,500 --> 00:00:11,500\nKeep the story moving, one clear line at a time.\n';
  let files = [], current = [], currentText = '', importVersion = 0;
  function status(message, error = false) { $('status').textContent = message; $('status').className = error ? 'status error' : 'status'; }
  function save(data, name, type) {
    const url = URL.createObjectURL(new Blob([data], {type})), link = document.createElement('a');
    link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  function clearOutput() { current = []; currentText = ''; $('output').value = ''; $('download').disabled = true; $('batch').disabled = true; $('stats').textContent = 'Ready when you are'; $('issues').replaceChildren(); }
  function invalidate() { clearOutput(); status('Settings changed. Run cleanup to refresh the output.'); }
  function options() { return {offset: Number($('offset').value), width: Number($('width').value), strip: $('strip').checked, tidy: $('tidy').checked}; }
  function convert(text) {
    const parsed = C.parse(text), cues = C.transform(parsed.cues, options());
    return {cues, text: C.render(cues, $('format').value), warnings: parsed.warnings.concat(C.inspect(cues))};
  }
  function extension() { return $('format').value === 'timed' ? 'txt' : $('format').value; }
  function process() {
    clearOutput();
    try {
      const result = convert($('input').value); current = result.cues; currentText = result.text;
      $('output').value = result.text; $('download').disabled = false; $('batch').disabled = files.length < 2;
      const words = current.reduce((sum, c) => sum + C.plain(c.text).trim().split(/\s+/).length, 0);
      $('stats').textContent = current.length + ' cues · ' + words + ' words · ends at ' + C.clock(Math.max(...current.map(c => c.end)), true);
      for (const issue of result.warnings.slice(0, 100)) { const li = document.createElement('li'); li.textContent = issue; $('issues').append(li); }
      if (result.warnings.length > 100) {const li = document.createElement('li'); li.textContent = (result.warnings.length - 100) + ' more checks; use the CSV export to review all cues.'; $('issues').append(li);}
      status(result.warnings.length ? 'Converted. Review the checks below before publishing.' : 'Converted. Your download is ready.');
    } catch (error) { status(error.message, true); }
  }
  $('sample').addEventListener('click', () => {importVersion++; files = []; $('files').value = ''; $('input').value = sample; $('source').textContent = 'Sample captions'; process();});
  $('input').addEventListener('input', () => {importVersion++; files = []; $('files').value = ''; $('source').textContent = 'Pasted captions'; invalidate();});
  for (const id of ['offset', 'width', 'strip', 'tidy', 'format']) $(id).addEventListener('change', invalidate);
  $('files').addEventListener('change', async () => {
    const version = ++importVersion, selected = [...$('files').files]; files = []; clearOutput();
    try {
      if (!selected.length) { $('source').textContent = 'Pasted captions'; return; }
      if (selected.length > 100) throw new Error('Choose at most 100 files at a time.');
      if (selected.some(file => !/\.(srt|vtt)$/i.test(file.name))) throw new Error('Choose SRT or VTT files only.');
      if (selected.some(file => file.size > C.MAX_BYTES)) throw new Error('Each file must be 2 MB or smaller.');
      if (selected.reduce((sum, file) => sum + file.size, 0) > 20 * 1024 * 1024) throw new Error('Choose at most 20 MB in one batch.');
      status('Reading files on your device…');
      const loaded = [];
      for (const file of selected) loaded.push({name: file.name, text: await file.text()});
      if (version !== importVersion) return;
      files = loaded; $('input').value = files[0].text;
      $('source').textContent = files.length === 1 ? files[0].name : files.length + ' files selected · previewing ' + files[0].name;
      process();
    } catch (error) { if (version === importVersion) { files = []; status(error.message, true); } }
  });
  $('run').addEventListener('click', process);
  $('download').addEventListener('click', () => {if (current.length) save(currentText, C.safeName(files[0]?.name || 'captions') + '-clean.' + extension(), 'text/plain;charset=utf-8');});
  $('batch').addEventListener('click', () => {
    try {
      if (files.length < 2) return;
      const entries = [], errors = [], names = new Set();
      for (const file of files) {
        try {
          const result = convert(file.text); const stem = C.safeName(file.name); let name = stem + '-clean.' + extension(), n = 2;
          while (names.has(name)) name = stem + '-clean-' + n++ + '.' + extension();
          names.add(name); entries.push({name, text: result.text});
          if (result.warnings.length) errors.push(file.name + ':\n' + result.warnings.join('\n') + '\n');
        } catch (error) { throw new Error(file.name + ': ' + error.message + ' No batch was exported.'); }
      }
      entries.push({name: 'REVIEW.txt', text: errors.length ? errors.join('\n') : 'All files converted. Review captions against the original media before publishing.\n'});
      save(C.zip(entries), 'clean-captions.zip', 'application/zip'); status('Batch exported. The ZIP includes a review report.');
    } catch (error) { status(error.message, true); }
  });
  $('reset').addEventListener('click', () => { importVersion++; files = []; $('files').value = ''; $('input').value = ''; $('source').textContent = 'No file selected'; clearOutput(); status('Files cleared from this page.'); });
  $('input').value = sample; process();
})();
