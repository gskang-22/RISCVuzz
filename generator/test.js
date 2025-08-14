import { Instruction } from './Instruction.js';


// Example instructions
const instructions = [
    'ADD',
    'ADDI',
    'LD',
    'SW',
    'fadd.s',
    'c.lwsp',
    // 'c.swsp',
    // 'c.addi',
    'c.lwsp x3, 5'
    // '00000000101000000000001010010011'
];

instructions.forEach(i => {
    const input = i.toLowerCase();
    try {
        const inst = new Instruction(input);
        console.log('Input:', input);
        console.log(inst.asm);
        console.log('0x' + inst.hex);
        console.log('---');
    } catch(e) {
        console.log('Input:', input, '\n→ Error:', e);
        console.log('---');
    }
});
