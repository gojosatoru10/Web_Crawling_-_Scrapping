import requests
from urllib.parse import urljoin

def is_allowed(url, user_agent='*'):
    base_url = url.split('/')[0] + '//' + url.split('/')[2]
    robots_url = urljoin(base_url, '/robots.txt')
    resp = requests.get(robots_url)
    if resp.status_code != 200:
        return True  # If no robots.txt, allow by default
    lines = resp.text.splitlines()
    allowed = True
    for line in lines:
        if line.lower().startswith('user-agent') and user_agent in line:
            allowed = True
        if allowed and line.lower().startswith('disallow'):
            path = line.split(':', 1)[1].strip()
            if url[len(base_url):].startswith(path):
                return False
    return True
