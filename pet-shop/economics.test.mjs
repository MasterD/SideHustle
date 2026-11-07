import assert from 'node:assert/strict';
import { economics, readiness } from './readiness.mjs';

// Synthetic numbers for arithmetic checks, never supplier quotes or real sales.
const q = { retail: 599, customerShipping: 0, supplierCost: 250,
  supplierShipping: 80, supplierServiceFee: 0, paymentRate: 0.03,
  paymentFixed: 2, platformRate: 0.02, refundReserve: 20,
  adCostPerOrder: 120, monthlyFixedCosts: 499, launchCost: 300 };
const result = economics(q);
assert.equal(result.contributionPerOrderZar, 97.05);
assert.equal(result.firstMonthBreakEvenOrders, 9);
assert.equal(result.monthlyBreakEvenOrders, 6);
assert.equal(economics({ ...q, supplierCost: null }).status, 'quote_incomplete');
assert.equal(economics({ ...q, paymentRate: 3 }).status, 'quote_invalid');
assert.equal(economics({ ...q, supplierCost: 800 }).firstMonthBreakEvenOrders, null);
assert.equal(readiness({ products: [] }).ready, false);
console.log('Passed: margin, fee validation, missing costs, negative margin and launch blockers.');
