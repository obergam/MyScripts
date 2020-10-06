import datetime

gLogTime = datetime.datetime.now()
gStartTime = gLogTime.strftime('%m-%d-%Y_%H:%M:%S')
gBatchID = gStartTime

tcClassName = '_'.join(gBatchID.split('_')[:-1])

print(gStartTime)
# print(tcClassName)