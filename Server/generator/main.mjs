#!/usr/bin/env node
import readline from 'readline';
import { Instruction } from './Instruction.js';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on('line', (line) => {
    try {
        const inst = new Instruction(line.trim());
        // console.log(JSON.stringify({ asm: inst.asm, hex: inst.hex }));
        console.log(JSON.stringify({hex: inst.hex }));
    } catch (err) {
        console.log(JSON.stringify({ error: err.message || String(err) }));
    }
});
