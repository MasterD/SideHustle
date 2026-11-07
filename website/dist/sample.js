'use strict';
const sampleSales = [
  {id:'DEMO-001',date:'2026-09-21',client:'Agency Alpha',cents:350000},
  {id:'DEMO-002',date:'2026-09-23',client:'Agency Beta',cents:420000},
  {id:'DEMO-003',date:'2026-09-25',client:'Agency Alpha',cents:210000},
  {id:'DEMO-004',date:'2026-09-27',client:'Agency Gamma',cents:250000},
  {id:'DEMO-005',date:'2026-09-28',client:'Agency Beta',cents:110000}
];
const sampleInvoices = [
  {client:'Agency Alpha',due:'2026-09-15',amount:350000,paid:150000},
  {client:'Agency Beta',due:'2026-09-20',amount:420000,paid:220000},
  {client:'Agency Gamma',due:'2026-10-06',amount:250000,paid:0},
  {client:'Agency Delta',due:'2026-09-24',amount:100000,paid:100000}
];
const sampleMoney = cents => new Intl.NumberFormat('en-ZA',{style:'currency',currency:'ZAR'}).format(cents/100);
function sampleCell(text, numeric=false){const td=document.createElement('td');td.textContent=text;if(numeric)td.className='number';return td;}
function renderSample(){
  const end=document.querySelector('#period').value==='all'?'2026-09-28':'2026-09-27';
  const sales=sampleSales.filter(row=>row.date>='2026-09-21'&&row.date<=end);
  document.querySelector('#sales').textContent=sampleMoney(sales.reduce((total,row)=>total+row.cents,0));
  document.querySelector('#transactions').textContent=String(sales.length);
  document.querySelector('#outstanding').textContent=sampleMoney(sampleInvoices.reduce((total,row)=>total+row.amount-row.paid,0));
  document.querySelector('#overdue').textContent=sampleMoney(sampleInvoices.filter(row=>row.due<'2026-09-28').reduce((total,row)=>total+row.amount-row.paid,0));
  const grouped=new Map();sales.forEach(row=>grouped.set(row.client,(grouped.get(row.client)||0)+row.cents));
  document.querySelector('#clients').replaceChildren(...Array.from(grouped,([client,cents])=>{const tr=document.createElement('tr');tr.append(sampleCell(client),sampleCell(sampleMoney(cents),true));return tr;}));
  document.querySelector('#invoices').replaceChildren(...sampleInvoices.map(row=>{const tr=document.createElement('tr');const balance=row.amount-row.paid;tr.append(sampleCell(row.client),sampleCell(row.due),sampleCell(sampleMoney(balance),true),sampleCell(balance===0?'Paid':row.due<'2026-09-28'?'Overdue':'Not yet due'));return tr;}));
}
document.querySelector('#period').addEventListener('change',renderSample);renderSample();
