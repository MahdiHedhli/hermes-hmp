/** TEST-ONLY, UNEXECUTED SOURCE. Public fixture keys; deterministic ekm never ships.
 * No server/app/native imports. Fixed local inputs and outputs, no network.
 * Future execution needs separate independent review and root admission.
 */
import { readFileSync, writeFileSync, mkdirSync, lstatSync, readdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash, createPrivateKey, createPublicKey, sign } from 'node:crypto';
import assert from 'node:assert/strict';
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..'); // isolated runtime has src/ and node_modules/
const INFO = Buffer.from('HMP push seal v1', 'ascii');
const OFFICIAL_SHA = '61fc662f01996cd06d713dacf5e133167bd309a1f329442d53f1e21a47b3ede6';
const sha = b => createHash('sha256').update(b).digest('hex');
const hex = b => Buffer.from(b).toString('hex');
const ab = b => Uint8Array.from(b).buffer; // never expose Buffer pool tails
const unhex = s => { assert.match(s, /^(?:[0-9a-f]{2})*$/); return Buffer.from(s,'hex'); };
const b64 = b => Buffer.from(b).toString('base64url');
function boundedRead(path, cap) { const st=lstatSync(path); assert(st.isFile() && !st.isSymbolicLink() && st.size<=cap); return readFileSync(path); }
const load = (name,cap=8*1024*1024) => JSON.parse(boundedRead(join(HERE,name),cap));
function files(path, prefix='') { let out=[]; for(const n of readdirSync(path)) {const q=join(path,n),s=lstatSync(q);assert(!s.isSymbolicLink());if(s.isDirectory())out.push(...files(q,prefix+n+'/'));else{assert(s.isFile());out.push(prefix+n);}}return out.sort(); }
function preflight() {
  assert.equal(process.argv.length,2); assert.equal(process.version,'v22.22.3'); assert.equal(process.cwd(),HERE);
  const allowed=new Set(['PATH','HOME','TMPDIR','LANG','LC_ALL','TZ','PYCRYPTODOME_DISABLE_GMP']);
  assert.equal(Object.keys(process.env).length,allowed.size);for(const key of Object.keys(process.env)) assert(allowed.has(key));
  assert.equal(process.env.LANG,'C.UTF-8');assert.equal(process.env.LC_ALL,'C.UTF-8');assert.equal(process.env.PYCRYPTODOME_DISABLE_GMP,'1');
  assert.equal(process.env.HOME,join(ROOT,'home'));assert.equal(process.env.TMPDIR,join(ROOT,'tmp'));assert.equal(process.env.TZ,'UTC');
  const pins=load('source-pins.json');for(const [name,h] of Object.entries(pins.hashes))assert.equal(sha(boundedRead(join(HERE,name),8*1024*1024)),h);
  const lock=load('dependencies.lock.json'); assert.equal(lock.packages.length,5);
  let expected=[];for(const pkg of lock.packages.filter(p=>p.ecosystem==='npm')) {
    for(const f of pkg.files) {assert(f.path.startsWith('package/')); const name=pkg.name+'/'+f.path.slice(8);expected.push(name);assert.equal(sha(boundedRead(join(ROOT,'node_modules',name),1024*1024)),f.sha256);}
  }
  assert.deepEqual(files(join(ROOT,'node_modules')),expected.sort());
  assert.equal(sha(boundedRead(join(HERE,'data/rfc9180-test-vectors.json'),6*1024*1024)),OFFICIAL_SHA);
  assert.equal(INFO.length,16);
}
function u64(n) {assert(Number.isSafeInteger(n) && n>=0);const b=Buffer.alloc(8);b.writeBigUInt64BE(BigInt(n));return b;}
function transcript(o,iid) {
 const f=[Buffer.from(o.aud),Buffer.from(iid),u64(o.ts),Buffer.from(o.nonce,'base64url'),Buffer.from(o.kid),Buffer.from(o.platform),Buffer.from(o.addr_kind),Buffer.from(o.env??''),createHash('sha256').update(Buffer.from(o.sealed,'base64url')).digest(),Buffer.from(o.route,'base64url'),Buffer.from(o.hint,'base64url'),Buffer.from(o.collapse,'base64url'),u64(o.ttl_s),Buffer.from(o.kind)];
 return Buffer.concat([Buffer.from('HMP1-PUSH-RELAY'),...f.flatMap(b=>{const l=Buffer.alloc(4);l.writeUInt32BE(b.length);return[l,b];})]);
}
function base32(b) {let bits=0,v=0,s='';for(const x of b){v=(v<<8)|x;bits+=8;while(bits>=5){bits-=5;s+='abcdefghijklmnopqrstuvwxyz234567'[(v>>>bits)&31];}}if(bits)s+='abcdefghijklmnopqrstuvwxyz234567'[(v<<(5-bits))&31];return s;}
async function main() {
 preflight(); // validate exact source/data/dependency files BEFORE dependency imports
 const hpke=await import(join(ROOT,'node_modules/@hpke/core/esm/mod.js'));
 const canonicalize=(await import(join(ROOT,'node_modules/canonicalize/lib/canonicalize.js'))).default;
 const {CipherSuite,DhkemP256HkdfSha256,HkdfSha256,Aes128Gcm,Aes256Gcm}=hpke;
 const suite=()=>new CipherSuite({kem:new DhkemP256HkdfSha256(),kdf:new HkdfSha256(),aead:new Aes128Gcm()});
 const tags=load('data/tag-domains.json').tags;for(const a of tags)for(const b of tags)if(a!==b)assert(!a.startsWith(b));
 const all=load('data/rfc9180-test-vectors.json');const chosen=all.filter(v=>v.mode===0&&v.kem_id===16&&v.kdf_id===1&&v.aead_id===1);assert.equal(chosen.length,1);const v=chosen[0];assert.equal(v.encryptions.length,257);assert.equal(v.exports.length,3);
 const s=suite(),r=await s.kem.deriveKeyPair(ab(unhex(v.ikmR))),e=await s.kem.deriveKeyPair(ab(unhex(v.ikmE)));
 for(const [key,want,kind] of [[r.publicKey,v.pkRm,'Public'],[r.privateKey,v.skRm,'Private'],[e.publicKey,v.pkEm,'Public'],[e.privateKey,v.skEm,'Private']])assert.equal(hex(await s.kem['serialize'+kind+'Key'](key)),want);
 const params={recipientPublicKey:r.publicKey,info:ab(unhex(v.info)),ekm:ab(unhex(v.ikmE))};
 const kem=await s.kem.encap(params);assert.equal(hex(kem.enc),v.enc);assert.equal(hex(kem.sharedSecret),v.shared_secret);
 const ctx=await s.createSenderContext(params);assert.equal(hex(ctx.enc),v.enc);
 for(const x of v.encryptions)assert.equal(hex(await ctx.seal(ab(unhex(x.pt)),ab(unhex(x.aad)))),x.ct);
 for(const x of v.exports)assert.equal(hex(await ctx.export(ab(unhex(x.exporter_context)),x.L)),x.exported_value);
 // No computation of private key schedule/nonce state. Explicit API exposure below.
 const coverage={pkRm:'compared',skRm:'compared',pkEm:'compared',skEm:'compared',enc:'compared',shared_secret:'compared',ct:'257 compared',exports:'3 compared',key_schedule_context:'not exposed',secret:'not exposed',key:'not exposed',base_nonce:'not exposed',exporter_secret:'not exposed',nonce:'not exposed'};
 const alt=all.find(x=>x.mode===0&&x.kem_id===16&&x.pkRm!==v.pkRm);assert(alt);
 const alternate=await s.kem.deserializePublicKey(ab(unhex(alt.pkRm)));
 const test=load('data/public-test-material.json'),spki=unhex(test.signing.spki_der_hex);
 const pub=createPublicKey({key:spki,format:'der',type:'spki'}),jwk=pub.export({format:'jwk'});assert.equal(jwk.crv,'P-256');
 const key=createPrivateKey({key:{...jwk,d:b64(unhex(test.signing.private_scalar_hex))},format:'jwk'});
 const iid=base32(createHash('sha256').update(spki).digest());assert.equal(iid,test.signing.iid);
 const defs=load('cases.json');assert.equal(defs.cases.length,151);const rows=[];
 for(const [index,c] of defs.cases.entries()) {
  const platform=c.platform??'apns',kind=c.addr_kind??'apns_token';
  const plain={addr:'SYNTHETIC/address',addr_kind:kind,app:'test.example',iid,n:b64(Buffer.alloc(16,index)),not_after:1700003600,platform,v:1};if(platform==='apns')plain.env='sandbox';Object.assign(plain,c.plain_patch??{});for(const k of c.plain_remove??[])delete plain[k];
  let pt=Buffer.from(canonicalize(plain));const mode=c.plain_mode;
  if(mode==='size1024'||mode==='size1025'){const size=mode==='size1024'?1024:1025;plain.addr+='x'.repeat(size-pt.length);pt=Buffer.from(canonicalize(plain));assert.equal(pt.length,size);}
  if(mode==='array')pt=Buffer.from('[]');if(mode==='negative_zero_expiry')pt=Buffer.from(pt.toString().replace('"not_after":0','"not_after":-0'));
  if(mode==='empty')pt=Buffer.alloc(0);if(mode==='one')pt=Buffer.from('x');
  const text=()=>pt.toString('utf8');
  if(mode==='duplicate')pt=Buffer.from('{"v":1,'+text().slice(1));if(mode==='escaped_duplicate')pt=Buffer.from('{"\\u0076":1,'+text().slice(1));
  if(mode==='fraction_v')pt=Buffer.from(text().replace('"v":1','"v":1.0'));if(mode==='exponent_v')pt=Buffer.from(text().replace('"v":1','"v":1e0'));
  if(mode==='fraction_expiry')pt=Buffer.from(text().replace('1700003600','1700003600.0'));if(mode==='exponent_expiry')pt=Buffer.from(text().replace('1700003600','1700003600e0'));
  if(mode==='invalid_utf8')pt=Buffer.from([0xff]);if(mode==='bom')pt=Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),pt]);if(mode==='lone_surrogate')pt=Buffer.from(text().replace('SYNTHETIC/address','\\ud800'));
  if(mode==='whitespace')pt=Buffer.from(' '+text());if(mode==='unsorted')pt=Buffer.from(JSON.stringify(plain));if(mode==='alternate_escape')pt=Buffer.from(text().replace('address','\\u0061ddress'));if(mode==='escaped_slash')pt=Buffer.from(text().replace('/','\\/'));
  const baseline={v:1,kind:'approval',aud:'TestAudience',iid_spki:b64(spki),ts:1700000000,nonce:b64(createHash('sha256').update('HMP-TEST-NONCE/'+c.id).digest().subarray(0,16)),kid:'TestKidA',platform,addr_kind:kind,sealed:'',route:b64(Buffer.alloc(32,1)),hint:b64(Buffer.alloc(32,2)),collapse:b64(Buffer.alloc(24,3)),ttl_s:330};if(platform==='apns')baseline.env='sandbox';
  const o={...baseline,...(c.outer_patch??{})};for(const k of c.outer_remove??[])delete o[k];
  const caseSuite=c.seal_suite==='aead256'?new CipherSuite({kem:new DhkemP256HkdfSha256(),kdf:new HkdfSha256(),aead:new Aes256Gcm()}):suite();
  const ekm=createHash('sha256').update('HMP-TEST-ONLY-EKM/'+c.id).digest();
  const info=Buffer.from(c.seal_info??'HMP push seal v1');const aad=Buffer.from(c.seal_aad??o.kid);
  const hp={recipientPublicKey:c.recipient==='alternate'?alternate:r.publicKey,info:ab(info),ekm:ab(ekm)};
  if(c.seal_mode==='auth')hp.senderKey=e.privateKey;if(c.seal_mode==='psk')hp.psk={id:ab(Buffer.from('HMP-TEST-PSK')),key:ab(Buffer.alloc(32,7))};
  const sealed=await caseSuite.seal(hp,ab(pt),ab(aad));let enc=Buffer.from(sealed.enc),ct=Buffer.from(sealed.ct);
  const mutation=c.seal_mutation;
  if(mutation==='tagbit')ct[ct.length-1]^=1;if(mutation==='ctbit')ct[0]^=1;if(mutation==='encbit')enc[32]^=1;if(mutation==='enczero')enc=Buffer.alloc(65);if(mutation==='enchybrid')enc[0]=6;if(mutation==='enccompressed')enc[0]=2;if(mutation==='encoffcurve'){enc=Buffer.alloc(65,1);enc[0]=4;}if(mutation==='encoutofrange'){enc=Buffer.alloc(65,255);enc[0]=4;}
  const raw=Buffer.concat([enc,ct]);o.sealed=b64(raw);baseline.sealed=o.sealed;
  const sw=c.sealed_wire_mode;if(sw==='padding')o.sealed+='=';if(sw==='whitespace')o.sealed+=' ';if(sw==='alphabet')o.sealed='+'+o.sealed.slice(1);if(sw==='trailingbits')o.sealed=b64(Buffer.alloc(82)).slice(0,-1)+'B';if(sw?.startsWith('size'))o.sealed=b64(Buffer.alloc(Number(sw.slice(4))));
  if(c.spki_mode){let b=Buffer.from(spki);if(c.spki_mode==='prefix')b[0]=0;if(c.spki_mode==='zero')b.fill(0,26);if(c.spki_mode==='offcurve')b.fill(1,27);if(c.spki_mode==='short')b=b.subarray(0,90);o.iid_spki=b64(b);}
  // Invalid shape fields cannot have a conforming signature transcript; sign the
  // valid baseline solely to provide a well-formed unrelated signature header.
  let tr;try{tr=transcript(o,iid);}catch{tr=transcript(baseline,iid);}
  let signature=sign('sha256',tr,{key,dsaEncoding:'der'});
  if(c.signature_mode==='nonverifying')signature=unhex('3006020101020101');if(c.signature_der_hex)signature=unhex(c.signature_der_hex);
  Object.assign(o,c.post_sign_patch??{});if(c.post_sign_sealed_bit){const b=Buffer.from(o.sealed,'base64url');b[b.length-1]^=1;o.sealed=b64(b);}let body=Buffer.from(JSON.stringify(o));const wm=c.wire_mode;
  if(wm==='unknown_exponent')body=Buffer.from(body.toString().replace('"unknown_test_field":0','"unknown_test_field":1e400'));
  if(wm==='fraction_ts')body=Buffer.from(body.toString().replace('"ts":1700000000','"ts":1700000000.0'));if(wm==='exponent_v')body=Buffer.from(body.toString().replace('"v":1','"v":1e0'));if(wm==='duplicate')body=Buffer.from('{"v":1,'+body.toString().slice(1));if(wm==='escaped_duplicate')body=Buffer.from('{"\\u0076":1,'+body.toString().slice(1));if(wm==='oversize'){o.unused='x'.repeat(4097-body.length-12);body=Buffer.from(JSON.stringify(o));while(body.length<4097){o.unused+='x';body=Buffer.from(JSON.stringify(o));}assert.equal(body.length,4097);}if(wm==='invalid_utf8')body=Buffer.from([0xff]);if(wm==='bom')body=Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),body]);
  rows.push({id:c.id,expected:c.expected,synthetic_only:true,recipient_test_public_hex:c.recipient==='alternate'?alt.pkRm:v.pkRm,recipient_test_private_hex:c.recipient==='alternate'?alt.skRm:v.skRm,seal_mode:c.seal_mode??'base',seal_aead_id:c.seal_suite==='aead256'?2:1,tag_bytes:16,test_ekm_hex:hex(ekm),seal_info_hex:hex(info),seal_aad_hex:hex(aad),plaintext_hex:hex(pt),plaintext_bytes:pt.length,enc_hex:hex(enc),ct_hex:hex(ct),raw_sealed_hex:hex(raw),sealed_sha256:sha(raw),request_body_hex:hex(body),signed_transcript_hex:hex(tr),signature_der_hex:hex(signature),expected_opener_calls:['eligible','domain_ok','hpke422','plain422','binding422'].includes(c.expected)?1:0,provider_calls:0});
 }
 const corpus={format:'hmp-push-seal-vectors-v1',synthetic_only:true,status:'GENERATOR_ONLY_NOT_INDEPENDENTLY_VERIFIED',contract_sha256:'7c7cb585b8513cd25122fe532a03d3cefa7b0213bea831c1891c28af5d9720a3',info_hex:hex(INFO),suite:{mode:0,kem_id:16,kdf_id:1,aead_id:1},official_sha256:OFFICIAL_SHA,cases_sha256:sha(boundedRead(join(HERE,'cases.json'),1024*1024)),source_pins_sha256:sha(boundedRead(join(HERE,'source-pins.json'),1024*1024)),dependency_lock_sha256:sha(boundedRead(join(HERE,'dependencies.lock.json'),1024*1024)),runtime:process.version,official_counts:{encryptions:257,exports:3},api_coverage:coverage,signature_policy:'randomized DER; regenerate other bytes exactly; independently verify every signature',cases:rows};
 const out=join(ROOT,'out');mkdirSync(out,{mode:0o700});writeFileSync(join(out,'generated.json'),JSON.stringify(corpus,null,2)+'\n',{mode:0o600,flag:'wx'});
 console.log('GENERATED_TEST_ONLY_151_PENDING_INDEPENDENT_CHECK');
}
main().catch(()=>{console.error('VECTOR_GENERATOR_FAILED');process.exitCode=1;});
