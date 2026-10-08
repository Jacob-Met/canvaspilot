const fs = require("node:fs");
const http = require("node:http");
const crypto = require("node:crypto");
const path = require("node:path");
const {chromium} = require("/Users/me/workspace/estate/production-evidence-49f845d0dece/browser-tools/node_modules/playwright");
const [input, output] = process.argv.slice(2);
const expressions = JSON.parse(fs.readFileSync(input, "utf8"));
fs.mkdirSync(output, {recursive:false});
const sha = value => crypto.createHash("sha256").update(value).digest("hex");
const requests = [];
const origins = {};
function makeServer(name) {
  return http.createServer((req, res) => {
    const origin = req.headers.origin;
    if (origin === origins.a || origin === origins.b) {
      res.setHeader("Access-Control-Allow-Origin", origin);
      res.setHeader("Access-Control-Allow-Credentials", "true");
    }
    if (req.url.startsWith("/api/")) {
      requests.push({server:name, method:req.method, path:req.url, origin:origin || null});
    }
    if (req.url === "/api/redirect") {
      res.writeHead(302, {Location:origins.b+"/api/assignments"});
      res.end();
    } else if (req.url.startsWith("/api/")) {
      res.writeHead(200, {"Content-Type":"application/json", "Link":""});
      res.end(JSON.stringify([{id:1, name:"Authored "+name, provider:origins[name]}]));
    } else {
      res.writeHead(200, {"Content-Type":"text/html"});
      const base = req.url === "/foreign-base" ? '<base href="'+origins.b+'/courses">' : "";
      res.end("<!doctype html><html><head>"+base+"<title>Authored "+name+"</title></head><body>Local provider fixture</body></html>");
    }
  });
}
(async () => {
  const a=makeServer("a"), b=makeServer("b");
  await new Promise(r=>a.listen(0,"127.0.0.1",r));
  await new Promise(r=>b.listen(0,"127.0.0.1",r));
  origins.a="http://127.0.0.1:"+a.address().port;
  origins.b="http://127.0.0.1:"+b.address().port;
  let browser;
  const runs=[];
  try {
    browser=await chromium.launch({executablePath:"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",headless:true});
    const version=browser.version();
    const context=await browser.newContext();
    await context.route("**/*", route => {
      const u=new URL(route.request().url());
      if (u.origin===origins.a || u.origin===origins.b) return route.continue();
      return route.abort("blockedbyclient");
    });
    const page=await context.newPage();
    for (const frozen of expressions) {
      if(sha(frozen.expression)!==frozen.expression_sha256) throw new Error("expression hash mismatch");
      const cases=[
        {name:"matching", page:origins.a+"/courses", request:"/api/assignments"},
        {name:"wrong-selected-page", page:origins.b+"/courses", request:"/api/assignments"},
        {name:"foreign-base-element", page:origins.a+"/foreign-base", request:"/api/assignments"},
        {name:"foreign-request-url", page:origins.a+"/courses", request:origins.b+"/api/assignments"},
        {name:"foreign-redirect-response", page:origins.a+"/courses", request:"/api/redirect"},
      ];
      const results=[];
      for (const test of cases) {
        await page.goto(test.page,{waitUntil:"domcontentloaded"});
        const documentState=await page.evaluate(()=>({href:location.href,origin:location.origin,baseURI:document.baseURI}));
        const start=requests.length;
        let value=null,error=null;
        try {
          value=await page.evaluate(frozen.expression,{method:"GET",path:test.request,headers:{Accept:"application/json"},body:null,providerOrigin:origins.a});
        } catch(e) {error=String(e);}
        const observed=requests.slice(start);
        let pass;
        if(test.name==="matching" || test.name==="foreign-base-element") {
          pass=!error && value?.json?.[0]?.provider===origins.a &&
            observed.length===1 && observed[0].server==="a";
        } else if(test.name==="foreign-redirect-response") {
          pass=!!error && /provider mismatch/.test(error) && value===null;
        } else {
          pass=!!error && /provider mismatch/.test(error) && observed.length===0 && value===null;
        }
        results.push({name:test.name,pass,documentState,request:test.request,value,error,requests:observed});
      }
      runs.push({pin:frozen.pin,broker_sha256:frozen.broker_sha256,expression_sha256:frozen.expression_sha256,
        passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results});
    }
    await context.close();
    const receipt={receiver_sha256:sha(fs.readFileSync(__filename)),browser:version,executable:"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      input:path.resolve(input),input_sha256:sha(fs.readFileSync(input)),origins,
      boundary:"Exact production JavaScript expression in a fresh actual Chrome context; authored loopback HTTP only; no Python broker/browser startup claim",
      redirect_limit:"Response-origin guard refuses foreign redirected data after the browser follows the redirect; no prevention of the redirect network request is claimed.",
      runs};
    fs.writeFileSync(path.join(output,"receipt.json"),JSON.stringify(receipt,null,2)+"\n");
    console.log(JSON.stringify(runs.map(r=>({pin:r.pin,passed:r.passed,failed:r.failed,failed_cases:r.results.filter(x=>!x.pass).map(x=>x.name)}))));
  } finally {
    if(browser) await browser.close();
    await new Promise(r=>a.close(r));
    await new Promise(r=>b.close(r));
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
