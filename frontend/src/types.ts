export type Status='unverified'|'flagged'|'verified'|'confirmed_fraud';
export type Check={name:string;state:'pass'|'warn'|'unknown';detail:string};
export type Decision={id:string;outcome:string;reason:string;evidence:string;created_at:string;reviewer:string};
export type Doc={id:string;filename:string;college:string;category:string;period:string;sha256:string;status:Status;created_at:string;checks:Check[];text:string;ai?:string;decisions:Decision[];anchor?:string};
export type User={id:string;name:string;college:string;role:'college'|'reviewer';email:string};
export type Anchor={id:string;case_id:string;document_hash:string;evidence_hash:string;outcome:string;timestamp:string;state:string;tx_hash?:string};
export const categories=['Teaching & faculty','Research publications','Student placements','Infrastructure','Student outcomes','Financial records'];
export const labels:Record<Status,string>={unverified:'Unverified',flagged:'Flagged',verified:'Verified',confirmed_fraud:'Confirmed fraud'};
