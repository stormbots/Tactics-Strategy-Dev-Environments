"""Current introduction uses an evergreen official entry point; history is immutable."""
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO='stormbots/Tactics-Strategy-Dev-Environments'
LATEST=f'https://github.com/{REPO}/releases/latest'
ASSETS={'Skyview-Dev-Setup-Windows-x64.exe','Skyview-Dev-Setup-LinuxMint-amd64.deb','sde-update.json','sde-update.json.minisig','SHA256SUMS.txt'}
def check_intro(text):
    intro=text.split('## Stable fallback and advanced manual installation')[0]
    if intro.count(LATEST)<2 or re.search(r'(?:Stable release|Current stable/latest is)\s*\*?\*?v?\d+\.\d+\.\d+',intro,re.I):
        raise ValueError('Current introduction must use evergreen official stable links, without a hardcoded current release version')
    if re.search(r'\[Download your installer[^\]]*\]\([^)]*/releases/tag/',intro,re.I):
        raise ValueError('Primary installer link must track latest stable')
    if not {'Skyview-Dev-Setup-Windows-x64.exe','Skyview-Dev-Setup-LinuxMint-amd64.deb'}.issubset(set(re.findall(r'Skyview-Dev-Setup-[A-Za-z0-9.-]+',intro))):
        raise ValueError('Both supported installer names must be documented')
def check_release(release):
    tag=release.get('tag_name','')
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',tag) or release.get('draft') is not False or release.get('prerelease') is not False:
        raise ValueError('The latest entry point must resolve to a nondraft stable canonical release')
    assets=release.get('assets',[])
    if len(assets)!=5 or {a['name'] for a in assets}!=ASSETS:
        raise ValueError('Stable release needs the complete five-asset distribution')
    for a in assets:
        if a.get('size',0)<=0 or a.get('browser_download_url')!=f'https://github.com/{REPO}/releases/download/{tag}/{a["name"]}':
            raise ValueError('Stable assets must be nonempty official downloads')
if __name__=='__main__':
    check_intro((ROOT/'README.md').read_text())
    if len(sys.argv)>1: check_release(json.loads(Path(sys.argv[1]).read_text()))
