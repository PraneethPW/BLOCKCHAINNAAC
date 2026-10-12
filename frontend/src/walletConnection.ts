export type Provider={request:(args:{method:string;params?:unknown[]})=>Promise<unknown>};

export async function walletRequest(provider:Provider,method:string,params?:unknown[],timeoutMs=90000):Promise<unknown>{
 let timer:ReturnType<typeof setTimeout>|undefined;
 try{
  return await Promise.race([
   provider.request({method,...(params?{params}:{})}),
   new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error('Your wallet did not respond. Open its extension, finish or dismiss any pending request, then try again. If this browser does not support the wallet popup, open Veris in Chrome or Edge.')),timeoutMs);})
  ]);
 }finally{if(timer)clearTimeout(timer);}
}

export async function chooseWalletAccount(provider:Provider,chooseAgain:boolean){
 if(chooseAgain){
  try{await walletRequest(provider,'wallet_requestPermissions',[{eth_accounts:{}}]);}
  catch(error){
   // Some EIP-1193 wallets do not implement EIP-2255 account selection.
   if(![-32601,4200].includes(Number((error as {code?:number}).code)))throw error;
  }
 }
 const accounts=await walletRequest(provider,'eth_requestAccounts');
 if(!Array.isArray(accounts)||typeof accounts[0]!=='string'||!/^0x[0-9a-fA-F]{40}$/.test(accounts[0]))throw new Error('No wallet account was selected. Create or unlock an account in your wallet app, then try again.');
 return accounts[0] as string;
}
