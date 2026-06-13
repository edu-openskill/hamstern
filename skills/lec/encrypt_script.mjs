#!/usr/bin/env node
// 판서 대본 암호화 — 브라우저 SubtleCrypto 와 동일한 PBKDF2(SHA-256)+AES-GCM.
// 사용: echo "<html>" | LEC_SCRIPT_PASSCODE=비번 node encrypt_script.mjs
// 출력(stdout): {"cipher":b64,"salt":b64,"iv":b64,"iters":N}
import { webcrypto as wc } from 'node:crypto';

const ITERS = 210000;
const pw = process.env.LEC_SCRIPT_PASSCODE;
if (!pw) { console.error('LEC_SCRIPT_PASSCODE env 가 필요합니다.'); process.exit(2); }

function readStdin() {
  return new Promise((res) => {
    let d = ''; process.stdin.setEncoding('utf8');
    process.stdin.on('data', c => d += c);
    process.stdin.on('end', () => res(d));
  });
}
const b64 = (buf) => Buffer.from(buf).toString('base64');

const plain = await readStdin();
const enc = new TextEncoder();
const salt = wc.getRandomValues(new Uint8Array(16));
const iv = wc.getRandomValues(new Uint8Array(12));
const keyMat = await wc.subtle.importKey('raw', enc.encode(pw), { name: 'PBKDF2' }, false, ['deriveKey']);
const key = await wc.subtle.deriveKey(
  { name: 'PBKDF2', salt, iterations: ITERS, hash: 'SHA-256' },
  keyMat, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
const cipher = await wc.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(plain));
process.stdout.write(JSON.stringify({ cipher: b64(cipher), salt: b64(salt), iv: b64(iv), iters: ITERS }));
