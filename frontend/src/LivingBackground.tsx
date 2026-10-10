import {Component,Suspense,useEffect,useMemo,useRef,useState} from 'react';
import type {ReactNode,RefObject} from 'react';
import {Canvas,useFrame,useLoader,useThree} from '@react-three/fiber';
import {MathUtils,ShaderMaterial,TextureLoader,Vector2} from 'three';

type Signal=RefObject<{progress:number;pointerX:number;pointerY:number}>;
class BackgroundBoundary extends Component<{children:ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return{failed:true};}render(){return this.state.failed?null:this.props.children;}}
const vertexShader=`varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}`;
const fragmentShader=`
 precision highp float;
 varying vec2 vUv;
 uniform sampler2D uOriginal; uniform sampler2D uSource; uniform sampler2D uRecord;
 uniform float uTime; uniform float uProgress; uniform vec2 uSize; uniform vec2 uPointer;
 float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
 float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);}
 vec2 cover(vec2 uv){float a=uSize.x/uSize.y;float image=1.777;vec2 fit=vec2(min(a/image,1.),min(image/a,1.));return (uv-.5)*fit+.5;}
 void main(){
  float t=uTime;float p=uProgress;vec2 uv=vUv;float aspect=uSize.x/uSize.y;
  vec2 offset=uPointer*.014+vec2(sin(t*.09)*.004,cos(t*.07)*.004);
  float drift=noise(uv*3.+vec2(t*.018,p*1.5));
  vec2 sceneUv=cover((uv-.5)/(1.05+p*.14)+.5+offset+vec2(drift*.004));
  vec3 a=texture2D(uOriginal,sceneUv).rgb;
  vec3 b=texture2D(uSource,sceneUv+vec2(p*.012,0)).rgb;
  vec3 c=texture2D(uRecord,sceneUv).rgb;
  vec3 art=mix(mix(a,b,smoothstep(.06,.39,p)),c,smoothstep(.43,.75,p));
  float luminance=dot(art,vec3(.2126,.7152,.0722));
  vec3 colour=mix(vec3(.012,.027,.062),vec3(.19,.36,.52)*luminance,.78);
  colour+=art*vec3(.025,.05,.085);
  float right=smoothstep(.12,.92,uv.x);
  colour*=.45+right*.55;
  vec2 field=vec2(uv.x*aspect,uv.y);
  float mist=noise(field*2.+vec2(t*.035,-t*.022));
  float glow=exp(-length((uv-vec2(.73+sin(t*.08)*.07,.48)) *vec2(1.,1.5))*3.8);
  colour+=vec3(.015,.085,.21)*glow*(.6+mist*.6);
  for(int i=0;i<9;i++){
   float j=float(i);float x=uv.x;
   float curve=.14+x*.72+sin(x*5.4+t*.15+j*.055+p*3.)*.15+j*.012;
   float distanceToLine=abs(uv.y-curve-uPointer.y*.018);
   float line=exp(-distanceToLine*(460.-j*17.));
   float aura=exp(-distanceToLine*32.)*.017;
   float sweep=pow(max(0.,sin(x*3.5-t*.65+j*.08)),12.);
   float shade=smoothstep(.25,.7,x)*(1.-smoothstep(.94,1.2,x));
   colour+=(vec3(.15,.55,1.)*line*(.08+sweep*.6)+vec3(.04,.21,.5)*aura)*shade;
  }
  vec2 cells=uv*vec2(26.,18.);vec2 cell=floor(cells),fraction=fract(cells);float seed=hash(cell);
  vec2 dotPosition=vec2(hash(cell+3.),hash(cell+17.))*.75+.125;
  float star=exp(-length((fraction-dotPosition)*vec2(aspect*.7,1.))*88.);
  float twinkle=.2+pow(.5+.5*sin(t*.8+seed*32.),8.)*.8;
  colour+=vec3(.5,.78,1.)*star*twinkle*step(.87,seed)*right*.5;
  float grain=(hash(uv*uSize+fract(t*.03))-.5)*.012;
  float vignette=1.-smoothstep(.24,.86,length((uv-.5)*vec2(.82,1.)));
  colour*=.72+vignette*.28;
  gl_FragColor=vec4(colour+grain,1.);
 }
`;
function SignalField({signal}:{signal:Signal}){
 const small=matchMedia('(max-width:700px)').matches;const suffix=small?'960':'1920';
 const textures=useLoader(TextureLoader,['atrium','trace','vault'].map(name=>'/images/'+name+'-'+suffix+'.webp'));
 const material=useRef<ShaderMaterial>(null);const {size}=useThree();
 const uniforms=useMemo(()=>({uOriginal:{value:textures[0]},uSource:{value:textures[1]},uRecord:{value:textures[2]},uTime:{value:0},uProgress:{value:0},uSize:{value:new Vector2(size.width,size.height)},uPointer:{value:new Vector2()}}),[textures]);
 useEffect(()=>{uniforms.uSize.value.set(size.width,size.height);},[size,uniforms]);
 useFrame((_,delta)=>{if(!material.current)return;const u=material.current.uniforms;u.uTime.value+=Math.min(delta,.05);u.uProgress.value=MathUtils.damp(u.uProgress.value,signal.current.progress,4,delta);u.uPointer.value.x=MathUtils.damp(u.uPointer.value.x,signal.current.pointerX,3,delta);u.uPointer.value.y=MathUtils.damp(u.uPointer.value.y,signal.current.pointerY,3,delta);});
 return <mesh frustumCulled={false}><planeGeometry args={[2,2]}/><shaderMaterial ref={material} uniforms={uniforms} vertexShader={vertexShader} fragmentShader={fragmentShader} depthTest={false} depthWrite={false} toneMapped={false}/></mesh>;
}
export default function LivingBackground({signal}:{signal:Signal}){
 const [visible,setVisible]=useState(!document.hidden),[lost,setLost]=useState(false);
 useEffect(()=>{const change=()=>setVisible(!document.hidden);document.addEventListener('visibilitychange',change);return()=>document.removeEventListener('visibilitychange',change);},[]);
 if(lost)return null;
 return <div className="living-webgl"><BackgroundBoundary><Canvas dpr={[1,1.25]} frameloop={visible?'always':'never'} gl={{alpha:true,antialias:false,powerPreference:'low-power'}} onCreated={({gl})=>{gl.domElement.addEventListener('webglcontextlost',()=>setLost(true),{once:true});}}><Suspense fallback={null}><SignalField signal={signal}/></Suspense></Canvas></BackgroundBoundary></div>;
}
