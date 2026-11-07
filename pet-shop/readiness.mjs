import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

export function economics(quote) {
  // All amounts are ZAR cash amounts on the same VAT basis. This is a
  // management estimate, not accounting profit or a tax calculation.
  const keys = ['retail', 'customerShipping', 'supplierCost', 'supplierShipping',
    'supplierServiceFee', 'paymentRate', 'paymentFixed', 'platformRate',
    'refundReserve', 'adCostPerOrder', 'monthlyFixedCosts', 'launchCost'];
  if (keys.some(k => !Number.isFinite(quote[k]) || quote[k] < 0)) {
    return { status: 'quote_incomplete', reason: 'Every cost must be explicitly quoted or set to an explained zero.' };
  }
  if (quote.paymentRate > 1 || quote.platformRate > 1) {
    return { status: 'quote_invalid', reason: 'Fee rates must be decimal fractions between 0 and 1.' };
  }
  const receipts = quote.retail + quote.customerShipping;
  const contribution = receipts - quote.supplierCost - quote.supplierShipping
    - quote.supplierServiceFee - receipts * (quote.paymentRate + quote.platformRate)
    - quote.paymentFixed - quote.refundReserve - quote.adCostPerOrder;
  const round = n => Math.round(n * 100) / 100;
  return {
    status: contribution > 0 ? 'positive_contribution' : 'does_not_break_even',
    contributionPerOrderZar: round(contribution),
    firstMonthBreakEvenOrders: contribution > 0 ? Math.ceil((quote.launchCost + quote.monthlyFixedCosts) / contribution) : null,
    monthlyBreakEvenOrders: contribution > 0 ? Math.ceil(quote.monthlyFixedCosts / contribution) : null,
    estimatedSupplierCashPerOrderZar: round(quote.supplierCost + quote.supplierShipping + quote.supplierServiceFee),
    recoveryDate: 'Unknown until a real sales rate and settlement timing are observed.'
  };
}

export function readiness(state) {
  const required = ['supplier_verified', 'store_access_verified', 'payment_connection_verified',
    'automatic_supplier_payment_verified', 'end_to_end_order_verified', 'stock_sync_verified',
    'returns_process_verified', 'working_capital_verified'];
  const blockers = required.filter(k => state[k] !== true);
  if (!state.store_url) blockers.push('store_url_missing');
  if (!state.supplier) blockers.push('supplier_missing');
  if (!state.market_confirmed) blockers.push('market_unconfirmed');
  if (!state.products?.length) blockers.push('no_verified_products');
  const productEconomics = (state.products ?? []).map(p => ({ sku: p.sku, ...economics(p.quote ?? {}) }));
  if (productEconomics.some(p => p.status !== 'positive_contribution')) blockers.push('product_economics_unverified_or_negative');
  return { ready: blockers.length === 0, blockers, spendLimitZar: state.spend_limit_zar,
    paidAdsAuthorised: state.paid_ads_authorised === true, productEconomics,
    note: 'Read-only preparation check; no live integrations or enforcement of store settings.' };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const state = JSON.parse(await readFile(new URL('./launch.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(readiness(state), null, 2));
}
