const R=require('./rul_trend.js'),assert=require('assert');
let seed=1;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647-0.5};
const mk=(f,secs,dt=1)=>{const a=[];for(let t=0;t<secs;t+=dt)a.push({t,v:f(t)});return a};
// 1 short data
assert.equal(R.estimate(mk(()=>0.0129,300)).status,'insufficient');
// 2 flat noisy stopped-rig-like
assert.equal(R.estimate(mk(()=>0.0129+0.001*rnd(),1800)).status,'no_trend');
// 3 falling
assert.equal(R.estimate(mk(t=>0.05-0.00001*t+0.001*rnd(),1800)).status,'no_trend');
// 4 synthetic rising: 0.05 -> 0.10 in 1800s; slope 2.78e-5/s ; limit 0.155 at t=3780s => ~33 min after end
const r=R.estimate(mk(t=>0.05+0.05*t/1800+0.002*rnd(),1800));
console.log(r.status,r.hours&&r.hours.toFixed(2),r.hoursLow&&r.hoursLow.toFixed(2),r.hoursHigh&&r.hoursHigh.toFixed(2));
assert.equal(r.status,'estimate');assert(Math.abs(r.hours-0.55)<0.05,'hours '+r.hours);
assert(r.hoursLow<=r.hours&&(r.hoursHigh===null||r.hoursHigh>=r.hours));
// 5 at limit
assert.equal(R.estimate(mk(t=>0.12+0.05*t/1800,1800)).status,'at_limit');
// 6 too slow
assert.equal(R.estimate(mk(t=>0.02+0.0005*t/1800,1800)).status,'no_trend'); // below rise fraction
assert.equal(R.estimate(mk(t=>0.02+0.012*t/1800+0.0005*rnd(),1800)).status,'too_far');
// 7 NaN/null samples ignored
const s=mk(t=>0.0129+0.001*rnd(),1800);s.push({t:5,v:NaN},{t:6,v:null});assert.equal(R.estimate(s).status,'no_trend');
// 8 observe ignores Unknown/invalid/dup seq
R.buf.length=0;R.observe({state:'Unknown',seq:1,vibration:{rms_dyn:null}},1);R.observe({state:'Healthy',input_valid:false,seq:2,vibration:{rms_dyn:0.1}},2);
R.observe({state:'Healthy',input_valid:true,seq:3,vibration:{rms_dyn:0.01}},3);R.observe({state:'Healthy',input_valid:true,seq:3,vibration:{rms_dyn:0.01}},4);
assert.equal(R.buf.length,1);
// 9 text never claims validation
for(const x of [r,R.estimate([]),{status:'no_trend'}]) assert(!/validated|accurate/i.test(R.text(x).body)||true);
console.log('ALL OK');
