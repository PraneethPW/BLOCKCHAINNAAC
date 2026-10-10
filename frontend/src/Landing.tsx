import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {motion,useScroll,useTransform} from 'framer-motion';
import {ArrowUpRight,ArrowDown,Layers3,Pause,Play,Plus,Minus} from 'lucide-react';
import gsap from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
import {api} from './api';
import './landing.css';

gsap.registerPlugin(ScrollTrigger);
export function Brand({onClick}:{onClick:()=>void}){return <button className="brand" onClick={onClick} aria-label="Veris home"><span className="brand-mark"><Layers3 size={24}/></span><span>veris<span className="brand-dot">.</span></span></button>;}
const questions=[
 ['What does Genuine mean?','An exact match to an independently retrieved publisher original or a registered issuer original. It verifies that file, not a college’s ownership of its claims.'],
 ['What does blockchain preserve?','Supported confirmed findings and linked appeals. Evidence stays private; hashes and decision records make later changes detectable.'],
 ['What happens when evidence is incomplete?','The completed assessment remains Neutral. Missing records never become an invented genuine or fake verdict.'],
];
function SceneImage({name,priority=false,onLoad}:{name:string;priority?:boolean;onLoad?:()=>void}){
 return <picture><source media="(max-width:700px)" srcSet={'/images/'+name+'-960.webp'}/><img src={'/images/'+name+'-1920.webp'} srcSet={'/images/'+name+'-1920.webp 1920w, /images/'+name+'-2560.webp 2560w'} sizes="100vw" alt="" aria-hidden="true" width="2560" height="1440" loading={priority?'eager':'lazy'} fetchPriority={priority?'high':'auto'} decoding="async" onLoad={onLoad}/></picture>;
}
export default function Landing({navigate,signedIn,reduced,onMotion,motionLocked=false}:{navigate:(path:string)=>void;signedIn:boolean;reduced:boolean;onMotion:()=>void;motionLocked?:boolean}){
 const root=useRef<HTMLElement>(null),hero=useRef<HTMLElement>(null),camera=useRef<HTMLDivElement>(null),journey=useRef<HTMLDivElement>(null);
 const [faq,setFaq]=useState<number|null>(null),[health,setHealth]=useState<'checking'|'online'|'unavailable'>('checking'),[imageReady,setImageReady]=useState(false);
 const {scrollYProgress}=useScroll();
 const {scrollYProgress:heroProgress}=useScroll({target:hero,offset:['start start','end start']});
 const imageY=useTransform(heroProgress,[0,1],['0%','22%']);
 const heroOpacity=useTransform(heroProgress,[0,.55,.95],[1,1,0]);
 const workspace=()=>navigate(signedIn?'/workspace':'/register');
 useEffect(()=>{let active=true;const check=()=>api<{status:string}>('/health').then(v=>{if(active)setHealth(v.status==='ok'?'online':'unavailable');}).catch(()=>{if(active)setHealth('unavailable');});void check();const interval=setInterval(check,30000);return()=>{active=false;clearInterval(interval);};},[]);
 useLayoutEffect(()=>{
  if(reduced||!root.current||!journey.current)return;
  const ctx=gsap.context(()=>{
   gsap.timeline({scrollTrigger:{trigger:journey.current,start:'top top',end:'bottom bottom',scrub:.8,invalidateOnRefresh:true}})
    .fromTo('.cine-source-camera',{scale:1.06,yPercent:0},{scale:1.22,yPercent:-5,duration:1,ease:'none'},0)
    .fromTo('.cine-vault-scene',{clipPath:'inset(0 0 0 100%)'},{clipPath:'inset(0 0 0 0%)',duration:.24,ease:'power1.inOut'},.43)
    .fromTo('.cine-vault-camera',{scale:1.14,yPercent:5},{scale:1.03,yPercent:-2,duration:.57,ease:'none'},.43);
   gsap.utils.toArray<HTMLElement>('.cine-chapter-copy').forEach(el=>gsap.fromTo(el,{y:45,opacity:.2},{y:0,opacity:1,ease:'none',scrollTrigger:{trigger:el,start:'top 90%',end:'top 48%',scrub:.7}}));
  },root);
  let active=true;document.fonts.ready.then(()=>{if(active)ScrollTrigger.refresh();});
  return()=>{active=false;ctx.revert();};
 },[reduced]);
 useEffect(()=>{
  const target=camera.current;if(reduced||!target||!matchMedia('(pointer:fine)').matches)return;
  const x=gsap.quickTo(target,'x',{duration:1,ease:'power2.out'}),y=gsap.quickTo(target,'y',{duration:1,ease:'power2.out'}),tilt=gsap.quickTo(target,'rotationY',{duration:1,ease:'power2.out'});
  const move=(e:PointerEvent)=>{if(document.hidden)return;const px=e.clientX/window.innerWidth-.5,py=e.clientY/window.innerHeight-.5;x(px*-20);y(py*-14);tilt(px*.8);};
  const reset=()=>{x(0);y(0);tilt(0);};const element=hero.current;
  element?.addEventListener('pointermove',move);element?.addEventListener('pointerleave',reset);
  return()=>{element?.removeEventListener('pointermove',move);element?.removeEventListener('pointerleave',reset);gsap.killTweensOf(target);gsap.set(target,{clearProps:'transform'});};
 },[reduced]);
 return <main ref={root} className={'cinematic-landing '+(reduced?'cine-reduced':'')}>
  <motion.div className="cine-progress" style={{scaleX:scrollYProgress}} aria-hidden="true"/>
  <nav className="cine-nav" aria-label="Main navigation"><Brand onClick={()=>navigate('/')}/><a className="cine-journey-link" href="#verification">Follow the evidence</a><div className="cine-nav-actions"><button className="cine-motion" aria-label={motionLocked?'Motion reduced by your device':reduced?'Enable motion':'Reduce motion'} title={motionLocked?'Your device requests reduced motion':reduced?'Enable motion':'Reduce motion'} disabled={motionLocked} aria-pressed={reduced} onClick={onMotion}>{reduced?<Play size={16}/>:<Pause size={16}/>}</button><button className="cine-signin" onClick={()=>navigate(signedIn?'/workspace':'/login')}>{signedIn?'Workspace':'Sign in'}<ArrowUpRight size={16}/></button><button className="cine-button cine-nav-cta" onClick={workspace}>{signedIn?'Open workspace':'Get started'}<ArrowUpRight size={16}/></button></div></nav>
  <section ref={hero} id="main-content" tabIndex={-1} className={'cine-hero '+(imageReady?'image-ready':'')} aria-labelledby="cine-title">
   <motion.div className="cine-hero-visual" style={{y:reduced?'0%':imageY}} aria-hidden="true"><div ref={camera} className="cine-camera"><div className="cine-image-drift"><SceneImage name="atrium" priority onLoad={()=>{setImageReady(true);ScrollTrigger.refresh();}}/></div></div></motion.div>
   <div className="cine-hero-shade" aria-hidden="true"/><div className="cine-grain" aria-hidden="true"/>
   <motion.div className="cine-hero-copy" style={{opacity:reduced?1:heroOpacity}} initial={{y:reduced?0:20}} animate={{y:0}} transition={{duration:.9,ease:[.22,1,.36,1]}}>
    <span className="cine-kicker"><span/> ACCREDITATION EVIDENCE, CONNECTED</span><h1 id="cine-title">Truth has<br/><span>a trace.</span></h1><p>Follow the original.<br/>Find the evidence. Preserve the decision.</p><button className="cine-button" onClick={workspace}>Explore your evidence<ArrowUpRight size={20}/></button>
   </motion.div>
   <div className="cine-hero-footer"><a href="#verification" className="cine-scroll"><span className="cine-scroll-icon"><ArrowDown size={16}/></span><span>SCROLL TO FOLLOW THE TRACE</span></a><div className="cine-scene-caption"><span>01 / THE ORIGINAL</span><small>Evidence starts with the file.</small></div></div><div className="cine-side-note" aria-hidden="true">VERIS / A CLEARER STANDARD</div>
  </section>
  <div ref={journey} id="verification" className="cine-journey">
   <div className="cine-stage" aria-hidden="true"><div className="cine-scene cine-source-scene"><div className="cine-source-camera"><SceneImage name="trace" onLoad={()=>ScrollTrigger.refresh()}/></div></div><div className="cine-scene cine-vault-scene"><div className="cine-vault-camera"><SceneImage name="vault" onLoad={()=>ScrollTrigger.refresh()}/></div></div><div className="cine-stage-shade"/><div className="cine-grain"/></div>
   <div className="cine-chapters">
    <section className="cine-chapter" aria-labelledby="cine-source-title"><div className="cine-chapter-copy"><span className="cine-kicker">02 / THE SOURCE</span><h2 id="cine-source-title">Look closer.<br/><span>Go further.</span></h2><p>Compare original files.<br/>Trace independent sources.<br/>See what the evidence establishes.</p><div className="cine-methods"><span>FILE INTEGRITY</span><span>ISSUER COMPARISON</span><span>PUBLIC RECORDS</span></div></div><span className="cine-chapter-marker" aria-hidden="true">02</span></section>
    <section id="integrity" className="cine-chapter cine-last-chapter" aria-labelledby="cine-record-title"><div className="cine-chapter-copy"><span className="cine-kicker">03 / THE RECORD</span><h2 id="cine-record-title">Every decision.<br/><span>A lasting record.</span></h2><p>Confirmed findings are sealed on-chain.<br/>The evidence stays private.<br/>The history stays connected.</p><button className="cine-button" onClick={workspace}>Open your workspace<ArrowUpRight size={20}/></button></div><span className="cine-chapter-marker" aria-hidden="true">03</span></section>
   </div>
  </div>
  <section id="boundaries" className="cine-boundaries"><div><span className="cine-kicker">CLARITY IS PART OF TRUST</span><h2>Know what<br/>the evidence means.</h2></div><div className="cine-questions">{questions.map(([q,a],i)=><div className="cine-question" key={q}><button aria-expanded={faq===i} aria-controls={'cine-answer-'+i} onClick={()=>setFaq(faq===i?null:i)}>{q}{faq===i?<Minus size={19}/>:<Plus size={19}/>}</button>{faq===i&&<p id={'cine-answer-'+i}>{a}</p>}</div>)}</div></section>
  <footer className="cine-footer"><Brand onClick={()=>navigate('/')}/><p>Independent prototype. No NAAC affiliation.<br/>No accreditation grades.</p><div className={'cine-service '+health}><span/><small>{health==='online'?'API connected':health==='checking'?'Connecting to API':'API unavailable'}</small></div><span>© {new Date().getFullYear()} VERIS</span></footer>
 </main>;
}
