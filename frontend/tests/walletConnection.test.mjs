import test from 'node:test';
import assert from 'node:assert/strict';
import {chooseWalletAccount,walletRequest} from '../src/walletConnection.ts';
const address='0x'+'1'.repeat(40);

test('new login requests account selection before reading the active address',async()=>{
 const calls=[];
 const provider={request:async request=>{calls.push(request);return request.method==='eth_requestAccounts'?[address]:[];}};
 assert.equal(await chooseWalletAccount(provider,true),address);
 assert.deepEqual(calls,[{method:'wallet_requestPermissions',params:[{eth_accounts:{}}]},{method:'eth_requestAccounts'}]);
});
test('wallets without permission selection fall back to their connection prompt',async()=>{
 for(const code of [-32601,4200]){
  const provider={request:async({method})=>{if(method==='wallet_requestPermissions')throw {code};return [address];}};
  assert.equal(await chooseWalletAccount(provider,true),address);
 }
});
test('declining account selection does not trigger another permission prompt',async()=>{
 let calls=0;
 await assert.rejects(chooseWalletAccount({request:async()=>{calls++;throw {code:4001};}},true),e=>e.code===4001);
 assert.equal(calls,1);
});
test('save uses the existing wallet permission, with no account reset',async()=>{
 const calls=[];
 assert.equal(await chooseWalletAccount({request:async({method})=>{calls.push(method);return [address];}},false),address);
 assert.deepEqual(calls,['eth_requestAccounts']);
});
test('empty accounts and stalled extensions show actionable failures',async()=>{
 await assert.rejects(chooseWalletAccount({request:async()=>[]},false),/Create or unlock/);
 await assert.rejects(walletRequest({request:()=>new Promise(()=>{})},'eth_chainId',undefined,5),/wallet did not respond/);
});
