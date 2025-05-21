import xml.etree.ElementTree as ET

def get_genre_pages_from_local_xml(xml_path='output/sitemap.550.xml'):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = [url.text for url in root.findall('.//ns:url/ns:loc', ns)]
    return urls
