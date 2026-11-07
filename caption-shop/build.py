"""Build the isolated product ZIP and local review. Uses only Python's standard library."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
OUT.mkdir(exist_ok=True)
CSS = (ROOT / 'styles.css').read_text(encoding='utf-8')
CORE = (ROOT / 'core.js').read_text(encoding='utf-8')
APP = (ROOT / 'app.js').read_text(encoding='utf-8')
for template, name in [('tool.template.html', 'Caption-Cleanup-Kit.html'),
                       ('guide.template.html', 'Quick-Start.html'),
                       ('listing.template.html', 'index.html'),
                       ('cover.template.html', 'cover.html'),
                       ('thumbnail.template.html', 'thumbnail.html')]:
    html = (ROOT / template).read_text(encoding='utf-8').replace('__CSS__', CSS).replace('__CORE__', CORE).replace('__APP__', APP)
    icon = '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 48 48%22%3E%3Crect width=%2248%22 height=%2248%22 rx=%2210%22 fill=%22%23245c3b%22/%3E%3Cpath d=%22M12 16h24v16H12z%22 fill=%22none%22 stroke=%22%23d8f49b%22 stroke-width=%223%22/%3E%3Cpath d=%22M17 22h14M17 27h9%22 stroke=%22%23d8f49b%22 stroke-width=%222%22/%3E%3C/svg%3E">'
    html = html.replace('</head>', icon + '</head>')
    if name == 'Caption-Cleanup-Kit.html':
        html = html.replace('Caption Cleanup Kit 1.0 · Open this HTML file', '<a href="Quick-Start.html">Quick-start guide</a> · Caption Cleanup Kit 1.0 · Open this HTML file')
    (OUT / name).write_text(html, encoding='utf-8')
sample = '1\n00:00:00,500 --> 00:00:03,500\nWelcome to your next creative project.\n\n2\n00:00:04,000 --> 00:00:07,000\nGood captions make every word easier to follow.\n'
(OUT / 'sample.srt').write_text(sample, encoding='utf-8')
(OUT / 'sample.vtt').write_text('WEBVTT\n\n' + sample.replace('1\n', '', 1).replace('\n\n2\n', '\n\n').replace(',', '.'), encoding='utf-8')
names = ['Caption-Cleanup-Kit.html', 'Quick-Start.html', 'sample.srt', 'sample.vtt']
archive = OUT / 'Caption-Cleanup-Kit-v1.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for name in names:
        bundle.write(OUT / name, name)
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert bundle.namelist() == names
manifest = {'product': 'Caption Cleanup Kit', 'version': '1.0', 'built_date': '2026-09-30',
            'archive': archive.name, 'bytes': archive.stat().st_size,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'files': names}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(manifest))
