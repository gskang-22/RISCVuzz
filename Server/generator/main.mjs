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
        console.log(JSON.stringify({ asm: inst.asm, hex: inst.hex }));
    } catch (e) {
        console.log(JSON.stringify({ error: e.toString() }));
    }
});
