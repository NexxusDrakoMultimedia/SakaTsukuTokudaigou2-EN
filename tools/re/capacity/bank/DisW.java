import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import java.io.*;
// args: out, then items: "lo-hi" = disassemble (clearing nothing), "w:addr" = print 32-bit LE word, "s:addr" = C string
public class DisW extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter pw = new PrintWriter(new FileWriter(a[0]));
    pw.println("program " + currentProgram.getName());
    for (int i = 1; i < a.length; i++) {
      String s = a[i];
      if (s.startsWith("w:")) {
        Address ad = toAddr(s.substring(2));
        pw.println(ad + "  .long 0x" + String.format("%08x", getInt(ad)));
      } else if (s.startsWith("s:")) {
        Address ad = toAddr(s.substring(2));
        StringBuilder sb = new StringBuilder();
        for (int k = 0; k < 64; k++) { int b = getByte(ad.add(k)) & 0xff; if (b == 0) break; sb.append((char) b); }
        pw.println(ad + "  .string \"" + sb + "\"");
      } else {
        String[] p = s.split("-");
        Address lo = toAddr(p[0]), hi = toAddr(p[1]);
        Address ad = lo;
        while (ad.compareTo(hi) <= 0) {
          Instruction in = getInstructionAt(ad);
          if (in == null) { disassemble(ad); in = getInstructionAt(ad); }
          if (in == null) { pw.println(ad + "  ??"); ad = ad.add(2); continue; }
          StringBuilder by = new StringBuilder();
          for (byte b : in.getBytes()) by.append(String.format("%02x", b & 0xff));
          pw.println(ad + "  " + by + "  " + in.toString());
          ad = ad.add(in.getLength());
        }
      }
    }
    pw.close();
  }
}
