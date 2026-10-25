// Money is integer cents. Sales-based fees are rounded once per modeled transaction.
export function estimateEvent(values) {
  const moneyKeys = ['booth', 'labor', 'other', 'sale', 'cost', 'target'];
  const cents = {};
  for (const key of moneyKeys) {
    const value = values[key];
    if (!Number.isFinite(value) || value < 0 || value > 1000000 || (key === 'sale' && value < 0.01)) {
      throw new RangeError('Enter valid nonnegative dollar amounts and a sale of at least $0.01.');
    }
    cents[key] = Math.round((value + Number.EPSILON) * 100);
  }
  if (!Number.isFinite(values.fee) || values.fee < 0 || values.fee > 100 ||
      !Number.isInteger(values.transactions) || values.transactions < 0 || values.transactions > 100000) {
    throw new RangeError('Use fees from 0 to 100% and a whole transaction count from 0 to 100,000.');
  }
  const feesPerSale = Math.round(cents.sale * values.fee / 100);
  const contribution = cents.sale - cents.cost - feesPerSale;
  const fixed = cents.booth + cents.labor + cents.other;
  const needed = amount => amount === 0 ? 0 : contribution > 0 ? Math.ceil(amount / contribution) : null;
  return {
    fixed, contribution, feesPerSale,
    breakEven: needed(fixed), targetTransactions: needed(fixed + cents.target),
    revenue: values.transactions * cents.sale,
    profit: values.transactions * contribution - fixed,
  };
}
