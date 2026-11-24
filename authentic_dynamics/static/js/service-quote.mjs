import {estimateServiceQuote} from "./service-quote-core.mjs";

const form = document.getElementById("sq-form");
const result = document.getElementById("sq-result");
const status = document.getElementById("sq-status");
const keys = ["hours", "laborRate", "materials", "subcontractors", "travel", "overhead", "margin"];
const fieldIds = ["hours", "labor-rate", "materials", "subcontractors", "travel", "overhead", "margin"];
const money = cents => (cents / 100).toLocaleString("en-US", {style: "currency", currency: "USD"});
let report = "";

function invalidate(message) {
  result.hidden = true;
  report = "";
  status.textContent = message;
}

form.addEventListener("input", () => invalidate("Inputs changed. Calculate again to refresh the estimate."));
form.addEventListener("reset", () => invalidate("Cleared. Enter your job costs or load the illustrative example."));

form.addEventListener("submit", event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const values = Object.fromEntries(keys.map((key, index) => [
    key, document.getElementById(fieldIds[index]).valueAsNumber,
  ]));
  const jobName = document.getElementById("job-name").value.trim().slice(0, 100);
  try {
    const estimate = estimateServiceQuote(values);
    const metrics = [
      ["cost", money(estimate.totalCost)],
      ["quote", money(estimate.quote)],
      ["profit", money(estimate.profit)],
      ["margin", estimate.actualMargin.toFixed(1) + "%"],
      ["labor", money(estimate.labor)],
      ["materials", money(estimate.materials)],
      ["subcontractors", money(estimate.subcontractors)],
      ["travel", money(estimate.travel)],
      ["overhead", money(estimate.overhead)],
    ];
    for (const [id, value] of metrics) {
      document.getElementById("sq-" + id + "-result").textContent = value;
    }
    const costShare = (100 - estimate.targetMargin).toFixed(1).replace(/\.0$/, "");
    const explanation = "At a " + estimate.targetMargin.toFixed(1) +
      "% target profit margin, " + costShare + "% of the suggested price covers the costs entered. " +
      "The price is rounded up to the next cent. Sales tax is not included.";
    document.getElementById("sq-explanation").textContent = explanation;
    const labels = ["Estimated labor hours", "Loaded labor cost per hour ($)",
      "Materials & supplies ($)", "Subcontractors ($)", "Travel, equipment & disposal ($)",
      "Allocated overhead ($)", "Target profit margin (%)"];
    const lines = [
      "Authentic Dynamics — Service Job Quote Worksheet",
      "Job / estimate: " + (jobName || "Not specified"),
      "",
      ...keys.map((key, index) => labels[index] + ": " + values[key]),
      "",
      "Cost breakdown:",
      "Labor: " + money(estimate.labor),
      "Materials & supplies: " + money(estimate.materials),
      "Subcontractors: " + money(estimate.subcontractors),
      "Travel, equipment & disposal: " + money(estimate.travel),
      "Allocated overhead: " + money(estimate.overhead),
      "Total entered job costs: " + money(estimate.totalCost),
      "",
      "Suggested quote before tax: " + money(estimate.quote),
      "Estimated profit after entered costs: " + money(estimate.profit),
      "Actual margin after cent rounding: " + estimate.actualMargin.toFixed(2) + "%",
      "",
      explanation,
      "Margin is calculated on all entered costs, including allocated overhead; it is not a markup.",
      "Excludes sales tax, income taxes, permit fees and costs not entered. Verify applicable charges and scope separately.",
      "Planning estimate only; not a binding quote or tax/accounting advice.",
    ];
    report = lines.join("\n");
    result.hidden = false;
    status.textContent = "Estimate ready. Change any assumption and recalculate to compare another job.";
    document.getElementById("sq-result-heading").focus();
  } catch (error) {
    invalidate(error.message);
  }
});

document.getElementById("sq-example").addEventListener("click", () => {
  const sample = [3.5, 48, 165, 0, 32, 55, 35];
  fieldIds.forEach((id, index) => { document.getElementById(id).value = sample[index]; });
  document.getElementById("job-name").value = "Illustrative service call";
  invalidate("Illustrative example loaded, not a local price benchmark. Adjust it to your actual costs, then calculate.");
});

document.getElementById("sq-download").addEventListener("click", () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([report], {type: "text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  const label = document.getElementById("job-name").value.trim().toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);
  link.download = (label || "service-job") + "-quote-worksheet.txt";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status.textContent = "Worksheet download requested. Your browser controls where it is saved.";
});
