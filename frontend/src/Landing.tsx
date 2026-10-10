import {lazy,Suspense,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {motion,useScroll} from 'framer-motion';
import {ArrowUpRight,ArrowDown,Layers3,Fingerprint,Globe2,ShieldCheck,Plus,Minus,Link2,FileCheck2} from 'lucide-react';
import gsap from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
import {api} from './api';
import './landing.css';

const LivingBackground=lazy(()=>import('./LivingBackground'));
gsap.registerPlugin(ScrollTrigger);
export function Brand({onClick}:{onClick:()=>void}){return <button className="brand" onClick={onClick} aria-label="Veris home"><span className="brand-mark"><Layers3 size={24}/></span><span>veris<span className="brand-dot">.</span></span></button>;}
const questions=[
 ['What does Genuine mean?','An exact match to an independently retrieved publisher original or a registered issuer original. It verifies that file, not a college’s ownership of its claims.'],
 ['What does blockchain preserve?','Supported confirmed findings and linked appeals. Evidence stays private; hashes and decision records make later changes detectable.'],
 ['What happens when evidence is incomplete?','The completed assessment remains Neutral. Missing records never become an invented genuine or fake verdict.'],
];
const steps=[
 {title:'Keep the original',label:'Original file',icon:Fingerprint,description:'The exact uploaded bytes receive a SHA-256 fingerprint. Structural checks identify corruption and document-level anomalies.',detail:'File fingerprint · PDF integrity · Metadata'},
 {title:'Connect the evidence',label:'Source comparison',icon:Globe2,description:'Compare available issuer originals and retrieve independent public records. Every finding stays linked to its supporting source.',detail:'Issuer originals · Public records · Claim consistency'},
 {title:'Preserve the finding',label:'Audit record',icon:ShieldCheck,description:'Confirmed findings and linked appeals are anchored to the blockchain. Original documents and supporting evidence stay private.',detail:'Decision hash · Evidence links · Blockchain receipt'},
];
function WorkflowGraphic({step}:{step:number}){
 return <div className={'flow-visual flow-step-'+step} aria-hidden="true">
  <div className="flow-halo"/><svg viewBox="0 0 600 420" className="flow-diagram">
   <defs><linearGradient id="flow-paper" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#254e81" stopOpacity=".72"/><stop offset="1" stopColor="#0b1c34" stopOpacity=".92"/></linearGradient><linearGradient id="flow-edge"><stop stopColor="#77e1ff"/><stop offset="1" stopColor="#6588ff" stopOpacity=".15"/></linearGradient><linearGradient id="flow-scan" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#70ddff" stopOpacity="0"/><stop offset="1" stopColor="#70ddff" stopOpacity=".36"/></linearGradient><clipPath id="flow-clip"><path d="M155 118 320 80 458 153 293 195 155 118V296L293 373 458 326V153"/></clipPath></defs>
   <g className="flow-wires" fill="none" stroke="#73b9ff" strokeWidth="1"><path d="M75 178 155 215M458 205 533 159M310 330V390"/><path d="M75 178V100H230M533 159V280H458" strokeDasharray="3 7" opacity=".4"/></g>
   <g className="flow-sheet flow-sheet-back"><path d="M158 149 322 109 455 183V354L290 397 158 321Z" fill="#101f35" stroke="#4c739d" strokeOpacity=".4"/></g>
   <g className="flow-sheet flow-sheet-middle"><path d="M158 130 322 90 455 164V335L290 378 158 302Z" fill="#14283f" stroke="#5f99c5" strokeOpacity=".5"/></g>
   <g className="flow-sheet flow-sheet-front"><path d="M155 111 320 72 458 149V314L293 359 155 282Z" fill="url(#flow-paper)" stroke="url(#flow-edge)" strokeWidth="1.5"/><path d="M155 111 293 185 458 149M293 185V359" fill="none" stroke="#89d1ff" strokeOpacity=".2"/>
    <path d="M183 156 250 192M183 175 266 220M183 194 250 231M183 230 261 272M183 247 237 277" fill="none" stroke="#a2d6f1" strokeOpacity=".4" strokeWidth="3"/>
    <path d="M318 211 426 184M318 232 426 204M318 253 392 235" fill="none" stroke="#9ac6f1" strokeOpacity=".5" strokeWidth="2"/>
    <g clipPath="url(#flow-clip)"><rect className="flow-scan" x="145" y="120" width="330" height="58" fill="url(#flow-scan)"/></g>
   </g>
   <g className="flow-nodes"><circle cx="75" cy="178" r="23" fill="#0d2039" stroke="#639ccb"/><path d="M68 178h14M75 171v14" stroke="#99dfff"/><circle cx="533" cy="159" r="23" fill="#0d2039" stroke="#639ccb"/><path d="m524 159 6 6 11-12" fill="none" stroke="#99dfff" strokeWidth="2"/><circle cx="310" cy="390" r="11" fill="#7cbdff" fillOpacity=".16" stroke="#7cbdff"/></g>
  </svg><span className="flow-label flow-label-original">FILE INTEGRITY</span><span className="flow-label flow-label-source">INDEPENDENT SOURCES</span><span className="flow-label flow-label-record">CONNECTED RECORD</span>
 </div>;
}
export default function Landing({navigate,signedIn,reduced}:{navigate:(path:string)=>void;signedIn:boolean;reduced:boolean}){
 const root=useRef<HTMLElement>(null),signal=useRef({progress:0,pointerX:0,pointerY:0});
 const [faq,setFaq]=useState<number|null>(null),[step,setStep]=useState(0),[health,setHealth]=useState<'checking'|'online'|'unavailable'>('checking');
 const {scrollYProgress}=useScroll();const workspace=()=>navigate(signedIn?'/workspace':'/register');
 useEffect(()=>{let active=true;const check=()=>api<{status:string}>('/health').then(v=>{if(active)setHealth(v.status==='ok'?'online':'unavailable');}).catch(()=>{if(active)setHealth('unavailable');});void check();const interval=setInterval(check,30000);return()=>{active=false;clearInterval(interval);};},[]);
 useLayoutEffect(()=>{
  if(reduced||!root.current)return;
  const ctx=gsap.context(()=>{
   gsap.to(signal.current,{progress:1,ease:'none',scrollTrigger:{trigger:root.current,start:'top top',end:'bottom bottom',scrub:1,invalidateOnRefresh:true}});
   gsap.utils.toArray<HTMLElement>('[data-reveal]').forEach(el=>gsap.fromTo(el,{y:32},{y:0,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 95%',end:'top 65%',scrub:1}}));
   gsap.fromTo('.living-hero-art',{y:0,rotate:-5},{y:85,rotate:3,ease:'none',scrollTrigger:{trigger:'.living-hero',start:'top top',end:'bottom top',scrub:1}});
  },root);let active=true;document.fonts.ready.then(()=>{if(active)ScrollTrigger.refresh();});return()=>{active=false;ctx.revert();};
 },[reduced]);
 useEffect(()=>{if(reduced||!matchMedia('(pointer:fine)').matches)return;const move=(e:PointerEvent)=>{signal.current.pointerX=e.clientX/innerWidth-.5;signal.current.pointerY=.5-e.clientY/innerHeight;};const reset=()=>{signal.current.pointerX=0;signal.current.pointerY=0;};window.addEventListener('pointermove',move,{passive:true});document.addEventListener('pointerleave',reset);return()=>{window.removeEventListener('pointermove',move);document.removeEventListener('pointerleave',reset);reset();};},[reduced]);
 const StageIcon=steps[step].icon;
 return <main ref={root} className={'living-landing '+(reduced?'living-reduced':'')}>
  <div className="living-environment" aria-hidden="true"><picture className="living-poster"><source media="(max-width:700px)" srcSet="/images/atrium-960.webp"/><img src="/images/atrium-1920.webp" alt="" width="1920" height="1080" fetchPriority="high"/></picture>{!reduced&&<Suspense fallback={null}><LivingBackground signal={signal}/></Suspense>}<div className="living-scrim"/><div className="living-grain"/></div>
  <motion.div className="living-progress" style={{scaleX:scrollYProgress}} aria-hidden="true"/>
  <nav className="living-nav" aria-label="Main navigation"><Brand onClick={()=>navigate('/')}/><div className="living-nav-actions"><button className="living-signin" onClick={()=>navigate(signedIn?'/workspace':'/login')}>{signedIn?'Workspace':'Sign in'}<ArrowUpRight size={16} aria-hidden="true"/></button><button className="living-button living-nav-cta" onClick={workspace}>{signedIn?'Open workspace':'Get started'}<ArrowUpRight size={16} aria-hidden="true"/></button></div></nav>
  <div className="living-content">
   <section id="main-content" tabIndex={-1} className="living-hero living-container" aria-labelledby="living-title">
    <div className="living-hero-copy"><span className="living-eyebrow"><span className="living-signal"/> ACCREDITATION, WITH EVIDENCE</span><h1 id="living-title">See the proof.<br/><span className="living-gradient">Trust the trail.</span></h1><p>Bring your documents, sources, and decisions into one connected verification workspace.</p><div className="living-hero-actions"><button className="living-button" onClick={workspace}>Start verifying<ArrowUpRight size={20} aria-hidden="true"/></button><a className="living-text-link" href="#platform">Explore the platform<ArrowDown size={16} aria-hidden="true"/></a></div><span className="living-hero-note"><ShieldCheck size={14} aria-hidden="true"/>Private evidence. Traceable decisions.</span></div>
    <div className="living-hero-art" aria-hidden="true"><div className="living-art-grid"/><div className="living-art-mark"><Fingerprint size={76} strokeWidth={.8}/><span>THE EVIDENCE<br/>IS CONNECTED.</span></div><div className="living-art-tag tag-original"><span/><Fingerprint size={17}/>Original file</div><div className="living-art-tag tag-source"><span/><Globe2 size={17}/>Independent sources</div><div className="living-art-tag tag-record"><span/><Link2 size={17}/>Immutable record</div><svg className="living-art-path" viewBox="0 0 500 500"><path d="M88 150C320 22 452 158 388 295S218 492 112 348 268 162 370 314"/></svg></div>
    <div className="living-hero-bottom"><span>BUILT FOR INSTITUTIONAL EVIDENCE</span><div><span>File integrity</span><i/><span>Source comparison</span><i/><span>Blockchain audit</span></div></div>
   </section>
   <section id="platform" className="living-platform living-container" aria-labelledby="platform-title">
    <div className="living-section-heading" data-reveal><div><span className="living-eyebrow">A CLEARER STANDARD</span><h2 id="platform-title">Built for evidence.<br/><span>Designed for clarity.</span></h2></div><p>Go beyond a file check. Understand the original, follow its sources, and preserve what the evidence supports.</p></div>
    <div className="living-capabilities">{[{icon:Fingerprint,title:'Inspect the original',copy:'Fingerprint exact bytes. Examine PDF structure, signatures, and signs of alteration.'},{icon:Globe2,title:'Trace the source',copy:'Compare available issuer files and public records with source-linked findings.'},{icon:ShieldCheck,title:'Protect the record',copy:'Anchor supported confirmed findings to the blockchain without exposing private files.'}].map(({icon:Icon,title,copy},i)=><article className="living-capability" data-reveal key={title}><div className="living-capability-top"><Icon size={26} strokeWidth={1.3} aria-hidden="true"/><span>0{i+1}</span></div><h3>{title}</h3><p>{copy}</p><div className="living-card-ray" aria-hidden="true"/></article>)}</div>
   </section>
   <section className="living-workflow living-container" aria-labelledby="workflow-title">
    <div className="living-workflow-copy" data-reveal><span className="living-eyebrow">ONE CONNECTED WORKFLOW</span><h2 id="workflow-title">From upload<br/><span>to an audit trail.</span></h2><div className="living-step-tabs" role="tablist" aria-label="Verification workflow">{steps.map((s,i)=><button key={s.title} id={'workflow-tab-'+i} role="tab" aria-selected={step===i} aria-controls="workflow-panel" tabIndex={step===i?0:-1} onClick={()=>setStep(i)} onKeyDown={e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;setStep(next);document.getElementById('workflow-tab-'+next)?.focus();}}}><span>0{i+1}</span>{s.label}</button>)}</div><div id="workflow-panel" role="tabpanel" aria-labelledby={'workflow-tab-'+step} tabIndex={0}><h3>{steps[step].title}</h3><p>{steps[step].description}</p><small>{steps[step].detail}</small></div></div>
    <div className="living-workflow-art" data-reveal><WorkflowGraphic step={step}/><div className="living-workflow-caption"><StageIcon size={18} aria-hidden="true"/><span>{steps[step].label}</span><span className="living-caption-line"/></div></div>
   </section>
   <section className="living-record living-container" aria-labelledby="record-title"><div className="living-record-light" aria-hidden="true"/><div data-reveal><span className="living-eyebrow"><Link2 size={14} aria-hidden="true"/> EVIDENCE MEETS ACCOUNTABILITY</span><h2 id="record-title">A decision today.<br/><span className="living-gradient">A record that lasts.</span></h2><p>Keep the original, the findings, and the history connected.</p><button className="living-button" onClick={workspace}>Open your workspace<ArrowUpRight size={20} aria-hidden="true"/></button></div><div className="living-record-footer"><span><FileCheck2 size={16} aria-hidden="true"/>Evidence stays private</span><span><Layers3 size={16} aria-hidden="true"/>Confirmed findings stay traceable</span></div></section>
   <section className="living-questions living-container" aria-labelledby="questions-title"><div><span className="living-eyebrow">CLEAR BY DESIGN</span><h2 id="questions-title">Trust starts<br/><span>with clarity.</span></h2></div><div>{questions.map(([q,a],i)=><div className="living-question" key={q}><button aria-expanded={faq===i} aria-controls={'living-answer-'+i} onClick={()=>setFaq(faq===i?null:i)}>{q}{faq===i?<Minus size={18} aria-hidden="true"/>:<Plus size={18} aria-hidden="true"/>}</button><div id={'living-answer-'+i} hidden={faq!==i}><p>{a}</p></div></div>)}</div></section>
   <footer className="living-footer living-container"><Brand onClick={()=>navigate('/')}/><p>Independent prototype. No NAAC affiliation.<br/>No accreditation grades.</p><div className={'living-service '+health}><span/><small>{health==='online'?'API connected':health==='checking'?'Connecting to API':'API unavailable'}</small></div><span>© {new Date().getFullYear()} Veris</span></footer>
  </div>
 </main>;
}
