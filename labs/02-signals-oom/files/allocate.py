import os
print("allocator PID=" + str(os.getpid()), flush=True)
a=[]
while True: a.append(b"x"*1000000)
