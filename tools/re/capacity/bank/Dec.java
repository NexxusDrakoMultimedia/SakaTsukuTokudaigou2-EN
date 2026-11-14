import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class Dec extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    String out = a[0];
    PrintWriter pw = new PrintWriter(new FileWriter(out));
    DecompInterface di = new DecompInterface();
    di.openProgram(currentProgram);
    Set<Function> done = new LinkedHashSet<>();
    for (int i = 1; i < a.length; i++) {
      String s = a[i];
      if (s.startsWith("ref:")) {
        Address ad = toAddr(s.substring(4));
        pw.println("== refs to " + ad);
        for (Reference r : getReferencesTo(ad)) {
          pw.println("  from " + r.getFromAddress() + " " + r.getReferenceType());
          Function f = getFunctionContaining(r.getFromAddress());
          if (f != null) done.add(f);
        }
      } else if (s.startsWith("range:")) {
        String[] p = s.substring(6).split("-");
        Address lo = toAddr(p[0]), hi = toAddr(p[1]);
        for (Function f : currentProgram.getFunctionManager().getFunctions(lo, true)) { if (f.getEntryPoint().compareTo(hi) > 0) break; done.add(f); }
      } else {
        Address ad = toAddr(s);
        Function f = getFunctionContaining(ad);
        if (f == null) { disassemble(ad); f = createFunction(ad, null); }
        if (f == null) { pw.println("no func at " + ad); continue; }
        done.add(f);
      }
    }
    for (Function f : done) {
      pw.println("\n//////// " + f.getName() + " @ " + f.getEntryPoint() + " body " + f.getBody().getMinAddress()+"-"+f.getBody().getMaxAddress());
      DecompileResults r = di.decompileFunction(f, 120, monitor);
      if (r.decompileCompleted()) pw.println(r.getDecompiledFunction().getC());
      else pw.println("FAIL " + r.getErrorMessage());
      pw.println("-- callers:");
      for (Reference rr : getReferencesTo(f.getEntryPoint())) pw.println("   " + rr.getFromAddress());
    }
    pw.close();
  }
}
