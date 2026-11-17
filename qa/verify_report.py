"""Optional browser checks: requires Playwright Python and a local Chromium binary."""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
payload=json.loads((root/'large_results/combined.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1360,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content((root/'docs/index.html').read_text());page.wait_for_selector('#large-table tr')
 def expected(group,size):return len([r for r in payload['summary'] if r['comparison_group']==group and r['scale']==size])
 assert page.locator('#large-table tr').count()==expected('rectilinear',512)
 assert '262,144' in page.locator('#large-profile').inner_text()
 page.locator('#large-scale').select_option('1024');assert '1,048,576' in page.locator('#large-profile').inner_text()
 page.locator('.large-bar').first.click();assert page.locator('#large-detail').get_attribute('open') is not None
 selected=json.loads(page.locator('#large-detail-content').inner_text());assert selected['profile']['scale']==1024
 assert len(selected['repetitions'])==3
 page.locator('#large-grid').select_option('crs_4326_to_2056');page.locator('#large-scale').select_option('4096')
 assert '16,777,216' in page.locator('#large-profile').inner_text()
 assert page.locator('#large-table tr').count()==3
 assert 'pyproj' not in page.locator('#large-table').inner_text()
 page.locator('#large-grid').select_option('crs_4326_to_2056__coordinates')
 assert page.locator('#large-table tr').count()==1 and 'pyproj' in page.locator('#large-table').inner_text()
 assert page.locator('#large-detail').get_attribute('open') is None
 page.locator('#large-grid').select_option('icosahedral');page.locator('#large-scale').select_option('1024')
 assert page.locator('#large-table tr').count()==expected('icosahedral',1024)
 page.locator('#figure-scenario').select_option('constant')
 assert page.locator('#coverage-figure button').count()==96
 for width in [390,700,1360]:
  page.set_viewport_size({'width':width,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Overflow at {width}'
 page.locator('#large-grid').select_option('rectilinear');page.locator('#large-timings').screenshot(path='/tmp/regridding-large-report.png')
 assert not errors,errors
 browser.close()
print('Verified shared-size filters, timing data, three repeats, CRS distinction, original figures, responsive layout and absence of JavaScript errors.')
