import fs from'node:fs';import{execFileSync}from'node:child_process';import assert from'node:assert/strict';import crypto from'node:crypto';
const root='D:/Hamon/worktrees/canvaspilot-history-0378a7b6',proof=root+'-proof',owned='7371f315869cbbea518c1ba2f1ff6e5639d384c0';
const git=(...a)=>execFileSync('git',['-C',root,...a],{encoding:'utf8'}).trim();const show=(rev,file)=>execFileSync('git',['-C',root,'show',rev+':'+file],{encoding:'utf8'});
const current=git('rev-parse','MERGE_HEAD');const cliFile='src/canvaspilot/cli.py',oldCli=show(owned,cliFile),mainCli=show(current,cliFile);
function between(s,a,b){const x=s.indexOf(a),y=s.indexOf(b,x);assert(x>=0&&y>x);return s.slice(x,y);}
const parser=between(oldCli,'    history_export = sub.add_parser(','    agenda = sub.add_parser(');
const dispatch=between(oldCli,'        elif args.cmd == "export-submission-history":','        elif args.cmd == "submission-history":');
assert(!mainCli.includes('export-submission-history'));
let cli=mainCli.replace('    comparison = sub.add_parser(',parser+'    comparison = sub.add_parser(').replace('        elif args.cmd == "compare-submissions":',dispatch+'        elif args.cmd == "compare-submissions":');
assert.equal(cli.replace(parser,'').replace(dispatch,''),mainCli);assert(cli.length>mainCli.length);fs.writeFileSync(root+'/'+cliFile,cli);
const section=between(show(owned,'README.md'),'## Save submission attempts for offline review','## Assignment briefs');
const mainReadme=show(current,'README.md');const readme=mainReadme.replace('## Assignment briefs',section+'## Assignment briefs');assert.equal(readme.replace(section,''),mainReadme);fs.writeFileSync(root+'/README.md',readme);
const sha=crypto.createHash('sha256').update(fs.readFileSync(root+'/src/canvaspilot/submission_history_export.py')).digest('hex');assert.equal(sha,'b574c8e81f3f48753723416645c252a23a77368c1812fe7334c69d51cd86d17f');
git('add','--',cliFile,'README.md');assert.equal(git('diff','--name-only','--diff-filter=U'),'');const result=git('commit','--no-edit');
const receipt={at:new Date().toISOString(),owned,current,commit:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}'),formatter_sha256:sha,all_existing_cli_and_readme_bytes_preserved:true,added_parser_bytes:parser.length,added_dispatch_bytes:dispatch.length,result};
fs.writeFileSync(proof+'/composition-receipt.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt,null,2));
