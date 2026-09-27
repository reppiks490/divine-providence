#!/usr/bin/env node
import fs from 'node:fs';
import crypto from 'node:crypto';

function canonicalize(value) {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || !Number.isSafeInteger(value)) throw new Error('fixture numbers must be safe integers');
    return JSON.stringify(value);
  }
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalize).join(',') + ']';
  if (typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonicalize(value[k])).join(',') + '}';
  }
  throw new Error('unsupported JSON value');
}

const path = process.argv[2];
if (!path) process.exit(2);
const fixture = JSON.parse(fs.readFileSync(path, 'utf8'));
if (fixture.profile !== 'supermesh-json-v1' || fixture.algorithm !== 'Ed25519') process.exit(3);
const canonical = Buffer.from(canonicalize(fixture.statement), 'utf8');
const canonicalMatch = canonical.toString('hex') === fixture.canonical_hex;
const digestMatch = crypto.createHash('sha256').update(canonical).digest('hex') === fixture.sha256;
const spki = Buffer.concat([Buffer.from('302a300506032b6570032100','hex'), Buffer.from(fixture.public_key_hex,'hex')]);
const key = crypto.createPublicKey({key:spki, format:'der', type:'spki'});
const signatureVerified = crypto.verify(null, canonical, key, Buffer.from(fixture.signature_hex,'hex'));
process.stdout.write(JSON.stringify({canonical_match:canonicalMatch,digest_match:digestMatch,signature_verified:signatureVerified}));
process.exit(canonicalMatch && digestMatch && signatureVerified ? 0 : 1);
