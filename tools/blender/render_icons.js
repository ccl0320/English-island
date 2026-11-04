// node tools/blender/render_icons.js [models/icons.glb] [icons/] [size]
// Serves tools/blender/ + lib/ itself and writes one PNG per prop. Needs Playwright with a Chromium.
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),http=require('http');
const root=path.resolve(__dirname,'../..'),glb=path.resolve(process.argv[2]||'models/icons.glb'),out=path.resolve(process.argv[3]||'icons'),S=process.argv[4]||256;
const three=process.env.THREE_JS; // optional local three.min.js r128 if the CDN is unreachable
(async()=>{fs.mkdirSync(out,{recursive:true});
 const srv=http.createServer((q,s)=>{let u=decodeURIComponent(q.url.split('?')[0]);let f=u.endsWith('icons.glb')?glb:path.join(root,u);
  fs.readFile(f,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':f.endsWith('.html')?'text/html':f.endsWith('.js')?'text/javascript':'application/octet-stream'});s.end(d)})}).listen(0);
 const port=srv.address().port,b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage();p.on('pageerror',e=>console.log('ERR',e.message));
 if(three)await p.route('**/three.min.js',r=>r.fulfill({body:fs.readFileSync(three),contentType:'text/javascript'}));
 await p.goto(`http://localhost:${port}/tools/blender/render_icons.html?s=${S}`);await p.waitForFunction(()=>window.done,null,{timeout:120000});
 const o=await p.evaluate(()=>window.out);for(const [k,v] of Object.entries(o))fs.writeFileSync(path.join(out,k+'.png'),Buffer.from(v.split(',')[1],'base64'));
 console.log(Object.keys(o).length,'icons ->',out);await b.close();srv.close()})();
