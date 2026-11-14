import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

// args: out lo-hi [lo-hi ...]   dumps disassembly (creating code if missing)
public class Dis extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter pw = new PrintWriter(new FileWriter(a[0]));
    for (int i = 1; i < a.length; i++) {
      String[] p = a[i].split("-");
      Address lo = toAddr(p[0]), hi = toAddr(p[1]);
      Address ad = lo;
      pw.println("---- " + lo + "-" + hi);
      while (ad.compareTo(hi) <= 0) {
        Instruction in = getInstructionAt(ad);
        if (in == null) { disassemble(ad); in = getInstructionAt(ad); }
        if (in == null) {
          Data d = getDataAt(ad);
          pw.println(ad + ": .data " + (d==null? "?" : d.toString()));
          ad = ad.add(2); continue;
        }
        pw.println(ad + ": " + in.toString());
        ad = ad.add(in.getLength());
      }
    }
    pw.close();
  }
}
