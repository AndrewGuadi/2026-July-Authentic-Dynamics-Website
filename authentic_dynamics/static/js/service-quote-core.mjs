// All currency values are integer cents; the quote rounds up so it does not miss the target margin.
export function estimateServiceQuote(values) {
  if (!Number.isFinite(values.hours) || values.hours < 0 || values.hours > 10000) {
    throw new RangeError("Enter labor hours from 0 to 10,000.");
  }
  if (!Number.isFinite(values.margin) || values.margin < 0 || values.margin > 90) {
    throw new RangeError("Choose a target profit margin from 0 to 90%.");
  }
  const limits = {laborRate: 10000, materials: 1000000, subcontractors: 1000000,
    travel: 1000000, overhead: 1000000};
  const cents = {};
  for (const [key, maximum] of Object.entries(limits)) {
    const value = values[key];
    if (!Number.isFinite(value) || value < 0 || value > maximum) {
      throw new RangeError("Enter nonnegative costs within the limits shown.");
    }
    cents[key] = Math.round((value + Number.EPSILON) * 100);
  }
  const labor = Math.round(values.hours * cents.laborRate);
  const directCosts = labor + cents.materials + cents.subcontractors + cents.travel;
  const totalCost = directCosts + cents.overhead;
  if (totalCost <= 0) {
    throw new RangeError("Enter at least one job cost above $0.00 before calculating.");
  }
  const marginBasisPoints = Math.round(values.margin * 100);
  const quote = Math.ceil(totalCost * 10000 / (10000 - marginBasisPoints));
  const profit = quote - totalCost;
  return {
    labor, materials: cents.materials, subcontractors: cents.subcontractors,
    travel: cents.travel, overhead: cents.overhead, directCosts, totalCost,
    quote, profit, targetMargin: marginBasisPoints / 100,
    actualMargin: quote > 0 ? profit / quote * 100 : 0,
  };
}
