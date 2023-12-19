import simpy
import random
from simpy.events import AllOf

phases_duration = [8, 3, 5]
cars_waiting_north = []
cars_waiting_south = []
cars_passing = 0
cars_north_to_south = 0
cars_south_to_north = 0
total_time = []
waiting_time = []

class TrafficLight:
    def __init__(self, env, name, duration, is_green):
        self.env = env
        self.name = name
        self.duration = duration
        self.is_green = is_green
    
    def change_state(self):
        global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
        if self.is_green:
            print('Semáforo del %s en verde en el minuto %d' % (self.name, self.env.now))
            yield self.env.timeout(self.duration)
            self.is_green = False
        else:
            print('Semáforo del %s en rojo en el minuto %d' % (self.name, self.env.now))
            yield self.env.timeout(self.duration)
            self.is_green = True
    
    def set_duration(self, new_duration):
        global phases_duration
        phases_duration = new_duration

    def set_state(self, new_state):
        global is_green
        is_green = new_state


class Bridge:
    def __init__(self, env, north_traffic_light, south_traffic_light, phases_duration):
        self.env = env
        self.north_traffic_light = north_traffic_light
        self.south_traffic_light = south_traffic_light
        self.phases_duration = phases_duration
        self.current_phase = 0
        self.arrive_time = 0
        self.leave_time = 0
    
    def change_phase(self):
        global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
        while True:
            north_state_process = self.env.process(self.north_traffic_light.change_state())
            south_state_process = self.env.process(self.south_traffic_light.change_state())

            yield AllOf(self.env, [north_state_process, south_state_process])

            self.current_phase = (self.current_phase + 1) % len(self.phases_duration)

            if self.current_phase == 1:
                self.south_traffic_light.set_state(False)

            if self.current_phase == 2:
                self.north_traffic_light.set_state(False)

            self.north_traffic_light.set_duration(self.phases_duration[self.current_phase])
            self.south_traffic_light.set_duration(self.phases_duration[self.current_phase])
    
    def travel(self, car, direction_from, direction_to):
        global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
        print(f'Carro {car} arrancando desde el {direction_from} en el minuto {self.env.now}...')
        yield self.env.timeout(1)
        if direction_to == 'norte':
            cars_north_to_south += 1
        else:
            cars_south_to_north += 1
        print(f'Carro {car} ha llegado al {direction_to} en el minuto {self.env.now}...')
        self.leave_time = self.env.now
        total_time.append(self.leave_time - self.arrive_time)
        waiting_time.append(self.leave_time - self.arrive_time - 1)
    
    def car_start_time(self, car_pos):
        yield self.env.timeout(7/60) if car_pos == 0 else \
              self.env.timeout(6/60) if car_pos == 1 else \
              self.env.timeout(5/60) if car_pos == 2 else \
              self.env.timeout(4/60)

    def car_arrival(self, direction, num_cars):
        global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
        self.arrive_time = self.env.now
        yield self.env.timeout(random.expovariate(1/3 if direction == 'norte' else 1/5))
        print(f'Carro {num_cars} llegó al {direction} en el minuto {self.env.now}')

        if direction == "norte":
            yield self.env.process(self.travel_to(num_cars, "sur"))
        elif direction == "sur":
            yield self.env.process(self.travel_to(num_cars, "norte"))

    def travel_to(self, car, direction_to):
        global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
        if direction_to == "sur":
            if self.north_traffic_light.is_green:
                cars_waiting_north.append({
                    "car": car,
                    "pos": len(cars_waiting_north)
                })
                cars_passing += 1
                car_queued = cars_waiting_north.pop(0)
                self.env.process(self.car_start_time(car_queued["pos"]))
                yield self.env.process(self.travel(car_queued["car"], "norte", "sur"))
            else:
                cars_waiting_north.append({
                    "car": car,
                    "pos": len(cars_waiting_north)
                })
        elif direction_to == "norte":
            if self.south_traffic_light.is_green:
                cars_waiting_south.append({
                    "car": car,
                    "pos": len(cars_waiting_north)
                })
                cars_passing += 1
                car_queued = cars_waiting_south.pop(0)
                self.env.process(self.car_start_time(car_queued["pos"]))
                yield self.env.process(self.travel(car_queued["car"], "sur", "norte"))
            else:
                cars_waiting_south.append({
                    "car": car,
                    "pos": len(cars_waiting_north)
                })


def run_bridge(env, phases_duration):
    global cars_north_to_south, cars_south_to_north, cars_waiting_north, cars_waiting_south, cars_passing
    north_traffic_light = TrafficLight(env, "norte", 8, True)
    south_traffic_light = TrafficLight(env, "sur", 8, False)
    bridge = Bridge(env, north_traffic_light, south_traffic_light, phases_duration)
    env.process(bridge.change_phase())
    total_cars = 1
    while True:
        # Arrival cars at north
        yield env.process(bridge.car_arrival('norte', total_cars))
        total_cars += 1

        # Arrival cars at south
        yield env.process(bridge.car_arrival('sur', total_cars))
        total_cars += 1

env = simpy.Environment()
env.process(run_bridge(env, phases_duration))
env.run(until=50)


print("\n--- Estadísticas al final de la simulación ---")
print("Número total de autos que pasaron por el puente:", cars_north_to_south + cars_south_to_north)
print("Número de carros que cruzaron al sur", cars_north_to_south)
print("Número de carros que cruzaron al norte", cars_south_to_north)
print("Número de autos que esperaron en dirección norte:", len(cars_waiting_north))
print("Número de autos que esperaron en dirección sur:", len(cars_waiting_south))
print("Tiempo promedio total del sistema:", sum(total_time) / len(total_time))
print("Tiempo promedio de espera (sin contar el tiempo de viaje):", sum(waiting_time) / len(waiting_time))