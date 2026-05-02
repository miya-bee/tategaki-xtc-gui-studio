from __future__ import annotations

import zipfile
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures'


def fixture_path(*parts: str) -> Path:
    return FIXTURE_ROOT.joinpath(*parts)


def build_sample_epub(output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chapter = fixture_path('epub', 'chapter1.xhtml').read_text(encoding='utf-8')
    css = fixture_path('epub', 'styles', 'main.css').read_text(encoding='utf-8')
    image_bytes = fixture_path('epub', 'images', 'scene.png').read_bytes()

    container_xml = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

    content_opf = '''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Regression Sample</dc:title>
    <dc:language>ja</dc:language>
    <dc:identifier id="BookId">regression-sample-epub</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="style" href="styles/main.css" media-type="text/css"/>
    <item id="scene" href="images/scene.png" media-type="image/png"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>
'''

    toc_ncx = '''<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="regression-sample-epub"/>
  </head>
  <docTitle><text>Regression Sample</text></docTitle>
  <navMap>
    <navPoint id="navPoint-1" playOrder="1">
      <navLabel><text>第一章</text></navLabel>
      <content src="chapter1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
'''

    with zipfile.ZipFile(output_path, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('OEBPS/content.opf', content_opf)
        zf.writestr('OEBPS/toc.ncx', toc_ncx)
        zf.writestr('OEBPS/chapter1.xhtml', chapter)
        zf.writestr('OEBPS/styles/main.css', css)
        zf.writestr('OEBPS/images/scene.png', image_bytes)
    return output_path
