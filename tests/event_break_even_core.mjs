import assert from 'node:assert/strict';
import {estimateEvent} from '../authentic_dynamics/static/js/event-break-even-core.mjs';
const sample = {booth:150, labor:200, other:50, sale:15, cost:5, fee:3, transactions:100, target:300};
assert.deepEqual(estimateEvent(sample), {fixed:40000, contribution:955, feesPerSale:45, breakEven:42, targetTransactions:74, revenue:150000, profit:55500});
// One sale below the rounded-up threshold loses money; the threshold covers costs.
assert.ok(estimateEvent({...sample, transactions:41}).profit < 0);
assert.ok(estimateEvent({...sample, transactions:42}).profit >= 0);
assert.equal(estimateEvent({...sample, transactions:73}).profit, 29715);
assert.equal(estimateEvent({...sample, transactions:74}).profit, 30670);
for (const cost of [15, 20]) {
  const result = estimateEvent({...sample, cost, fee:0});
  assert.equal(result.breakEven, null);
  assert.equal(result.targetTransactions, null);
  assert.ok(result.profit < 0);
}
const free = estimateEvent({...sample, booth:0,labor:0,other:0,cost:15,fee:0,target:0,transactions:0});
assert.equal(free.breakEven,0); assert.equal(free.profit,0);
assert.equal(estimateEvent({...sample,sale:0.10,cost:0.03,fee:0,booth:0.21,labor:0,other:0}).breakEven,3);
assert.equal(estimateEvent({...sample,sale:10.50,fee:3}).feesPerSale,32);
for (const bad of [{sale:0},{booth:-1},{sale:Infinity},{fee:101},{transactions:1.5},{transactions:100001},{cost:NaN}]) {
  assert.throws(()=>estimateEvent({...sample,...bad}),RangeError);
}
console.log('Arithmetic, rounding, thresholds, loss scenarios and bounds passed.');
