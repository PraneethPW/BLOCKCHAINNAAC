import type {Doc,User,Anchor} from './types';
export const API=(import.meta as ImportMeta & {env:Record<string,string>}).env.VITE_API_URL||'http://127.0.0.1:8000';
let token='';
export function setToken(value:string){token=value;}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);if(token)headers.set('Authorization',`Bearer ${token}`);
 if(init.body&&!(init.body instanceof FormData))headers.set('Content-Type','application/json');
 const r=await fetch(API+path,{...init,headers});if(!r.ok){const d=await r.json().catch(()=>({detail:'Could not connect to the server'}));throw new Error(typeof d.detail==='string'?d.detail:'Check the submitted fields.');}return r.json();
}
export async function login(email:string,password:string){const r=await api<{token:string;user:User}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});setToken(r.token);return r.user;}
export const getDocs=()=>api<Doc[]>('/documents');
export const getLedger=()=>api<Anchor[]>('/ledger');
export async function report(id:string){const r=await fetch(`${API}/documents/${id}/report`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw new Error('Could not generate the report');return r.blob();}
export async function original(id:string){const r=await fetch(`${API}/documents/${id}/file`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw new Error('Original file is unavailable.');return r.blob();}
