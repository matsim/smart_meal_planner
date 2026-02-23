import urllib.request, json, zipfile, io, xml.etree.ElementTree as ET, re

url = 'https://www.data.gouv.fr/api/1/datasets/table-de-composition-nutritionnelle-des-aliments-ciqual/'
d = json.loads(urllib.request.urlopen(url).read())
z_url = next(r['url'] for r in d['resources'] if 'XML' in r['title'] or 'xml' in r['format'].lower())
r = urllib.request.urlopen(z_url)
z = zipfile.ZipFile(io.BytesIO(r.read()))

def read_xml(filename):
    txt = z.open(filename).read().decode('windows-1252', errors='replace')
    txt = re.sub(r'<(?!\/?(?:[a-zA-Z_?]+)(?:>|\s))', '&lt;', txt)
    txt = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', txt)
    txt = txt.replace('encoding="windows-1252"', 'encoding="utf-8"')
    return ET.fromstring(txt.encode('utf-8'))

alim_root = read_xml('alim_2020_07_07.xml')
const_root = read_xml('const_2020_07_07.xml')
compo_root = read_xml('compo_2020_07_07.xml')

print("ALIM root:", alim_root.tag, [child.tag for child in alim_root[:2]])
print("ALIM sample node:", ET.tostring(alim_root[0]).decode('utf-8'))
print("CONST sample node:", ET.tostring(const_root[0]).decode('utf-8'))
print("COMPO sample node:", ET.tostring(compo_root[0]).decode('utf-8'))
