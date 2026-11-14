"""Minimal SH-4 interpreter to EXECUTE the tsString layout function (original and patched bytes).

Scope: the integer instructions used by the layout function and by the font-patch code; the FPU
instructions of the layout function (position -> float conversions for the draw call) are treated as
no-ops except fmov.s pushes/pops, which move r15.  Unknown opcodes raise SimError (never guess).
Used by fontpatch.py to prove that the patched code (a) is byte-for-byte equivalent to the original
when the width table is all 12, and (b) implements the documented proportional rule otherwise.
"""
import struct

M = 0xFFFFFFFF


class SimError(Exception):
    pass


def s8(x):
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def s16(x):
    x &= 0xFFFF
    return x - 65536 if x & 0x8000 else x


def s32(x):
    x &= M
    return x - (1 << 32) if x & 0x80000000 else x


class Machine:
    def __init__(self):
        self.mem = {}                 # sparse byte memory
        self.R = [0] * 16
        self.T = 0
        self.PR = 0
        self.MACL = 0
        self.MACH = 0
        self.pc = 0
        self.calls = []               # external calls: (target, r4, r5, r6, r7, r8, r10, r11)
        self.trace = []
        self.stop = None
        self.native = []              # (lo, hi) ranges whose code is executed natively
        self.ext_ret = {}             # target -> python callable(machine) for hooks

    # memory ----------------------------------------------------------------------------------
    def load(self, addr, data):
        for i, b in enumerate(data):
            self.mem[addr + i] = b

    def rb(self, a):
        a &= M
        return self.mem.get(a, 0)

    def rn(self, a, n):
        return int.from_bytes(bytes(self.rb(a + i) for i in range(n)), 'little')

    def wn(self, a, v, n):
        for i in range(n):
            self.mem[(a + i) & M] = (v >> (8 * i)) & 0xFF

    # execution -------------------------------------------------------------------------------
    def run(self, pc, stop_pc, max_steps=2_000_000, watch=None):
        """run until pc == stop_pc. watch: dict pc -> callback(machine) invoked before executing there."""
        self.pc = pc
        steps = 0
        while self.pc != stop_pc:
            if watch and self.pc in watch:
                watch[self.pc](self)
            self.step()
            steps += 1
            if steps > max_steps:
                raise SimError('step limit')
        return steps

    def step(self):
        pc = self.pc
        op = self.rn(pc, 2)
        npc = pc + 2
        br = self.exec_op(op, pc)
        if br is None:
            self.pc = npc
            return
        kind, target = br
        if kind == 'nodelay':
            self.pc = target
            return
        # delayed branch: execute the delay slot, then jump
        dop = self.rn(npc, 2)
        if self.illegal_slot(dop):
            raise SimError('illegal delay-slot instruction %04x at %#x' % (dop, npc))
        self.pc = npc
        r2 = self.exec_op(dop, npc)
        if r2 is not None:
            raise SimError('branch in delay slot at %#x' % npc)
        if kind == 'call':
            self.calls.append((target, self.R[4], self.R[5], self.R[6], self.R[7], self.R[8], self.R[10], self.R[11]))
            if target in self.ext_ret:
                self.ext_ret[target](self)
                self.pc = npc + 2
                return
            if not any(lo <= target < hi for lo, hi in self.native):
                self.R[0] = 0                      # unknown external function: returns 0
                self.pc = npc + 2
                return
        self.pc = target

    @staticmethod
    def illegal_slot(op):
        hi = op >> 12
        if hi in (0xA, 0xB, 0xD, 0x9):             # bra bsr mov.l/mov.w @(disp,PC)
            return True
        if hi == 0x8 and ((op >> 8) & 15) in (0x9, 0xB, 0xD, 0xF):
            return True
        if hi == 0xC and ((op >> 8) & 15) in (0x7, 0x3):   # mova, trapa
            return True
        if (op & 0xF0FF) in (0x400B, 0x402B) or op in (0x000B, 0x002B):
            return True
        return False

    def exec_op(self, op, pc):
        R = self.R
        n = (op >> 8) & 15
        m = (op >> 4) & 15
        hi = op >> 12
        lo = op & 15
        d8 = op & 0xFF
        if hi == 0xE:
            R[n] = s8(d8) & M
        elif hi == 0x7:
            R[n] = (R[n] + s8(d8)) & M
        elif hi == 0x6:
            if lo == 0:
                R[n] = s8(self.rn(R[m], 1)) & M
            elif lo == 1:
                R[n] = s16(self.rn(R[m], 2)) & M
            elif lo == 2:
                R[n] = self.rn(R[m], 4)
            elif lo == 3:
                R[n] = R[m]
            elif lo == 4:
                v = s8(self.rn(R[m], 1)) & M
                R[m] = (R[m] + 1) & M if m != n else R[m]
                R[n] = v
            elif lo == 5:
                v = s16(self.rn(R[m], 2)) & M
                R[m] = (R[m] + 2) & M if m != n else R[m]
                R[n] = v
            elif lo == 6:
                v = self.rn(R[m], 4)
                R[m] = (R[m] + 4) & M if m != n else R[m]
                R[n] = v
            elif lo == 0xB:
                R[n] = (-R[m]) & M
            elif lo == 0xC:
                R[n] = R[m] & 0xFF
            elif lo == 0xD:
                R[n] = R[m] & 0xFFFF
            elif lo == 0xE:
                R[n] = s8(R[m]) & M
            elif lo == 0xF:
                R[n] = s16(R[m]) & M
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0xD:
            R[n] = self.rn(((pc + 4) & ~3) + d8 * 4, 4)
        elif hi == 0x9:
            R[n] = s16(self.rn(pc + 4 + d8 * 2, 2)) & M
        elif hi == 0x5:
            R[n] = self.rn(R[m] + lo * 4, 4)
        elif hi == 0x1:
            self.wn(R[n] + lo * 4, R[m], 4)
        elif hi == 0x2:
            if lo == 0:
                self.wn(R[n], R[m], 1)
            elif lo == 1:
                self.wn(R[n], R[m], 2)
            elif lo == 2:
                self.wn(R[n], R[m], 4)
            elif lo == 4:
                R[n] = (R[n] - 1) & M
                self.wn(R[n], R[m], 1)
            elif lo == 5:
                R[n] = (R[n] - 2) & M
                self.wn(R[n], R[m], 2)
            elif lo == 6:
                R[n] = (R[n] - 4) & M
                self.wn(R[n], R[m], 4)
            elif lo == 8:
                self.T = 1 if (R[n] & R[m]) == 0 else 0
            elif lo == 9:
                R[n] &= R[m]
            elif lo == 0xA:
                R[n] ^= R[m]
            elif lo == 0xB:
                R[n] |= R[m]
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0x3:
            a, b = R[n], R[m]
            if lo == 0:
                self.T = int(a == b)
            elif lo == 2:
                self.T = int(a >= b)
            elif lo == 3:
                self.T = int(s32(a) >= s32(b))
            elif lo == 6:
                self.T = int(a > b)
            elif lo == 7:
                self.T = int(s32(a) > s32(b))
            elif lo == 8:
                R[n] = (a - b) & M
            elif lo == 0xC:
                R[n] = (a + b) & M
            elif lo == 0xE:                      # addc
                t = a + b + self.T
                self.T = int(t > M)
                R[n] = t & M
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0x4:
            sub = op & 0xFF
            if sub == 0x00:
                self.T = (R[n] >> 31) & 1
                R[n] = (R[n] << 1) & M
            elif sub == 0x01:
                self.T = R[n] & 1
                R[n] >>= 1
            elif sub == 0x08:
                R[n] = (R[n] << 2) & M
            elif sub == 0x18:
                R[n] = (R[n] << 8) & M
            elif sub == 0x28:
                R[n] = (R[n] << 16) & M
            elif sub == 0x21:
                self.T = R[n] & 1
                R[n] = (s32(R[n]) >> 1) & M
            elif sub == 0x15:
                self.T = int(s32(R[n]) > 0)
            elif sub == 0x11:
                self.T = int(s32(R[n]) >= 0)
            elif sub == 0x22:                    # sts.l PR,@-Rn
                R[n] = (R[n] - 4) & M
                self.wn(R[n], self.PR, 4)
            elif sub == 0x26:                    # lds.l @Rn+,PR
                self.PR = self.rn(R[n], 4)
                R[n] = (R[n] + 4) & M
            elif sub == 0x0B:                    # jsr @Rn
                self.PR = pc + 4
                return ('call', R[n])
            elif sub == 0x2B:                    # jmp @Rn
                return ('delay', R[n])
            elif sub in (0x5A, 0x6A, 0x62, 0x66, 0x4A):   # lds Rm,FPUL / FPSCR : no effect we model
                pass
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0x0:
            if lo == 7:                          # mul.l Rm,Rn
                self.MACL = (s32(R[n]) * s32(R[m])) & M
            elif lo == 9 and m == 2:             # movt Rn
                R[n] = self.T
            elif lo == 0xA and m == 1:
                R[n] = self.MACL
            elif lo == 0xA and m == 2:
                R[n] = self.PR
            elif lo == 0xC:
                R[n] = s8(self.rn(R[m] + R[0], 1)) & M
            elif lo == 0xD:
                R[n] = s16(self.rn(R[m] + R[0], 2)) & M
            elif lo == 0xE:
                R[n] = self.rn(R[m] + R[0], 4)
            elif lo == 4:
                self.wn(R[n] + R[0], R[m], 1)
            elif lo == 5:
                self.wn(R[n] + R[0], R[m], 2)
            elif lo == 6:
                self.wn(R[n] + R[0], R[m], 4)
            elif op == 0x0009:
                pass
            elif op == 0x000B:
                return ('delay', self.PR)
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0x8:
            sub = n
            if sub == 0x9:                       # bt
                if self.T:
                    return ('nodelay', pc + 4 + s8(d8) * 2)
            elif sub == 0xB:                     # bf
                if not self.T:
                    return ('nodelay', pc + 4 + s8(d8) * 2)
            elif sub == 0xD:                     # bt/s
                if self.T:
                    return ('delay', pc + 4 + s8(d8) * 2)
            elif sub == 0xF:                     # bf/s
                if not self.T:
                    return ('delay', pc + 4 + s8(d8) * 2)
            elif sub == 0x0:                     # mov.b R0,@(disp,Rn)
                self.wn(R[m] + (op & 15), R[0], 1)
            elif sub == 0x1:                     # mov.w R0,@(disp,Rn)
                self.wn(R[m] + (op & 15) * 2, R[0], 2)
            elif sub == 0x4:                     # mov.b @(disp,Rm),R0
                R[0] = s8(self.rn(R[m] + (op & 15), 1)) & M
            elif sub == 0x5:                     # mov.w @(disp,Rm),R0
                R[0] = s16(self.rn(R[m] + (op & 15) * 2, 2)) & M
            elif sub == 0x8:                     # cmp/eq #imm,R0
                self.T = int(s32(R[0]) == s8(d8))
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0xA:
            disp = op & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            return ('delay', pc + 4 + disp * 2)
        elif hi == 0xC:
            sub = n
            if sub == 0x7:                       # mova @(disp,PC),R0
                R[0] = ((pc + 4) & ~3) + d8 * 4
            elif sub == 0x8:                     # tst #imm,R0
                self.T = int((R[0] & d8) == 0)
            elif sub == 0x9:
                R[0] &= d8
            elif sub == 0xB:
                R[0] |= d8
            else:
                raise SimError('op %04x at %#x' % (op, pc))
        elif hi == 0xF:
            # FPU: only the stack-moving forms matter
            if lo == 0xB:                        # fmov.s FRm,@-Rn
                R[n] = (R[n] - 4) & M
            elif lo == 9:                        # fmov.s @Rm+,FRn
                R[m] = (R[m] + 4) & M
            elif lo in (4, 5) or (op & 0xF0FF) in (0xF00D,):
                if lo in (4, 5):
                    raise SimError('fcmp at %#x (T flag would change)' % pc)
        else:
            raise SimError('op %04x at %#x' % (op, pc))
        return None
