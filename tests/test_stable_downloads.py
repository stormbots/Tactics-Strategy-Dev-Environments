import unittest
from stable_downloads import ROOT,ASSETS,REPO,check_intro,check_release
class CurrentDownloads(unittest.TestCase):
    def test_intro_and_stale_regression(self):
        text=(ROOT/'README.md').read_text();check_intro(text)
        with self.assertRaises(ValueError):check_intro(text.replace('/releases/latest','/releases/tag/v1.2.6'))
    def test_stable_target_and_official_assets(self):
        data={'tag_name':'v1.2.12','draft':False,'prerelease':False,'assets':[{'name':n,'size':100,'browser_download_url':f'https://github.com/{REPO}/releases/download/v1.2.12/{n}'} for n in ASSETS]}
        check_release(data)
        with self.assertRaises(ValueError):check_release({**data,'prerelease':True})
        with self.assertRaises(ValueError):check_release({**data,'assets':data['assets'][:-1]})
