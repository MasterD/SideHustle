import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=new URL('.',import.meta.url).pathname.replace(/^\/C:/,'C:');
const wb=Workbook.create(), s=wb.worksheets.add('ROI'), e=wb.worksheets.add('Evidence');
const money='"$"#,##0.00;("$"#,##0.00);"—"';
for(const sh of [s,e]){sh.showGridLines=false;sh.getRange('A1:H75').format.font={name:'Calibri',size:11};sh.getRange('A1:H75').format.rowHeight=23;}
s.getRange('A:A').format.columnWidth=38;s.getRange('B:B').format.columnWidth=18;s.getRange('C:C').format.columnWidth=3;s.getRange('D:D').format.columnWidth=35;s.getRange('E:E').format.columnWidth=16;s.getRange('F:F').format.columnWidth=3;s.getRange('G:G').format.columnWidth=49;
s.getRange('A2').values=[['Pet store ROI']];s.getRange('A2').format.font={bold:true,size:19};
s.getRange('D2').values=[['USD model | 8 October 2026']];
s.getRange('A3').values=[['Unverified inputs remain blank. Results show n.a. until their inputs are entered.']];
s.getRange('A4').values=[['All profit/ROI figures exclude income tax. Reserve is cash tied up, not an expense.']];
s.getRange('A3:G4').format.font={size:10,color:'#555555'};
function band(sh,r,cols){sh.getRange(r).values=[cols];sh.getRange(r).format={fill:'#243B53',font:{bold:true,color:'#FFFFFF'}};}
band(s,'A5:B5',['Result','Value']);band(s,'D5:E5',['Editable input','USD / rate']);
const inputs=[
['Selling price excluding sales tax',null,'Proposed price; not a confirmed market price'],
['Customer shipping charge',null,'Revenue charged to buyer; enter 0 if included'],
['Supplier item cost',7.21,'Observed leash quote, 8 October'],
['Supplier shipping',4.99,'US destination only; per leash'],
['Supplier tax / extra service cost',null,'Confirm tax and all mandatory charges'],
['Wallet fee per order',null,'Use actual deposit fee / orders funded'],
['Payment provider percentage',null,'Chosen provider and international card quote needed'],
['Payment provider fixed fee',null,'USD equivalent; include mandatory fee tax'],
['Shopify transaction percentage',0.02,'Published SA Basic; confirm account applicability'],
['Sales tax added to buyer charge',null,'Pass-through tax; enter applicable rate or 0'],
['FX / cross-border cost per order',null,'Both collection and supplier-payment conversion'],
['Expected refund/dispute loss per order',null,'Net expected loss; exclude already counted fees'],
['Customer acquisition cost per order',null,'All paid acquisition; organic cash CAC may be 0'],
['AppScenic monthly subscription',39,'Published Standard; SKU tier not verified'],
['Shopify monthly subscription',25,'Published SA Basic monthly; account quote needed'],
['Monthly subscription taxes',null,'Confirm invoices; enter 0 only if none'],
['Other monthly operating costs',null,'Apps, domain allocation, labour if desired'],
['One-off launch expenses',null,'Samples, domain upfront, creative, setup ads'],
['Qualified store visits per day',null,'Scenario assumption until actual traffic exists'],
['Visit-to-order conversion rate',null,'Scenario assumption; excludes repeat-purchase value'],
['Payout delay / reserve days',null,'Include holds, weekends and gateway delays'],
['Peak orders per day',null,'Reserve planning; may exceed average traffic orders'],
['Minimum usable supplier wallet balance',null,'Not yet quoted; exclude fees counted per order'],
['Additional refund cash buffer',null,'Liquidity allowance, not another expense'],
['Prepaid advertising cash buffer',null,'Liquidity allowance; CAC already counted in profit'],
['Fixed-cost cash cushion in months',null,'User risk tolerance / liquidity runway'],
['ROI horizon in months',null,'Explicit investment period'],
['ZAR per USD',null,'Use bank executable rate; avoid double-counting FX'],
['Days per model month',30,'Planning convention; no calendar forecast']];
s.getRange('D6:E34').values=inputs.map(x=>x.slice(0,2));s.getRange('G6:G34').values=inputs.map(x=>[x[2]]);
s.getRange('E6:E34').format={fill:'#FFF2CC',font:{color:'#0000FF'},numberFormat:money};s.getRange('G6:G34').format.font={size:10,color:'#555555'};
for(const r of [12,14,15,25])s.getRange(`E${r}`).setNumberFormat('0.0%');
for(const r of [24,26,27,31,32,34])s.getRange(`E${r}`).setNumberFormat('0.0');
s.getRange('E33').setNumberFormat('0.0000');
s.getRange('E6:E34').conditionalFormats.add('containsBlanks',{format:{fill:'#FCE4D6'}});
for(const r of [12,14,15,25])s.getRange(`E${r}`).dataValidation={rule:{type:'decimal',operator:'between',formula1:0,formula2:1}};
band(s,'A25:B25',['Calculation','USD / units']);
const calcs=[
['Revenue per order, excluding tax','=IF(COUNT(E6:E7)=2,SUM(E6:E7),"n.a.")'],
['Gross amount for fee calculation','=IF(AND(ISNUMBER(B26),ISNUMBER(E15)),B26*(1+E15),"n.a.")'],
['Supplier cash cost incl. wallet / FX','=IF(COUNT(E8:E11,E16)=5,SUM(E8:E11,E16),"n.a.")'],
['Payment processing per order','=IF(AND(ISNUMBER(B27),COUNT(E12:E13)=2),B27*E12+E13,"n.a.")'],
['Shopify transaction fee per order','=IF(AND(ISNUMBER(B27),ISNUMBER(E14)),B27*E14,"n.a.")'],
['Refund/dispute loss allowance','=IF(ISNUMBER(E17),E17,"n.a.")'],
['Contribution before acquisition','=IF(COUNT(B26,B28:B31)=5,B26-SUM(B28:B31),"n.a.")'],
['Contribution after acquisition','=IF(AND(ISNUMBER(B32),ISNUMBER(E18)),B32-E18,"n.a.")'],
['Monthly fixed operating costs','=IF(COUNT(E19:E22)=4,SUM(E19:E22),"n.a.")'],
['Expected orders per month','=IF(COUNT(E24:E25,E34)=3,E24*E25*E34,"n.a.")'],
['Monthly profit before income tax','=IF(COUNT(B33:B35)=3,B33*B35-B34,"n.a.")'],
['Launch expenses','=IF(ISNUMBER(E23),E23,"n.a.")'],
['Supplier and extra liquidity reserve','=IF(AND(ISNUMBER(B28),COUNT(E26:E30)=5),MAX(E28,ROUNDUP(E27*E26,0)*B28)+SUM(E29:E30),"n.a.")'],
['Initial cash commitment','=IF(AND(COUNT(B34,B37:B38)=3,ISNUMBER(E31)),B37+B38+B34*E31,"n.a.")'],
['Profit over horizon less launch costs','=IF(AND(COUNT(B36:B37)=2,ISNUMBER(E32)),B36*E32-B37,"n.a.")'],
['ROI on initial committed cash','=IF(COUNT(B39:B40)=2,IF(B39>0,B40/B39,"n.a."),"n.a.")'],
['Launch-expense payback, months','=IF(COUNT(B36:B37)=2,IF(B36>0,B37/B36,"n.a."),"n.a.")'],
['Months to earn initial cash amount','=IF(COUNT(B36,B39)=2,IF(B36>0,B39/B36,"n.a."),"n.a.")'],
['Monthly break-even whole orders','=IF(COUNT(B33:B34)=2,IF(B33>0,ROUNDUP(B34/B33,0),"n.a."),"n.a.")'],
['First-month break-even whole orders','=IF(COUNT(B33:B34,B37)=3,IF(B33>0,ROUNDUP((B34+B37)/B33,0),"n.a."),"n.a.")'],
['Expected days per order','=IF(COUNT(E24:E25)=2,IF(E24*E25>0,1/(E24*E25),"n.a."),"n.a.")'],
['First-sale probability within 30 days','=IF(COUNT(E24:E25,E34)=3,1-(1-E25)^(E24*E34),"n.a.")'],
['Zero-sales loss over chosen horizon','=IF(AND(COUNT(B34,B37)=2,ISNUMBER(E32)),B37+B34*E32,"n.a.")'],
['Maximum CAC at forecast volume','=IF(COUNT(B32,B34:B35)=3,IF(B35>0,B32-B34/B35,"n.a."),"n.a.")'],
['Initial cash commitment in ZAR','=IF(AND(ISNUMBER(B39),ISNUMBER(E33)),B39*E33,"n.a.")']];
s.getRange('A26:A50').values=calcs.map(x=>[x[0]]);s.getRange('B26:B50').formulas=calcs.map(x=>[x[1]]);s.getRange('B26:B50').setNumberFormat(money);
for(const r of [35,42,43,44,45,46])s.getRange(`B${r}`).setNumberFormat('0.0');for(const r of [41,47])s.getRange(`B${r}`).setNumberFormat('0.0%');
const heads=[[6,'Contribution after acquisition',33],[7,'Monthly fixed costs',34],[8,'Expected monthly orders',35],[9,'Monthly profit before income tax',36],[10,'Monthly break-even orders',44],[11,'First-month break-even orders',45],[12,'Initial cash commitment',39],[13,'Horizon ROI on committed cash',41],[14,'Launch expense payback (months)',42],[15,'Expected days per order',46],[16,'Zero-sales horizon loss',48],[17,'Maximum CAC at forecast volume',49],[18,'Initial cash commitment (ZAR)',50]];
for(const [r,label,src]of heads){s.getRange(`A${r}`).values=[[label]];s.getRange(`B${r}`).formulas=[[`=B${src}`]];s.getRange(`B${r}`).setNumberFormat([8,10,11,14,15].includes(r)?'0.0':r===13?'0.0%':money);}
s.getRange('A53').values=[['n.a. means missing input or no positive payback.']];
s.getRange('A54').values=[['No traffic history exists. Timing is a scenario, not a delivery date or promise.']];
s.getRange('A55').values=[['Zero-sales loss excludes extra ad spend, disputes and unrecoverable wallet funds.']];
s.getRange('A56').values=[['Cash reserve is only a planning estimate; payout holds can require more cash.']];
s.getRange('A53:G56').format.font={size:10,color:'#555555'};
s.getRange('B6:B50').format.horizontalAlignment='right';
s.getRange('D37').values=[['How to test risk and reward']];s.getRange('D37').format.font={bold:true};
const notes=['Fill each blank cost with a verified quote or an explicit assumption.','Test 0%, 0.5%, 1% and 2% conversion by changing E25.','Vary visits/day, CAC, selling price, refunds and payout delays.','These conversion rates are illustrations, not industry benchmarks.','Days per order = 1 / (visits/day × conversion). It is an average.','Probability assumes independent visits and constant conversion.','Cash earning time assumes flat profits; it is not a cash-flow forecast.','Confirm minimum wallet amount and billing before any commitment.'];
s.getRange('D38:D45').values=notes.map(x=>[x]);s.getRange('D38:G45').format.font={size:10,color:'#555555'};
s.freezePanes.freezeRows(5);
e.getRange('A:A').format.columnWidth=33;e.getRange('B:B').format.columnWidth=19;e.getRange('C:C').format.columnWidth=60;e.getRange('D:D').format.columnWidth=75;
e.getRange('A2').values=[['Costs and task evidence']];e.getRange('A2').format.font={bold:true,size:19};
band(e,'A4:D4',['Cost / task','Value / status','Meaning / next step','Source']);
const rows=[
['AppScenic Standard monthly',39,'Published; 100 products; premium products excluded','https://appscenic.com/pricing'],
['Shopify Basic monthly',25,'Published South African monthly price, not account invoice','https://www.shopify.com/za/pricing'],
['Combined published monthly fees',64,'Before taxes, payment fees, ads and order costs','Published Standard + Basic monthly prices'],
['Shopify annual alternative',228,'$19/month equivalent paid yearly; $228 upfront; avoid annual lock-in for test','https://www.shopify.com/za/pricing'],
['Shopify advertised introduction',1,'$1/month for 3 months; existing-account eligibility unverified','https://www.shopify.com/za/pricing'],
['Supplier item cost',7.21,'Leash LED9562 Light Blue or LED9556 Red; observed 8 October','https://retailer.appscenic.com/#catalog'],
['US shipping per leash',4.99,'2–8 days shown plus separate 2 days average processing','https://retailer.appscenic.com/#catalog'],
['Supplier cost + shipping',12.20,'Not total cost; 10 unfunded orders need at least $122 before fees','Authenticated catalogue quote, 8 October 2026'],
['Stock evidence','Mixed','Light Blue/Red in stock; Blue/Gray out of stock','Authenticated variant list, 8 October 2026'],
['Wallet processing fee','Unverified','Page says add a store first; no store connected for quote','https://retailer.appscenic.com/#wallet'],
['Wallet help example','Ambiguous','Dated USD 3.47% + 20p; do not assume fixed amount in USD','https://helpdesk.appscenic.com/support/solutions/articles/80001142302'],
['Shopify Basic transaction fee',0.02,'Additional to gateway fee; base includes tax and buyer shipping','https://www.shopify.com/za/pricing'],
['Refunded platform fees','Not returned','Shopify third-party transaction fees remain paid on refund','https://help.shopify.com/en/manual/your-account/manage-billing/billing-charges/types-of-charges/third-party-charges/third-party-transaction-fees'],
['Shopify Payments / SA','Not listed','South Africa absent from supported countries; merchant country must be verified','https://help.shopify.com/en/manual/payments/shopify-payments/supported-countries'],
['Gateway and settlement','Unverified','Provider, international eligibility, chargebacks, FX, holds, fee taxes needed','No provider connected or account quote verified'],
['Task 1: all fees','Awaiting access','Wallet requires store connection; Shopify tab reached login','Read-only checks, 8 October 2026'],
['Task 2: supplier terms','Awaiting reply authority','14 days; contradictory packaging text; discounted sale items may be final','Authenticated policy; support enquiry drafted, unsent'],
['Resale channels','Restricted','Supplier prohibits Amazon, eBay and Walmart; verify Shopify/image licence','Authenticated supplier policy, 8 October 2026'],
['Task 3: ROI model','Prepared','Editable calculator; unknown costs blank; no established sales forecast','This workbook'],
['Launch / operating test','Not performed','No checkout, supplier payment, stock-sync or test order verified','Saved venture state'],
['Actual venture spending',0,'R0; no purchases, trial activation or wallet funding authorised','Owner instructions'],
['Traffic / conversion / CAC','Unknown','No real customer data; model scenarios only','No observed sales or campaign data'],
['Optional / additional costs','Unquoted','Domain, samples, creative, ads, app upgrades, taxes, refund losses','Set quote or chosen assumption in ROI inputs'],
['AppScenic monthly cancellation','Month end','Monthly cancellation effective end of current billing month','https://appscenic.com/pricing'],
['Sales launch date','Unknown','Requires agreed costs, integration, payments and test fulfilment','Not yet launch-ready']];
e.getRange(`A5:D${rows.length+4}`).values=rows;e.getRange(`A5:D${rows.length+4}`).format.wrapText=true;e.getRange(`A5:D${rows.length+4}`).format.rowHeight=46;
e.getRange('B5:B13').setNumberFormat(money);e.getRange('B16').setNumberFormat('0.0%');e.freezePanes.freezeRows(4);
// Boundary checks with explicit illustrative values, then restore all unknown inputs.
const orig=s.getRange('E6:E34').values;
const example=[25,0,7.21,4.99,0,0.5,0.03,0.3,0.02,0,0.2,1,4,39,25,0,0,100,20,0.01,7,2,0,50,50,1,3,18,30];
s.getRange('E6:E34').values=example.map(x=>[x]);wb.recalculate();
const vals=s.getRange('B26:B50').values.map(x=>x[0]);
if(Math.abs(vals[7]-5.55)>1e-8 || Math.abs(vals[10]-(-30.7))>1e-8 || vals[18]!==12)throw Error('Independent unit / monthly / break-even verification failed: '+JSON.stringify(vals));
s.getRange('E25').values=[[0]];wb.recalculate();if(s.getRange('B35').values[0][0]!==0 || s.getRange('B46').values[0][0]!=='n.a.')throw Error('Zero conversion check failed');
s.getRange('E11').values=[[null]];wb.recalculate();if(s.getRange('B33').values[0][0]!=='n.a.')throw Error('Missing fee guard failed');
s.getRange('E6:E34').values=orig;wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'ROI!A5:B18',include:'values,formulas',tableMaxRows:14,tableMaxCols:2,maxChars:2500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},maxChars:1000})).ndjson);
for(const [name,range,file]of [['ROI','A1:G24','ROI'],['ROI','A25:G56','ROI-detail'],['Evidence','A1:D29','Evidence']]){const p=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(`${out}/${file}.png`,new Uint8Array(await p.arrayBuffer()));}
await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/pet-store-roi.xlsx`);
console.log('Exported ROI workbook; illustrative test inputs restored to blanks.');
