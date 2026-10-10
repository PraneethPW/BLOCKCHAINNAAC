import {Component,Suspense,useRef} from 'react';
import type {ReactNode} from 'react';
import {Canvas,useFrame} from '@react-three/fiber';
import {Float,Environment,Lightformer,RoundedBox,ContactShadows} from '@react-three/drei';
import * as THREE from 'three';
class Boundary extends Component<{children:ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return {failed:true};}render(){return this.state.failed?<div className="scene-fallback"><span>V</span></div>:this.props.children;}}
function Vault({progress,reduced}:{progress:number;reduced:boolean}){
 const ref=useRef<THREE.Group>(null);
 useFrame(({clock,pointer},dt)=>{if(!ref.current)return;const t=reduced?0:clock.elapsedTime;const p=reduced?0:progress;ref.current.rotation.y=THREE.MathUtils.damp(ref.current.rotation.y,-.38+p*2.8+(reduced?0:pointer.x*.12),4,dt);ref.current.rotation.x=THREE.MathUtils.damp(ref.current.rotation.x,.13+p*.3-(reduced?0:pointer.y*.08),4,dt);ref.current.position.y=Math.sin(t*.45)*.09;});
 return <group ref={ref}>
  <RoundedBox args={[2.6,3.05,.55]} radius={.17} smoothness={5}><meshStandardMaterial color="#d6e0d4" metalness={.84} roughness={.25}/></RoundedBox>
  <RoundedBox args={[2.32,2.76,.13]} position={[0,0,.32]} radius={.11} smoothness={5}><meshStandardMaterial color="#202e25" metalness={.8} roughness={.3}/></RoundedBox>
  <RoundedBox args={[2.08,2.5,.055]} position={[0,0,.41]} radius={.08}><meshStandardMaterial color="#596b56" metalness={.8} roughness={.3}/></RoundedBox>
  <mesh position={[0,.14,.54]}><torusGeometry args={[.69,.085,24,64]}/><meshStandardMaterial color="#d6e9c4" metalness={.9} roughness={.18}/></mesh>
  <mesh position={[0,.14,.57]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[.24,.24,.18,48]}/><meshStandardMaterial color="#c9ec97" metalness={.85} roughness={.2}/></mesh>
  {[0,1,2,3].map(i=><mesh key={i} position={[Math.cos(i*Math.PI/2)*.45,.14+Math.sin(i*Math.PI/2)*.45,.6]} rotation={[0,0,i*Math.PI/2]}><boxGeometry args={[.55,.07,.06]}/><meshStandardMaterial color="#e3eedc" metalness={.9} roughness={.18}/></mesh>)}
  {[-1,1].flatMap(x=>[-1,1].map(y=><mesh key={`${x}${y}`} position={[x*.93,y*1.12,.46]}><sphereGeometry args={[.035,16,16]}/><meshStandardMaterial color="#d5efb5" metalness={1} roughness={.1}/></mesh>))}
  <Float speed={reduced?0:1.5} rotationIntensity={.1} floatIntensity={.5}>
   <group position={[-1.7,.55,.7]} rotation={[0,.25,-.15]}><RoundedBox args={[1.07,1.35,.04]} radius={.03}><meshStandardMaterial color="#f5f5e9" roughness={.65}/></RoundedBox>{[0,1,2,3,4].map(i=><mesh key={i} position={[-.04,.36-i*.13,.027]}><boxGeometry args={[i===0?.56:.7,.025,.006]}/><meshBasicMaterial color={i===0?'#63804e':'#b4b8a9'}/></mesh>)}<mesh position={[.21,-.39,.03]}><ringGeometry args={[.1,.115,32]}/><meshBasicMaterial color="#629d37"/></mesh></group>
  </Float>
  <Float speed={reduced?0:2} rotationIntensity={.3} floatIntensity={.5}><group position={[1.5,-.75,.95]} rotation={[.1,-.3,.2]}><RoundedBox args={[.75,.75,.16]} radius={.12}><meshStandardMaterial color="#bef264" metalness={.55} roughness={.22}/></RoundedBox><mesh position={[0,0,.1]} rotation={[0,0,-.25]}><torusGeometry args={[.19,.025,12,32]}/><meshStandardMaterial color="#23391f"/></mesh></group></Float>
 </group>;
}
export default function Scene({progress=0,reduced=false}:{progress?:number;reduced?:boolean}){return <Boundary><Canvas dpr={[1,1.5]} camera={{position:[0,.1,6.4],fov:42}} gl={{alpha:true,antialias:true}}><ambientLight intensity={1.3}/><directionalLight position={[3,5,4]} intensity={4}/><pointLight position={[-3,-1,2]} color="#d9ffb1" intensity={12}/><Suspense fallback={null}><Vault progress={progress} reduced={reduced}/><Environment resolution={128}><Lightformer intensity={3} position={[0,4,2]} scale={[8,3,1]}/><Lightformer intensity={2} position={[-4,1,0]} rotation={[0,Math.PI/2,0]} scale={[4,6,1]}/><Lightformer intensity={2} position={[4,1,1]} rotation={[0,-Math.PI/2,0]} scale={[3,6,1]} color="#c2e697"/></Environment><ContactShadows position={[0,-1.9,0]} opacity={.35} scale={8} blur={2.4} far={4}/></Suspense></Canvas></Boundary>;}
