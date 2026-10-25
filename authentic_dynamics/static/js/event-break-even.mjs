import {estimateEvent} from './event-break-even-core.mjs';

const form = document.getElementById('event-form');
const result = document.getElementById('event-result');
const status = document.getElementById('event-status');
const keys = ['booth', 'labor', 'other', 'sale', 'cost', 'fee', 'transactions', 'target'];
const money = cents => (cents / 100).toLocaleString('en-US', {style: 'currency', currency: 'USD'});
const count = value => value === null ? 'Not reachable' : value.toLocaleString('en-US');
let report = '';

function invalidate(message) {
  result.hidden = true;
  report = '';
  status.textContent = message;
}
form.addEventListener('input', () => invalidate('Numbers changed. Calculate to update your estimate.'));
form.addEventListener('reset', () => invalidate('Cleared. Enter your numbers or load the illustrative example.'));
form.addEventListener('submit', event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const values = Object.fromEntries(keys.map(key => [key, document.getElementById(key).valueAsNumber]));
  try {
    const estimate = estimateEvent(values);
    const entries = [
      ['fixed', 'Fixed event costs', money(estimate.fixed)],
      ['contribution', 'Contribution per sale', money(estimate.contribution)],
      ['break-even', 'Transactions to break even', count(estimate.breakEven)],
      ['target', 'Transactions for target profit', count(estimate.targetTransactions)],
      ['revenue', 'Estimated revenue', money(estimate.revenue)],
      ['profit', 'Estimated event profit / loss', money(estimate.profit)],
    ];
    for (const [id, , value] of entries) document.getElementById(`${id}-result`).textContent = value;
    const explanation = estimate.contribution <= 0
      ? 'Each sale leaves zero or less to cover fixed costs. Review pricing, product costs or fees. A zero-cost event can break even with zero sales, but these margins cannot produce positive profit.'
      : `At ${count(values.transactions)} transactions, this scenario ${estimate.profit < 0 ? 'loses' : 'earns'} ${money(Math.abs(estimate.profit))} after entered costs. Your profit goal is ${money(Math.round(values.target * 100))}.`;
    document.getElementById('event-explanation').textContent = explanation;
    const labels = ['Booth fee ($)', 'Staffing ($)', 'Other fixed costs ($)', 'Average sale ($)', 'Product cost per sale ($)', 'Sales-based fees (%)', 'Expected transactions', 'Target profit ($)'];
    report = [
      'Authentic Dynamics — Vendor Event Estimate', '',
      ...keys.map((key, index) => `${labels[index]}: ${values[key]}`), '',
      ...entries.map(([, label, value]) => `${label}: ${value}`), '', explanation, '',
      'Illustrative estimate, not a sales forecast. Assumes constant average sale and cost.',
      'Percentage fees rounded to cents per transaction. Excludes sales tax, taxes on profit and unentered overhead.',
      'https://www.authenticdynamics.com/tools/event-break-even',
    ].join('\n');
    result.hidden = false;
    status.textContent = 'Estimate ready. Change your assumptions and recalculate to compare scenarios.';
    document.getElementById('result-heading').focus();
  } catch (error) {
    invalidate(error.message);
  }
});
document.getElementById('example').addEventListener('click', () => {
  const sample = [150, 200, 50, 15, 5, 3, 100, 300];
  keys.forEach((key, index) => { document.getElementById(key).value = sample[index]; });
  invalidate('Illustrative example loaded, not a local market forecast. Adjust the numbers, then calculate.');
});
document.getElementById('download').addEventListener('click', () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([report], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'event-break-even-estimate.txt';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status.textContent = 'Estimate download requested. Your browser controls where it is saved.';
});
