import simpy
import random
from simpy.events import AllOf
phases_duration = [8, 3, 5]

class TrafficLight:
    def __init__(self, env, name, duration, is_green):
        self.env = env
        self.name = name
        self.duration = duration
        self.is_green = is_green
    
    def change_state(self):
        if self.is_green:
            print('Semáforo del %s en verde en el minuto %d' % (self.name, self.env.now))
            yield self.env.timeout(self.duration)
            self.is_green = False
        
        else:
            print('Semáforo del %s en rojo en el minuto %d' % (self.name, self.env.now))
            yield self.env.timeout(self.duration)
            self.is_green = True
    
    def set_duration(self, new_duration):
        self.duration = new_duration

    def set_state(self, new_state):
        self.is_green = new_state
    


class Bridge:
    def __init__(self, env, north_traffic_light, south_traffic_light, phases_duration):
        self.env = env
        self.north_traffic_light = north_traffic_light
        self.south_traffic_light = south_traffic_light
        self.phases_duration = phases_duration
        self.current_phase = 0
        self.cars_waiting_north = []
        self.cars_waiting_south = []
        self.cars_passing = 0
        self.cars_north_to_south = 0
        self.cars_south_to_north = 0
        self.arrive_time = 0
        self.leave_time = 0
        self.total_time = []
        self.waiting_time = []
    
    def change_phase(self):
        while True:
            north_state_process = self.env.process(self.north_traffic_light.change_state())
            south_state_process = self.env.process(self.south_traffic_light.change_state())

            yield AllOf(self.env, [north_state_process, south_state_process])

            self.current_phase = (self.current_phase + 1) % len(self.phases_duration)

            if self.current_phase == 1 :
                self.south_traffic_light.set_state(False)

            if self.current_phase == 2 :
                self.north_traffic_light.set_state(False)

            self.north_traffic_light.set_duration(self.phases_duration[self.current_phase])
            self.south_traffic_light.set_duration(self.phases_duration[self.current_phase])
    
    def travel(self, car, direction_from, direction_to):
        print(f'Carro {car} arrancando desde el {direction_from} en el minuto {self.env.now}...')
        yield self.env.timeout(1)
        if direction_to == 'norte':
            self.cars_north_to_south += 1
        else:
            self.cars_south_to_north +=1
        print(f'Carro {car} ha llegado al {direction_to} en el minuto {self.env.now}...')
        self.leave_time = self.env.now
        self.total_time.append(self.leave_time - self.arrive_time)
        self.waiting_time.append(self.leave_time - self.arrive_time - 1)
        
    
    def car_start_time(self,  car_pos):
        if car_pos == 0:
            yield self.env.timeout(7/60)
        elif car_pos == 1:
            yield self.env.timeout(6/60)
        elif car_pos == 2:
            yield self.env.timeout(5/60)
        else:
            yield self.env.timeout(4/60)

    def car_arrival(self, direction, num_cars):
        yield self.env.timeout(random.expovariate(1/3 if direction == 'norte' else 1/5))
        print('Carro %s llegó al %s en el minuto %d' % (num_cars, direction, self.env.now))
        self.arrive_time = self.env.now
        if direction == "norte":
            yield self.env.process(self.travel_to(num_cars, "sur"))
        elif direction == "sur":
            yield self.env.process(self.travel_to(num_cars, "norte"))

    def travel_to(self, car, direction_to):

        if direction_to == "sur":
            if self.north_traffic_light.is_green:
                self.cars_waiting_north.append({
                    "car": car,
                    "pos": len(self.cars_waiting_north)
                })
                self.cars_passing += 1
                car_queued = self.cars_waiting_north.pop(0) 
                self.env.process(self.car_start_time(car_queued["pos"]))
                yield self.env.process(self.travel(car_queued["car"], "norte", "sur"))
            else:
                self.cars_waiting_north.append({
                    "car": car,
                    "pos": len(self.cars_waiting_north)
                })

        elif direction_to == "norte":
            if self.south_traffic_light.is_green:
                self.cars_waiting_south.append({
                    "car": car,
                    "pos": len(self.cars_waiting_north)
                })
                self.cars_passing += 1
                car_queued = self.cars_waiting_south.pop(0)
                
                self.env.process(self.car_start_time(car_queued["pos"]))
                yield self.env.process(self.travel(car_queued["car"], "sur", "norte"))
            else:
                self.cars_waiting_south.append({
                    "car": car,
                    "pos": len(self.cars_waiting_north)
                })



def run_bridge(env, phases_duration):

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
    
    # Fin de la simulación, imprimir estadísticas
    print("\n--- Estadísticas al final de la simulación ---")
    print("Número total de autos que pasaron por el puente:", bridge.cars_north_to_south + bridge.cars_south_to_north)
    print("Número de autos que esperaron en dirección norte:", len(bridge.cars_waiting_north))
    print("Número de autos que esperaron en dirección sur:", len(bridge.cars_waiting_south))
    print("Tiempo promedio total de espera:", sum(bridge.total_time) / len(bridge.total_time))
    print("Tiempo promedio de espera (sin contar el tiempo de viaje):", sum(bridge.waiting_time) / len(bridge.waiting_time))

    


env = simpy.Environment()
env.process(run_bridge(env, phases_duration))
env.run(until=50)