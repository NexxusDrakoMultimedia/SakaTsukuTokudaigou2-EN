import os
p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/tools/release.py'
s = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")
old = '''    if not a.date or not re.match(r"^\d{4}-\d{2}-\d{2}$", a.date):
        fail("--date YYYY-MM-DD is required")
'''
new = '''    if not a.date or not re.match(r"^\d{4}-\d{2}-\d{2}$", a.date):
        fail("--date YYYY-MM-DD is required")
    try:
        import datetime
        if datetime.date(*(int(x) for x in a.date.split("-"))).year < 1980:      # zip entries cannot hold earlier dates
            raise ValueError("year before 1980")
    except ValueError as e:
        fail("--date %s is not a real calendar date (%s)" % (a.date, e))
'''
assert old in s, "x"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
