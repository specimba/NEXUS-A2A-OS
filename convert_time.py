import datetime

ts = 1781400781382 / 1000.0
dt_utc = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
dt_local = datetime.datetime.fromtimestamp(ts)

print("Timestamp:", ts)
print("UTC Time:", dt_utc.strftime('%Y-%m-%d %H:%M:%S.%f'))
print("Local Time:", dt_local.strftime('%Y-%m-%d %H:%M:%S.%f'))
