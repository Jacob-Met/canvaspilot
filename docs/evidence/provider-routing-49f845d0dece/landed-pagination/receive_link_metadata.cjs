const fs=require("node:fs"),http=require("node:http"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const {chromium}=require("/Users/me/workspace/estate/production-evidence-49f845d0dece/browser-tools/node_modules/playwright");
const [input,out]=process.argv.slice(2), frozen=JSON.parse(fs.readFileSync(input,"utf8"))[0];
const sha=x=>crypto.createHash("sha256").update(x).digest("hex");
assert.equal(sha(frozen.expression),frozen.expression_sha256);
const requests=[];
let origin,next,server,browser;
(async()=>{
 server=http.createServer((req,res)=>{
  if(req.url==="/probe"){
   res.writeHead(200,{"Content-Type":"text/html","Set-Cookie":"canvas_fixture=authored; Path=/; HttpOnly; SameSite=Lax"});
   res.end("<!doctype html><title>Local metadata fixture</title>");
  }else if(req.url==="/api/v1/courses"){
   requests.push({method:req.method,session_present:(req.headers.cookie||"").includes("canvas_fixture=authored"),accept:req.headers.accept});
   res.writeHead(200,{"Content-Type":"application/json","LiNk":next,"Set-Cookie":"unrelated_fixture=not-forwarded; Path=/; HttpOnly","X-Unrelated-Fixture":"not-forwarded"});
   res.end(JSON.stringify([{id:17,name:"Authored fixture assignment"}]));
  }else{res.writeHead(404);res.end();}
 });
 await new Promise(r=>server.listen(0,"127.0.0.1",r));
 origin="http://127.0.0.1:"+server.address().port;
 next='<'+origin+'/api/v1/courses?opaque=a%2Bb%3D>; rel="next"';
 browser=await chromium.launch({executablePath:"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",headless:true});
 const context=await browser.newContext();
 await context.route("**/*",r=>new URL(r.request().url()).origin===origin?r.continue():r.abort("blockedbyclient"));
 const page=await context.newPage();await page.goto(origin+"/probe",{waitUntil:"domcontentloaded"});
 const result=await page.evaluate(({expression,parameters})=>(0,eval)("("+expression+")")(parameters),{expression:frozen.expression,parameters:{method:"GET",path:"/api/v1/courses",headers:{Accept:"application/json"},body:null,providerOrigin:origin}});
 const checks={
  rows:JSON.stringify(result.json)===JSON.stringify([{id:17,name:"Authored fixture assignment"}]),
  status:result.status===200,
  only_link:JSON.stringify(result.headers)===JSON.stringify({link:next}),
  private_cookie_remains_browser:JSON.stringify(requests)===JSON.stringify([{method:"GET",session_present:true,accept:"application/json"}])
 };
 const receipt={receiver_sha256:sha(fs.readFileSync(__filename)),input_sha256:sha(fs.readFileSync(input)),source:frozen.pin,broker_sha256:frozen.broker_sha256,expression_sha256:frozen.expression_sha256,browser:browser.version(),boundary:"Exact composed production expression in actual Chrome via Playwright, authored loopback only; owner Link/cookie/JSON/status assertions retained, no school or broker startup",requests,result,checks};
 fs.writeFileSync(out,JSON.stringify(receipt,null,2)+"\n");console.log(JSON.stringify(checks));
 assert.ok(Object.values(checks).every(Boolean));await context.close();
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server)await new Promise(r=>server.close(r));});
