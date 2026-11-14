import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
// args: out lo hi  -> list functions with body range and number of callers
public class ListF extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter pw = new PrintWriter(new FileWriter(a[0]));
    Address lo = toAddr(a[1]), hi = toAddr(a[2]);
    for (Function f : currentProgram.getFunctionManager().getFunctions(lo, true)) {
      if (f.getEntryPoint().compareTo(hi) > 0) break;
      int n = 0; for (Reference r : getReferencesTo(f.getEntryPoint())) n++;
      pw.println(f.getEntryPoint() + " " + f.getBody().getMinAddress() + "-" + f.getBody().getMaxAddress() + " refs=" + n);
    }
    pw.close();
  }
}
