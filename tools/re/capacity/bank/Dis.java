import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import java.io.*;
public class Dis extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter pw = new PrintWriter(new FileWriter(a[0]));
    for (int i = 1; i + 1 < a.length; i += 2) {
      Address lo = toAddr(a[i]), hi = toAddr(a[i+1]);
      Address ad = lo;
      while (ad.compareTo(hi) <= 0) {
        Instruction in = getInstructionAt(ad);
        if (in == null) { disassemble(ad); in = getInstructionAt(ad); }
        if (in == null) { pw.println(ad + "  ??  " + String.format("%02x", getByte(ad)&0xff)); ad = ad.add(2); continue; }
        pw.println(ad + "  " + in.toString());
        ad = ad.add(in.getLength());
      }
    }
    pw.close();
  }
}
