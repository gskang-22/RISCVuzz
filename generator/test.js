import { Instruction } from './Instruction.js';


// Example instructions
const instructions = [
    'ADDI x5, x0, 10',
];

instructions.forEach(i => {
    try {
        const inst = new Instruction(i);
        console.log('Input:', i);
        // console.log('ASM:', inst.asm);
        console.log('0x' + inst.hex);
        console.log('---');
    } catch(e) {
        console.log('Input:', i, '\n→ Error:', e);
        console.log('---');
    }
});
