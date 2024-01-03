from datetime import datetime, timezone # UTC

print(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
