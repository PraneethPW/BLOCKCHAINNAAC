import fs from 'node:fs';
import solc from 'solc';
const input={language:'Solidity',sources:{'VerisVault.sol':{content:fs.readFileSync(new URL('./VerisVault.sol',import.meta.url),'utf8')}},settings:{optimizer:{enabled:true,runs:200},evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}};
const output=JSON.parse(solc.compile(JSON.stringify(input)));
const errors=(output.errors||[]).filter(e=>e.severity==='error');
if(errors.length)throw new Error(errors.map(e=>e.formattedMessage).join('\n'));
const c=output.contracts['VerisVault.sol'].VerisVault;
fs.writeFileSync(new URL('../backend/vault_contract.json',import.meta.url),JSON.stringify({contractName:'VerisVault',compiler:solc.version(),abi:c.abi,bytecode:'0x'+c.evm.bytecode.object},null,2));
console.log('Compiled VerisVault.');
