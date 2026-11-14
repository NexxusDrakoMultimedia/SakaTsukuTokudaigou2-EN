import os
import io
p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/tools/apply_patch.py'
s = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")

# 1. preflight helper after read_patch
old = "def apply_vcdiff(src_path, patch, tmp, entry, label):"
new = '''def preflight_patches(man, patch_dir, method, req, to_iso):
    """Check every patch file that the chosen route needs (present, SHA-1) BEFORE anything is written, so that a
    missing or damaged download does not leave a half-written output folder behind."""
    need = []
    if (method == "iso" or to_iso) and man["volume_iso"].get("changed"):
        need.append(man["volume_iso"]["patch"])
    if method == "raw" and not to_iso:
        need.extend(man["tracks"][str(n)]["patch"] for n in req)
    for pe in need:
        read_patch(os.path.join(patch_dir, pe["file"]), pe)


def apply_vcdiff(src_path, patch, tmp, entry, label):'''
assert old in s
s = s.replace(old, new, 1)

# 2. call it in run_raw before output decisions
old = '''    if to_iso:
        out = default_out_iso(disc.sheet, man, a)
        return make_iso_output('''
new = '''    preflight_patches(man, patch_dir, method, req, to_iso)
    if to_iso:
        out = default_out_iso(disc.sheet, man, a)
        return make_iso_output('''
assert old in s
s = s.replace(old, new, 1)

# 3. cleanup on failure
old = '''    os.makedirs(out_dir, exist_ok=True)
    sheet_out = os.path.join(out_dir, os.path.basename(disc.sheet))
    shutil.copyfile(disc.sheet, sheet_out)
    say("  %s: copied" % os.path.basename(disc.sheet))
    if method == "raw":
        for n in sorted(disc.tracks):
            e = man["tracks"][str(n)]
            if e["changed"]:
                write_patched(disc.tracks[n], os.path.join(patch_dir, e["patch"]["file"]), outs[n], e, "track %d" % n,
                              a.overwrite)
            else:
                how = copy_or_link(disc.tracks[n], outs[n], a.link, a.overwrite)
                say("  track %d: unchanged, %s" % (n, how))
    else:
        run_via_iso_tracks(disc, man, a, patch_dir, outs, hashes, reference, out_dir)
'''
new = '''    made_dir = not os.path.isdir(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    sheet_out = os.path.join(out_dir, os.path.basename(disc.sheet))
    fresh = [p for p in [sheet_out] + [outs[n] for n in sorted(outs)] if not os.path.exists(p)]
    try:
        shutil.copyfile(disc.sheet, sheet_out)
        say("  %s: copied" % os.path.basename(disc.sheet))
        if method == "raw":
            for n in sorted(disc.tracks):
                e = man["tracks"][str(n)]
                if e["changed"]:
                    write_patched(disc.tracks[n], os.path.join(patch_dir, e["patch"]["file"]), outs[n], e, "track %d" % n,
                                  a.overwrite)
                else:
                    how = copy_or_link(disc.tracks[n], outs[n], a.link, a.overwrite)
                    say("  track %d: unchanged, %s" % (n, how))
        else:
            run_via_iso_tracks(disc, man, a, patch_dir, outs, hashes, reference, out_dir)
    except BaseException:
        # a failed run must not leave something that looks like a finished disc
        for p in fresh:
            if os.path.exists(p):
                os.remove(p)
        if made_dir:
            try:
                os.rmdir(out_dir)
            except OSError:
                pass
        say("  (the files of this run were removed)")
        raise
'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("ok", repr(nl))
