"""Run the controls in a real browser against temporary settings, not the display."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

from flask import Flask, render_template_string
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
import test_plugin

fixture = test_plugin.PluginTests()
fixture.setUp()
app = Flask(__name__)
app.config['REFRESH_TASK'] = fixture.plugin.task
fixture.config.get_config.return_value = 'Australia/Sydney'
with patch('threading.Thread.start'):
    app.register_blueprint(fixture.plugin.get_blueprint())
settings = (Path(__file__).resolve().parents[1]/'plugins/game_display/settings.html').read_text()
check = '''<script>
(async()=>{
 const wait=async()=>{for(let n=0;n<100;n++){if(!document.querySelector('#gd-fields').disabled)return;await new Promise(r=>setTimeout(r,50));}throw new Error('Settings not ready');};
 try {
  await wait();
  if(document.querySelectorAll('.gd-cell').length!==168)throw new Error('Wrong cell count');
  document.querySelector('#gd-enabled').click(); await wait();
  let data=await (await fetch('/game_display/controls')).json();
  if(data.controls.enabled!==false)throw new Error('Off switch failed');
  document.querySelector('#gd-enabled').click(); await wait();
  document.querySelector('#gd-scheduled').click(); await wait();
  document.querySelector('#gd-clear').click();
  document.querySelector('[data-day="0"][data-hour="9"]').click();
  document.querySelector('[data-day="3"][data-hour="19"]').click();
  document.querySelector('#gd-save').click(); await wait();
  data=await (await fetch('/game_display/controls')).json();
  if(!data.controls.enabled || !data.controls.schedule_enabled || !data.controls.hours[0][9] || !data.controls.hours[3][19] || data.controls.hours.flat().filter(Boolean).length!==2)throw new Error('Schedule save failed');
  const grid=document.querySelector('#gd-grid');
  if(grid.scrollWidth>grid.clientWidth+2)throw new Error('Grid overflows its columns');
  for(let n=0;n<100 && document.querySelector('#gd-option-fields').disabled;n++)await new Promise(r=>setTimeout(r,50));
  document.querySelector('#gd-options').open=true;
  document.querySelector('#gd-option-ha_url').value='http://ha.test:8123';
  document.querySelector('#gd-option-master_entity').value='sensor.player';
  document.querySelector('#gd-option-poll_interval_seconds').value='20';
  document.querySelector('#gd-options-save').click();
  for(let n=0;n<100 && document.querySelector('#gd-option-fields').disabled;n++)await new Promise(r=>setTimeout(r,50));
  const options=await (await fetch('/game_display/settings')).json();
  if(options.settings.ha_url!=='http://ha.test:8123'||options.settings.master_entity!=='sensor.player'||options.settings.poll_interval_seconds!==20)throw new Error('Plugin settings save failed');
  if(document.querySelector('.gd-controls').innerText.includes('test-native-token'))throw new Error('Token leaked into UI');
  document.body.dataset.testResult='passed';
 }catch(error){document.body.dataset.testResult='failed: '+error.message;}
})();
</script>'''

@app.route('/')
def page():
    return render_template_string('<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="font:14px Arial;background:#f4f5f8;margin:0"><main style="max-width:720px;margin:32px auto;padding:28px;background:white;border-radius:16px"><h2 style="margin-top:0">Game Display</h2>'+settings+'</main>'+check+'</body></html>')

server=make_server('127.0.0.1', 8766, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with tempfile.TemporaryDirectory() as profile:
        result=subprocess.run(['/usr/bin/chromium-headless-shell','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--user-data-dir='+profile,'--window-size=1000,1450','--virtual-time-budget=10000','--dump-dom','--screenshot=/tmp/inky-controls-ui.png','http://127.0.0.1:8766/'],capture_output=True,text=True,timeout=50)
    if 'data-test-result="passed"' not in result.stdout:
        print(result.stdout[-3000:]);print(result.stderr[-1200:]);raise SystemExit('Browser check failed')
    print('Browser check passed: 168 cells, on/off, schedule save, correct grid size, portable settings save, no token disclosure.')
finally:
    server.shutdown()
    fixture.tearDown()
