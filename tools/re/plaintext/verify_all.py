import sys, os, collections
sys.path.insert(0, 'tools/re/plaintext')
import members, bz_plain
st = collections.Counter()
fails = []
for dp, dn, fn in os.walk('extracted'):
    for f in fn:
        p = os.path.join(dp, f)
        with open(p, 'rb') as fh:
            d = fh.read()
        if len(d) < 30 or d[2:3] != b'-' or d[6:7] != b'-':
            continue
        for h, pk, o in members.iter_members(d):
            m = h['method']
            st['n', m] += 1
            st['hcrc', members.header_crc_ok(d, h)] += 1
            st['res21', h['reserved21']] += 1
            if m == '-nc--':
                pl = pk
                st['nc_len_ok', len(pl) == h['orig_size']] += 1
            elif m == '-bz--':
                try:
                    pl = bz_plain.decompress_bz(pk, h['orig_size'])
                except Exception as e:
                    st['bz_err'] += 1
                    fails.append((p, o, str(e), h['name']))
                    continue
                st['bz_ok'] += 1
            else:
                try:
                    pl = bz_plain.decompress_bzw(pk, h['orig_size'])
                except Exception as e:
                    st['bzw_err'] += 1
                    fails.append((p, o, str(e), h['name']))
                    continue
                st['bzw_ok'] += 1
            st['dcrc', m, members.data_crc_ok(h, pl)] += 1
for k, v in sorted(st.items(), key=str):
    print(k, v)
print(fails[:10])
