import assert from "node:assert/strict";
import {estimateServiceQuote} from "../authentic_dynamics/static/js/service-quote-core.mjs";

const sample = {hours:3.5, laborRate:48, materials:165, subcontractors:0,
  travel:32, overhead:55, margin:35};
const result = estimateServiceQuote(sample);
assert.deepEqual(result, {
  labor:16800, materials:16500, subcontractors:0, travel:3200, overhead:5500,
  directCosts:36500, totalCost:42000, quote:64616, profit:22616,
  targetMargin:35, actualMargin:22616 / 64616 * 100,
});
assert.ok(result.actualMargin >= sample.margin);
assert.equal(estimateServiceQuote({...sample, margin:0}).quote, 42000);
assert.equal(estimateServiceQuote({...sample, margin:90}).quote, 420000);
assert.equal(estimateServiceQuote({...sample, hours:0, laborRate:0}).labor, 0);
assert.equal(estimateServiceQuote({...sample, materials:0, subcontractors:0,
  travel:0, overhead:0, hours:2, laborRate:50}).totalCost, 10000);
assert.equal(estimateServiceQuote({...sample, margin:12.5}).targetMargin, 12.5);

for (const bad of [
  {hours:-1}, {hours:10001}, {hours:NaN}, {laborRate:-1}, {laborRate:10001},
  {materials:1000001}, {subcontractors:Infinity}, {travel:-0.01}, {overhead:NaN},
  {margin:-0.1}, {margin:90.1}, {margin:Infinity},
]) {
  assert.throws(() => estimateServiceQuote({...sample, ...bad}), RangeError);
}
assert.throws(() => estimateServiceQuote({hours:0,laborRate:0,materials:0,
  subcontractors:0,travel:0,overhead:0,margin:35}), /at least one job cost/);
console.log("Service quote arithmetic, cent rounding, margin targets, and input bounds passed.");
