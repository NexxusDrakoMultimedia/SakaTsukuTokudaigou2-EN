p = 'tools/re/art6_gen_ss.py'
s = open(p, encoding='utf8').read()
s = s.replace("ink_b = {'mode': 'mask', 'ink': [{'color': [40, 40, 225], 'tol': 130}, {'luma_lt': 75}], 'dilate': 1, 'fill': 'diffuse'}",
              "ink_b = {'mode': 'mask', 'ink': [{'bg_dist_gt': 75, 'bg': [215, 140, 40]}], 'dilate': 1, 'fill': 'diffuse'}\nink_l = {'mode': 'mask', 'ink': [{'luma_gt': 135}, {'luma_lt': 35}], 'dilate': 2, 'fill': 'diffuse'}")
s = s.replace("[116, 152, 178, 26], 'lav', ink_w", "[116, 152, 178, 26], 'lav', ink_l").replace("[116, 188, 178, 24], 'lav', ink_w", "[116, 188, 178, 24], 'lav', ink_l")
s = s.replace("[100, 24, 168, 38], 'bl', ink_b, 30)", "[100, 25, 168, 37], 'bl', ink_b, 30)")
open(p, 'w', encoding='utf8').write(s)
