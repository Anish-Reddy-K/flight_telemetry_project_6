import time
import uuid

planes = {}

def simulate_update(plane_id):
    plane = planes.setdefault(plane_id, {
        "last_time": time.time(),
        "last_fuel": 5000,
        "total_fuel_used": 0.0,
        "total_time": 0.0,
        "current_rate": None
    })

    new_time = time.time()
    delta_time = new_time - plane["last_time"]
    delta_fuel = 10  # Simulate 10 gal used

    if delta_time > 0:
        plane["total_time"] += delta_time / 3600
        plane["total_fuel_used"] += delta_fuel
        plane["current_rate"] = plane["total_fuel_used"] / plane["total_time"]

    plane["last_time"] = new_time
    plane["last_fuel"] -= delta_fuel

# Simulate 100 planes updating every second
plane_ids = [str(uuid.uuid4()) for _ in range(100)]

start = time.time()
for _ in range(10):  # 10 rounds = 10 seconds
    for pid in plane_ids:
        simulate_update(pid)
    time.sleep(1)
end = time.time()

print(f"Simulated 100 planes for 10 seconds in {end - start:.2f}s")

# Python’s dict lookups are O(1) — they’re super fast.