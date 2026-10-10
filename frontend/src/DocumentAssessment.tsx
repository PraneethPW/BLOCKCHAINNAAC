import {labels} from './types';
import type {Doc} from './types';

export function assessmentLabel(document:Pick<Doc,'status'|'verification_response'>){
 const result=document.verification_response;
 const outcomes={neutral:'Neutral',checking:'Checking',genuine:'Genuine',manipulated:'Manipulated',corrupted:'Corrupted',fabricated:'Fake / fabricated',non_original:'Non-original',conflict:'Conflicting evidence',fraud_confirmed:'Confirmed fraud'};
 return result?outcomes[result.outcome]||result.title:labels[document.status];
}

export default function DocumentAssessment({document}:{document:Pick<Doc,'status'|'verification_response'>}){
 const result=document.verification_response;
 const style=result?result.tone==='success'?'verified':result.tone==='danger'?'flagged':'unverified':document.status;
 return <span className={'badge '+style} title={result?.title}><span/>{assessmentLabel(document)}</span>;
}
