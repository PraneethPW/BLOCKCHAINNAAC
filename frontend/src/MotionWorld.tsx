import {Component,Suspense,useEffect,useRef,useState} from 'react';
import type {ReactNode} from 'react';
import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {Environment,Lightformer,RoundedBox} from '@react-three/drei';
import * as THREE from 'three';
import gsap from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
gsap.registerPlugin(ScrollTrigger);

class Boundary extends Component<{children:ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return {failed:true};}render(){return this.state.failed?<div className="world-fallback"/>:this.props.children;}}
function Geometry({reduced,mode}:{reduced:boolean;mode:string}){
 const root=useRef<THREE.Group>(null),rings=useRef<THREE.Group>(null),paper=useRef<THREE.Group>(null);
 const {camera}=useThree();const path=useRef({orbit:0,x:0,y:0,z:8});
 useEffect(()=>{
   if(reduced)return;
   const ctx=gsap.context(()=>{gsap.timeline({scrollTrigger:{trigger:document.documentElement,start:'top top',end:'bottom bottom',scrub:1.3}})
    .to(path.current,{orbit:1.5,x:1.1,y:.5,z:7,duration:1,ease:'none'})
    .to(path.current,{orbit:3.2,x:-.7,y:-.4,z:8.5,duration:1,ease:'none'})
    .to(path.current,{orbit:5.1,x:.3,y:.7,z:7.5,duration:1,ease:'none'});});
   ScrollTrigger.refresh();return()=>ctx.revert();
 },[reduced,mode]);
 useFrame(({clock,pointer},dt)=>{
   if(!root.current||!rings.current||!paper.current)return;
   const t=reduced?0:clock.elapsedTime;const p=path.current;
   camera.position.set(p.x,p.y,p.z);camera.lookAt(0,0,0);
   root.current.rotation.y=THREE.MathUtils.damp(root.current.rotation.y,-.45+p.orbit+(reduced?0:pointer.x*.16),3,dt);
   root.current.rotation.x=THREE.MathUtils.damp(root.current.rotation.x,.25+(reduced?0:pointer.y*.1),3,dt);
   root.current.position.x=mode==='landing'?1.65:mode==='auth'?-1.9:1.9;
   root.current.position.y=Math.sin(t*.35)*.12;
   rings.current.rotation.z=t*.07+p.orbit*.25;paper.current.rotation.y=Math.sin(t*.45)*.12;
 });
 const points=new Float32Array(Array.from({length:720},(_,i)=>Math.sin(i*91.73)*(i%3===2?5:11)));
 return <><group ref={root} scale={mode==='workspace'?.78:1}>
   <group rotation={[0,0,-.12]}>
    <RoundedBox args={[2.25,2.8,.38]} radius={.15} smoothness={4}><meshPhysicalMaterial color="#98c9ff" metalness={.78} roughness={.18} clearcoat={1}/></RoundedBox>
    <RoundedBox args={[2.06,2.61,.09]} position={[0,0,.23]} radius={.12}><meshStandardMaterial color="#0c152b" metalness={.65} roughness={.24}/></RoundedBox>
    <group ref={paper} position={[0,0,.37]}>
     <RoundedBox args={[1.68,2.14,.035]} radius={.05}><meshStandardMaterial color="#bddeef" metalness={.5} roughness={.23}/></RoundedBox>
     {[0,1,2,3,4].map(i=><mesh key={i} position={[-.13,.6-i*.18,.028]}><boxGeometry args={[i===0?.78:1.07,.028,.007]}/><meshBasicMaterial color={i===0?'#1760ac':'#5587a6'}/></mesh>)}
     <mesh position={[.36,-.7,.033]}><ringGeometry args={[.14,.165,40]}/><meshBasicMaterial color="#167ca8"/></mesh>
    </group>
    <mesh position={[.75,.97,.31]}><sphereGeometry args={[.03,12,12]}/><meshBasicMaterial color="#a8f2ff"/></mesh>
   </group>
   <group ref={rings} rotation={[.55,.2,0]}>
    {[0,1,2].map(i=><mesh key={i} rotation={[i*.55,i*.7,.3]}><torusGeometry args={[2.05+i*.35,.014,8,100]}/><meshBasicMaterial color={i===1?'#4f75ff':'#8be6ff'} transparent opacity={i===2?.32:.8}/></mesh>)}
    {[0,1,2,3].map(i=><group key={i} position={[Math.cos(i*1.57)*2.5,Math.sin(i*1.57)*2.5,.5]} rotation={[.3,.4,i*.4]}><RoundedBox args={[.46,.46,.46]} radius={.05}><meshPhysicalMaterial color="#3e67d4" metalness={.85} roughness={.14}/></RoundedBox><mesh><boxGeometry args={[.5,.5,.5]}/><meshBasicMaterial wireframe color="#88e7ff" transparent opacity={.4}/></mesh></group>)}
   </group>
  </group><points><bufferGeometry><bufferAttribute attach="attributes-position" args={[points,3]}/></bufferGeometry><pointsMaterial size={.013} color="#7faccb" transparent opacity={.6} sizeAttenuation/></points></>;
}
export default function MotionWorld({mode='landing',reduced=false}:{mode?:string;reduced?:boolean}){
 const [visible,setVisible]=useState(!document.hidden);
 useEffect(()=>{const listener=()=>setVisible(!document.hidden);document.addEventListener('visibilitychange',listener);return()=>document.removeEventListener('visibilitychange',listener);},[]);
 return <div className={`motion-world world-${mode}`} aria-hidden="true"><Boundary><Canvas frameloop={reduced||!visible?'demand':'always'} eventSource={document.body} eventPrefix="client" dpr={[1,1.35]} camera={{position:[0,0,8],fov:44}} gl={{alpha:true,antialias:true,powerPreference:'low-power'}}><ambientLight intensity={1.5}/><directionalLight position={[3,5,6]} intensity={4}/><pointLight position={[-4,1,3]} color="#5480ff" intensity={18}/><Suspense fallback={null}><Geometry reduced={reduced} mode={mode}/><Environment resolution={64}><Lightformer intensity={3} position={[0,4,3]} scale={[8,2,1]}/><Lightformer intensity={2} position={[-4,0,1]} rotation={[0,Math.PI/2,0]} scale={[5,6,1]}/></Environment></Suspense></Canvas></Boundary></div>;
}
