import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
for i in z.infolist():
    print(i.filename, i.file_size, i.date_time, oct(i.external_attr >> 16), i.compress_type, i.flag_bits)
print("testzip:", z.testzip())
