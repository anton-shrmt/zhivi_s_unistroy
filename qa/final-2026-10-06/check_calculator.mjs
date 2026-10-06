import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const html=fs.readFileSync(path.resolve(here,'../../index.html'),'utf8');
const code=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const context=vm.createContext({document:{readyState:'loading',addEventListener(){},title:'QA'},window:{location:{href:'http://127.0.0.1:4184/'}},URL});
vm.runInContext(code,context);
// Independent fixtures for the agreed rate table and rounded monthly results.
const goldens={
 longterm:{comfort:[35200,39600,52800,61600],business:[40500,45500,60700,70800]},
 guaranteed:{comfort:[30000,33800,45000,52500],business:[34500,38800,51800,60400]},
 daily:{comfort:[79500,95400,111300,127200],business:[91400,109700,128000,146300]}
};
const types=['studio','r1','r2','r3'];
const cases=[];
for(const [model,conditions] of Object.entries(goldens))for(const [condition,amounts] of Object.entries(conditions))for(const [i,type] of types.entries())for(const price of [3000000,9500000,20000000]){
 const r=context.compute({model,condition,type,price,days:265});
 assert.equal(r.monthly,amounts[i],`${model}/${condition}/${type}`);
 assert.equal(r.gross-r.commissionAmount,r.monthly);
 assert.equal(r.yearlyCash,r.monthly*12);
 assert.equal(r.appreciation,price/10);
 assert.equal(r.yearly,r.yearlyCash+price/10);
 assert.ok(Math.abs(r.yieldPct-r.yearly/price*100)<1e-10);
 const y=Math.floor(r.payback),fraction=r.payback-y;
 const before=r.yearlyCash*y+price*(1.1**y-1);
 const finalYear=r.yearlyCash+price*1.1**y*.1;
 assert.ok(Math.abs(before+fraction*finalYear-price)<.00001,'payback interpolation');
 cases.push({model,condition,type,price,days:265,monthly:r.monthly,pass:true});
}
// Boundary occupancy samples independently calculated for a one-room apartment.
for(const [days,monthly] of [[150,54000],[340,122400]]){
 const r=context.compute({model:'daily',condition:'comfort',type:'r1',price:9500000,days});
 assert.equal(r.monthly,monthly);cases.push({model:'daily',days,monthly,pass:true});
}
fs.writeFileSync(path.join(here,'calculator.json'),JSON.stringify({cases,passed:cases.length},null,2)+'\n');
console.log(`Calculator: ${cases.length} independent checks passed`);
