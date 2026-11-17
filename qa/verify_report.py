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
 assert page.locator('#figure-scenario').count()==0, 'Small-grid figures must not remain on home'
 assert page.locator('#explorer').count()==0, 'Small-grid evidence must not remain on home'
 assert page.locator('#chunked-timings').count()==1
 assert page.locator('nav[aria-label="Report pages"] a[aria-current="page"]').get_attribute('href')=='index.html'
 chunk=json.loads((root/'chunked_results/combined.json').read_text())
 assert page.locator('#chunk-table tr').count()==len(chunk['summary'])
 assert 'including reads' in page.locator('#chunk-storage').inner_text()
 assert '42,497' in page.locator('#chunk-diagnostic').inner_text()
 assert 'no computation completed' in page.locator('#chunk-diagnostic').inner_text()
 assert '4 finite-mask mismatches' in page.locator('#chunk-accuracy-note').inner_text()
 if chunk['summary']:
  chosen=chunk['summary'][0]['tool'];page.locator('#chunk-tool').select_option(chosen)
  assert page.locator('#chunk-table tr').count()==len([r for r in chunk['summary'] if r['tool']==chosen])
  page.locator('#chunk-table details').first.click()
  assert 'synchronous' in page.locator('#chunk-table details pre').first.inner_text()
  page.locator('#chunk-tool').select_option('')
 for width in [390,700,1360]:
  page.set_viewport_size({'width':width,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Overflow at {width}'
 page.locator('#large-grid').select_option('rectilinear');page.locator('#large-timings').screenshot(path='/tmp/regridding-large-report.png')
 page.set_content((root/'docs/small-data.html').read_text());page.wait_for_selector('#results tr')
 assert page.locator('#large-timings').count()==0
 assert page.locator('nav[aria-label="Report pages"] a[aria-current="page"]').get_attribute('href')=='small-data.html'
 page.locator('#figure-scenario').select_option('constant');assert page.locator('#coverage-figure button').count()==96
 page.locator('#pkg').select_option('astropy_healpix');assert '54 of 924' in page.locator('#count').inner_text()
 page.set_content((root/'docs/tool-guide.html').read_text())
 assert page.locator('nav[aria-label="Report pages"] a[aria-current="page"]').get_attribute('href')=='tool-guide.html'
 contracts=json.loads((root/'docs/tool_contracts.json').read_text())
 assert len(contracts['tools'])==15
 assert page.locator('#contracts details').count()==15
 assert page.locator('#recommendations article').count()==11
 assert page.locator('a[href="tool-selection-skill.md"]').count()==1
 skill=(root/'skills/regridding-tool-selection/SKILL.md').read_text()
 assert skill==(root/'docs/tool-selection-skill.md').read_text()
 assert skill.startswith('---\nname: select-geospatial-regridding-tool\n')
 assert '## Workflow' in skill and '## Non-float rules' in skill
 assert '257 fields' in page.locator('#recommendations').inner_text()
 assert 'Finite coverage' in page.locator('#recommendations').inner_text()
 rules=json.loads((root/'tool_recommendations.json').read_text())
 for rule,article in zip(rules['recommendations'],page.locator('#recommendations article').all()):
  assert rule['preferred'] in article.inner_text()
  assert article.locator('tbody tr').count()==len(rule['packages'])
 for phrase in ['2^53','bit flags','scale_factor','globally constrained rounding']:
  assert phrase in page.locator('body').inner_text(),phrase
 page.locator('#contracts details').filter(has=page.locator('summary',has_text='xESMF')).first.locator('summary').click()
 assert 'nearest_s2d' in page.locator('body').inner_text()
 for width in [390,700,1360]:
  page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Guide overflow at {width}'
 comparison=json.loads((root/'external_comparisons.json').read_text())
 page.set_content((root/'docs/comparison.html').read_text())
 assert page.locator('nav[aria-label="Report pages"] a[aria-current="page"]').get_attribute('href')=='comparison.html'
 assert page.locator('.source-card').count()==len(comparison['sources'])
 assert page.locator('#source-count').inner_text()==f"{len(comparison['sources'])} of {len(comparison['sources'])} sources"
 page.locator('#topic-filter').select_option('Chunking')
 assert page.locator('.source-card:visible').count()==sum('Chunking' in x['topics'] for x in comparison['sources'])
 page.locator('#relation-filter').select_option('consistent')
 assert page.locator('.source-card:visible').count()==sum('Chunking' in x['topics'] and x['relation']=='consistent' for x in comparison['sources'])
 page.locator('#topic-filter').select_option('');page.locator('#relation-filter').select_option('')
 assert '31.7' in page.locator('#cnes-pyinterp-benchmark').inner_text()
 assert 'not a wall-clock' in page.locator('#mira-2022').inner_text()
 for width in [390,700,1360]:
  page.set_viewport_size({'width':width,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Comparison overflow at {width}'
 page.screenshot(path='/tmp/regridding-comparison.png',full_page=False)
 for file in ['index.html','small-data.html','tool-guide.html','comparison.html']:
  page.goto('about:blank')
  page.set_content((root/'docs'/file).read_text())
  assert page.locator('nav[aria-label="Report pages"] a[href="comparison.html"]').count()==1
 assert not errors,errors
 browser.close()
print('Verified four report pages, external topic/relation filters, recommendation evidence, timing controls, downloads, navigation, responsive layout and no JavaScript errors.')
