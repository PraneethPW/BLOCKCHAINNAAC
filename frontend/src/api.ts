export const API='/api';
export class ApiError extends Error{constructor(message:string,public status:number){super(message);}}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);headers.set('X-Veris-Request','workspace');
 if(init.body&&!(init.body instanceof FormData))headers.set('Content-Type','application/json');
 const r=await fetch(API+path,{...init,headers,credentials:'include',cache:'no-store'});if(!r.ok){const d=await r.json().catch(()=>null);const detail=d?.detail;throw new ApiError(typeof detail==='string'?detail:Array.isArray(detail)?detail.map((e:{msg:string})=>e.msg).join(' '):r.status===429?'Too many requests. Wait a minute and try again.':'The service could not complete this request. Please retry.',r.status);}return r.json();
}
export async function downloadFile(path:string,name:string){const response=await fetch(API+path,{credentials:'include',cache:'no-store'});if(!response.ok){const error=await response.json().catch(()=>null);throw new ApiError(typeof error?.detail==='string'?error.detail:'This file is unavailable or your session has expired.',response.status);}const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
