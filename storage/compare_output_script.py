import difflib

paragraphs = [
        """
=== Running fuzz 0: 0x00000013 ===
=== Running fuzz 1: 0x10028027 ===
=== Running fuzz 2: 0xffffffff ===
Caught SIGILL (Illegal Instruction)
Faulting address: 0x3fe78d0020
=== Running fuzz 3: 0x00008067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
=== Running fuzz 4: 0x00050067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffdc1baf2108
=== Running fuzz 5: 0x00048067 ===
=== Running fuzz 6: 0x00058067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xfffffffffffffffe
=== Running fuzz 7: 0x0000a103 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 8: 0x0142b183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffff878a406206
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 9: 0x01423183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0019
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0019
x0 (zero) changed: 0xd8b2fb3fc35cd94a -> 0x0000000000000000
x3 (gp) changed: 0xd5c1e2fb3cfa9478 -> 0xffffffffffffffff
x9 (s1) changed: 0x0000000000000000 -> 0x0000000000098e00
f2   changed: 0x74b3977385b267fd -> 0xffffffff85b267fd
f3   changed: 0xb8092bb3cafdea73 -> 0xffffffffcafdea73
f4   changed: 0x0000000000000001 -> 0xffffffff00000001
f5   changed: 0x489e03954350cb80 -> 0xffffffff4350cb80
f6   changed: 0xb8912e1ade5ff3cd -> 0xffffffffde5ff3cd
f7   changed: 0x27ca1d145b08a7be -> 0xffffffff5b08a7be
f10  changed: 0x0da567778ba48f39 -> 0xffffffff8ba48f39
f13  changed: 0x0000000000000000 -> 0xffffffff00000000
f14  changed: 0x0000000000000000 -> 0xffffffff00000000
f15  changed: 0x0800000000000006 -> 0xffffffff00000006
f16  changed: 0x0c6cd25bf8dd32a5 -> 0xfffffffff8dd32a5
f17  changed: 0x7fe92f0d96e9cb5a -> 0xffffffff96e9cb5a
f20  changed: 0xc29b73b407a253b6 -> 0xffffffff07a253b6
f25  changed: 0x0000000000000000 -> 0xffffffff00000000
""",
        """
=== Running fuzz 0: 0x00000013 ===
=== Running fuzz 1: 0x10028027 ===
=== Running fuzz 2: 0xffffffff ===
Caught SIGILL (Illegal Instruction)
Faulting address: 0x3fe78d0020
=== Running fuzz 3: 0x00008067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
=== Running fuzz 4: 0x00050067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffdc1baf2108
=== Running fuzz 5: 0x00048067 ===
=== Running fuzz 6: 0x00058067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xfffffffffffffffe
=== Running fuzz 7: 0x0000a103 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 8: 0x0142b183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffff878a406206
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 9: 0x01423183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0019
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0019
x0 (zero) changed: 0xd8b2fb3fc35cd94a -> 0x0000000000000000
x3 (gp) changed: 0xd5c1e2fb3cfa9478 -> 0xffffffffffffffff
x9 (s1) changed: 0x0000000000000000 -> 0x0000000000098e00
f2   changed: 0x74b3977385b267fd -> 0xffffffff85b267fd
f3   changed: 0xb8092bb3cafdea73 -> 0xffffffffcafdea73
f4   changed: 0x0000000000000001 -> 0xffffffff00000001
f5   changed: 0x489e03954350cb80 -> 0xffffffff4350cb80
f6   changed: 0xb8912e1ade5ff3cd -> 0xffffffffde5ff3cd
f7   changed: 0x27ca1d145b08a7be -> 0xffffffff5b08a7be
f10  changed: 0x0da567778ba48f39 -> 0xffffffff8ba48f39
f13  changed: 0x0000000000000000 -> 0xffffffff00000000
f14  changed: 0x0000000000000000 -> 0xffffffff00000000
f15  changed: 0x0800000000000006 -> 0xffffffff00000006
f16  changed: 0x0c6cd25bf8dd32a5 -> 0xfffffffff8dd32a5
f17  changed: 0x7fe92f0d96e9cb5a -> 0xffffffff96e9cb5a
f20  changed: 0xc29b73b407a253b6 -> 0xffffffff07a253b6
f25  changed: 0x0000000000000000 -> 0xffffffff00000000
""",
        """
=== Running fuzz 0: 0x00000013 ===
=== Running fuzz 1: 0x10028027 ===
=== Running fuzz 2: 0xffffffff ===
Caught SIGILL (Illegal Instruction)
Faulting address: 0x3ff35fc020
=== Running fuzz 3: 0x00008067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
=== Running fuzz 4: 0x00050067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffdc1baf2108
=== Running fuzz 5: 0x00048067 ===
=== Running fuzz 6: 0x00058067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xfffffffffffffffe
=== Running fuzz 7: 0x0000a103 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 8: 0x0142b183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffff878a406206
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 9: 0x01423183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0020
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0020
x0 (zero) changed: 0xd8b2fb3fc35cd94a -> 0x0000000000000000
x3 (gp) changed: 0xd5c1e2fb3cfa9478 -> 0xffffffffffffffff
x9 (s1) changed: 0x0000000000000000 -> 0x0000000000086d00
f2   changed: 0x74b3977385b267fd -> 0xffffffff85b267fd
f3   changed: 0xb8092bb3cafdea73 -> 0xffffffffcafdea73
f4   changed: 0x0000000000000001 -> 0xffffffff00000001
f5   changed: 0x489e03954350cb80 -> 0xffffffff4350cb80
f6   changed: 0xb8912e1ade5ff3cd -> 0xffffffffde5ff3cd
f7   changed: 0x27ca1d145b08a7be -> 0xffffffff5b08a7be
f10  changed: 0x0da567778ba48f39 -> 0xffffffff8ba48f39
f13  changed: 0x0000000000000000 -> 0xffffffff00000000
f14  changed: 0x0000000000000000 -> 0xffffffff00000000
f15  changed: 0x0800000000000006 -> 0xffffffff00000006
f16  changed: 0x0c6cd25bf8dd32a5 -> 0xfffffffff8dd32a5
f17  changed: 0x7fe92f0d96e9cb5a -> 0xffffffff96e9cb5a
f20  changed: 0xc29b73b407a253b6 -> 0xffffffff07a253b6
f25  changed: 0x0000000000000000 -> 0xffffffff00000000
""",
        """
=== Running fuzz 0: 0x00000013 ===
=== Running fuzz 1: 0x10028027 ===
=== Running fuzz 2: 0xffffffff ===
Caught SIGILL (Illegal Instruction)
Faulting address: 0x3ff35fc020
=== Running fuzz 3: 0x00008067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
=== Running fuzz 4: 0x00050067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffdc1baf2108
=== Running fuzz 5: 0x00048067 ===
=== Running fuzz 6: 0x00058067 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xfffffffffffffffe
=== Running fuzz 7: 0x0000a103 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffffd112f01034
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 8: 0x0142b183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xffffff878a406206
SIGSEGV fault occured in restricted area. ERROR!! Returning
=== Running fuzz 9: 0x01423183 ===
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0020
Caught SIGSEGV (Segmentation Fault)
Faulting address: 0xf0020
x0 (zero) changed: 0xd8b2fb3fc35cd94a -> 0x0000000000000000
x3 (gp) changed: 0xd5c1e2fb3cfa9478 -> 0xffffffffffffffff
x9 (s1) changed: 0x0000000000000000 -> 0x0000000000086d00
f2   changed: 0x74b3977385b267fd -> 0xffffffff85b267fd
f3   changed: 0xb8092bb3cafdea73 -> 0xffffffffcafdea73
f4   changed: 0x0000000000000001 -> 0xffffffff00000001
f5   changed: 0x489e03954350cb80 -> 0xffffffff4350cb80
f6   changed: 0xb8912e1ade5ff3cd -> 0xffffffffde5ff3cd
f7   changed: 0x27ca1d145b08a7be -> 0xffffffff5b08a7be
f10  changed: 0x0da567778ba48f39 -> 0xffffffff8ba48f39
f13  changed: 0x0000000000000000 -> 0xffffffff00000000
f14  changed: 0x0000000000000000 -> 0xffffffff00000000
f15  changed: 0x0800000000000006 -> 0xffffffff00000006
f16  changed: 0x0c6cd25bf8dd32a5 -> 0xfffffffff8dd32a5
f17  changed: 0x7fe92f0d96e9cb5a -> 0xffffffff96e9cb5a
f20  changed: 0xc29b73b407a253b6 -> 0xffffffff07a253b6
f25  changed: 0x0000000000000000 -> 0xffffffff00000000
"""
    ]

def compare_paragraphs(p1, p2, label1, label2):
    print(f"\n--- Comparing {label1} vs {label2} ---")
    if p1 == p2:
        print("✅ They are identical.")
        return

    diff = difflib.ndiff(p1.split(), p2.split())
    for i, line in enumerate(diff):
        if line.startswith("- ") or line.startswith("+ "):
            print(line)  # show added/removed parts

pairs = [
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 2),
    (1, 3),
    (2, 3),
]

for i, j in pairs:
    compare_paragraphs(paragraphs[i], paragraphs[j], f"Paragraph {i+1}", f"Paragraph {j+1}")