from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import uvicorn
import json


class SimulationRequest(BaseModel):
    start_station: str
    end_station: str
    train_ids: list[str]

#  main App setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Loading ---
def load_train_data():
    try:
        with open("train_data_cleaned.json", "r", encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"❌ Critical Error: Could not load train_data_cleaned.json. Details: {e}")
        return None

all_trains_data = load_train_data()

# --- All Backend Models Integrated Here ---

# (Priority Model Logic)
TRAIN_PREFIX_MAP = {
    'DUR': {'type': 'Duronto', 'official_priority': 4, 'speed_kmh': 95}, 'GAT': {'type': 'Gatimaan', 'official_priority': 6, 'speed_kmh': 120},
    'RJD': {'type': 'Rajdhani', 'official_priority': 2, 'speed_kmh': 100}, 'RAT': {'type': 'Garib Rath', 'official_priority': 7, 'speed_kmh': 85},
    'EXP': {'type': 'Express', 'official_priority': 8, 'speed_kmh': 65}, 'PSG': {'type': 'Passenger', 'official_priority': 13, 'speed_kmh': 45},
    'PAS': {'type': 'Passenger', 'official_priority': 13, 'speed_kmh': 45}, 'VB': {'type': 'Vande Bharat', 'official_priority': 1, 'speed_kmh': 110},
    'RA': {'type': 'Rajdhani', 'official_priority': 2, 'speed_kmh': 100}, 'TE': {'type': 'Tejas', 'official_priority': 3, 'speed_kmh': 105},
    'SH': {'type': 'Shatabdi', 'official_priority': 5, 'speed_kmh': 100}, 'SF': {'type': 'Superfast', 'official_priority': 9, 'speed_kmh': 75},
    'EX': {'type': 'Express', 'official_priority': 8, 'speed_kmh': 65}, 'SP': {'type': 'Special', 'official_priority': 11, 'speed_kmh': 60},
    'ME': {'type': 'Express', 'official_priority': 8, 'speed_kmh': 55}
}
STATION_PLATFORM_CONFIG = { 'NDLS': 16, 'MTJ': 10, 'AGC': 10, 'JAT': 5, 'VSP': 1, 'CNB': 10 }

def get_train_attributes(name):
    if not name or not name.split(): return {"type": "Unknown", "official_priority": 10, "speed_kmh": 65}
    last_word = name.split()[-1].upper()
    prefix3, prefix2 = last_word[:3], last_word[:2]
    if prefix3 in TRAIN_PREFIX_MAP: return TRAIN_PREFIX_MAP[prefix3]
    if prefix2 in TRAIN_PREFIX_MAP: return TRAIN_PREFIX_MAP[prefix2]
    return {"type": "Express", "official_priority": 10, "speed_kmh": 65}

def filter_trains_for_section(all_train_data, start_code, end_code):
    section_trains = {}
    for train_id, train_details in all_train_data.items():
        station_codes = [s.get('code') for s in train_details.get('stations', [])]
        try:
            if start_code in station_codes and end_code in station_codes:
                if station_codes.index(start_code) < station_codes.index(end_code):
                    section_trains[train_id] = train_details
        except (ValueError, IndexError):
            continue
    return section_trains

# (Block System, Platform, Conflict, and Scheduling Models)
class TrackBlock:
    def __init__(self, block_id, start_km, end_km): self.id, self.start_km, self.end_km, self.is_occupied, self.occupied_by_train = block_id, start_km, end_km, False, None
    def occupy(self, train_id):
        if self.is_occupied and self.occupied_by_train != train_id: raise ValueError(f"Train {train_id} cannot enter Block {self.id}. Occupied by {self.occupied_by_train}.")
        self.is_occupied, self.occupied_by_train = True, train_id
    def release(self): self.is_occupied, self.occupied_by_train = False, None

class SectionController:
    def __init__(self, all_train_data, start_code, end_code, block_length_km=5.0):
        self.start_code, self.end_code, self.section_stations = start_code, end_code, {}
        self.blocks = self._generate_blocks(all_train_data, block_length_km)
        self.block_map = {block.id: block for block in self.blocks}
    def _get_station_data(self, train_stations, station_code):
        for station in train_stations:
            if station.get('code') == station_code: return station
        return None
    def _generate_blocks(self, all_train_data, block_length_km):
        ref_train_stations = None
        for train_details in all_train_data.values():
            stations = train_details.get('stations', [])
            station_codes = [s.get('code') for s in stations]
            if self.start_code in station_codes and self.end_code in station_codes:
                if station_codes.index(self.start_code) < station_codes.index(self.end_code):
                    ref_train_stations = stations
                    break
        if not ref_train_stations: raise ValueError(f"No reference train found traveling in the direction {self.start_code} -> {self.end_code}.")
        start_station, end_station = self._get_station_data(ref_train_stations, self.start_code), self._get_station_data(ref_train_stations, self.end_code)
        if not start_station or not end_station: raise ValueError("Start or end station not found in reference train's route.")
        start_dist, end_dist = float(start_station['distanceFromOrigin']), float(end_station['distanceFromOrigin'])
        if start_dist >= end_dist: raise ValueError(f"Start station {self.start_code} is at or after end station {self.end_code} in the reference route.")
        for station in ref_train_stations:
            dist = float(station['distanceFromOrigin'])
            if start_dist <= dist <= end_dist: self.section_stations[station['code']] = dist
        section_blocks, current_km, block_num = [], start_dist, 1
        while current_km < end_dist:
            block_end_km = min(current_km + block_length_km, end_dist)
            section_blocks.append(TrackBlock(f"B{block_num:03d}", current_km, block_end_km))
            current_km, block_num = block_end_km, block_num + 1
        return section_blocks
    def get_block_for_position(self, position_km):
        for block in self.blocks:
            if block.start_km <= position_km < block.end_km: return block
        return self.blocks[-1] if position_km >= self.blocks[-1].end_km else None

class PlatformAvailabilityModel:
    def __init__(self, station_config): self.station_config, self.platform_bookings = station_config, {sc: [] for sc in station_config}
    def is_platform_available(self, station_code, check_arrival, check_departure):
        if station_code not in self.station_config: return False
        num_platforms, overlapping = self.station_config[station_code], 0
        for _, ba, bd in self.platform_bookings[station_code]:
            if check_arrival < bd and check_departure > ba: overlapping += 1
        return overlapping < num_platforms

class ConflictResolutionModel:
    def make_decision(self, train_A, train_B, hold_station):
        train_to_proceed, train_to_hold = (train_A, train_B) if train_A.priority_score >= train_B.priority_score else (train_B, train_A)
        return {"action": "HOLD", "train_to_hold": train_to_hold.id, "train_to_proceed": train_to_proceed.id, "hold_at_station": hold_station}

class SchedulingModel:
    def __init__(self, original_train_data): self.original_train_data = original_train_data
    def apply_delay(self, train_id, station_code, delay_minutes):
        train_schedule = self.original_train_data.get(train_id, {}).get('stations', [])
        updated_schedule, delay_active = [], False
        for station_stop in train_schedule:
            current_stop = station_stop.copy()
            if current_stop['code'] == station_code: delay_active = True
            if delay_active and delay_minutes > 0:
                for key in ['arrival', 'departure']:
                    if current_stop[key] != "00:00:00":
                        try:
                            time_obj = datetime.strptime(current_stop[key], '%H:%M:%S')
                            current_stop[key] = (time_obj + timedelta(minutes=delay_minutes)).strftime('%H:%M:%S')
                        except ValueError: pass
            updated_schedule.append({"station": current_stop['code'], "name": current_stop.get('name', ''), "arr": current_stop['arrival'], "dep": current_stop['departure']})
        return updated_schedule
    def get_original_schedule(self, train_id):
        return [{"station": s['code'], "name": s.get('name', ''), "arr": s['arrival'], "dep": s['departure']} for s in self.original_train_data.get(train_id, {}).get('stations', [])]

class Train:
    def __init__(self, train_id, start_pos_km, departure_time_str, speed_kmh, priority_score):
        self.id, self.position_km = train_id, start_pos_km
        self.speed_kmh, self.priority_score = speed_kmh, priority_score
        self.scheduled_departure_time, self.status = departure_time_str, "SCHEDULED"
        self.current_block_id = None
        self.waiting_for_train_id = None
        self.hold_start_time = None
    def update_position(self, time_step_minutes):
        if self.status == "RUNNING": self.position_km += (self.speed_kmh / 60.0) * time_step_minutes

class Simulation:
    def __init__(self, section_controller, platform_model, resolution_model, section_trains_data):
        self.section, self.platform_model, self.resolution_model = section_controller, platform_model, resolution_model
        if not self.section.blocks: raise ValueError("Cannot initialize simulation: Track section has no blocks.")
        self.trains = self._initialize_trains(section_trains_data)
        self.train_map = {t.id: t for t in self.trains}
        self.events = []
        if not self.trains: return
        dep_times = [t.scheduled_departure_time for t in self.trains if t.scheduled_departure_time]
        if not dep_times: raise ValueError("Cannot start simulation: No valid departure times for selected trains.")
        first_departure = min(dep_times)
        self.sim_time = datetime.strptime(f"{datetime.now().strftime('%Y-%m-%d')} {first_departure}", '%Y-%m-%d %H:%M:%S') - timedelta(minutes=1)

    def _initialize_trains(self, section_trains_data):
        train_objects, start_pos, start_code = [], self.section.blocks[0].start_km, self.section.start_code
        sorted_train_data = sorted(section_trains_data.values(), key=lambda t: next((s['departure'] for s in t['stations'] if s['code'] == start_code), "23:59:59"))
        for details in sorted_train_data:
            departure_time = next((s['departure'] for s in details['stations'] if s['code'] == start_code), None)
            if departure_time:
                attributes = get_train_attributes(details.get("name", ""))
                priority_score = 1 / attributes.get('official_priority', 10)
                train_objects.append(Train(details['id'], start_pos, departure_time, attributes['speed_kmh'], priority_score))
        return train_objects
    
    def _find_nearby_available_station(self, train):
        sorted_stations = sorted(self.section.section_stations.items(), key=lambda item: item[1])
        for station_code, station_km in sorted_stations:
            if station_km > train.position_km + 2: 
                if self.platform_model.is_platform_available(station_code, self.sim_time, self.sim_time + timedelta(minutes=15)):
                    return station_code
        return None
    
    def run(self, duration_minutes=360, time_step_minutes=1):
        if not self.trains: return
        for _ in range(duration_minutes):
            self.sim_time += timedelta(minutes=time_step_minutes)
            sorted_trains = sorted([t for t in self.trains if t.status != 'COMPLETED'], key=lambda x: x.position_km, reverse=True)
            for train in sorted_trains:
                if train.status in ["COMPLETED", "HOLDING"]: continue
                if train.status == "SCHEDULED" and self.sim_time.strftime('%H:%M:%S') >= train.scheduled_departure_time:
                    if not self.section.blocks[0].is_occupied: train.status = "RUNNING"
                if train.status == "RUNNING":
                    old_pos = train.position_km
                    train.update_position(time_step_minutes)
                    new_block = self.section.get_block_for_position(train.position_km)
                    if train.position_km >= self.section.blocks[-1].end_km:
                        train.status = "COMPLETED"
                        if train.current_block_id in self.section.block_map: self.section.block_map[train.current_block_id].release()
                        continue
                    if new_block and new_block.id != train.current_block_id:
                        try:
                            new_block.occupy(train.id)
                            if train.current_block_id in self.section.block_map: self.section.block_map[train.current_block_id].release()
                            train.current_block_id = new_block.id
                        except ValueError:
                            train.position_km = old_pos
                            occupant = self.train_map[new_block.occupied_by_train]
                            hold_station = self._find_nearby_available_station(train)
                            if hold_station:
                                decision = self.resolution_model.make_decision(occupant, train, hold_station)
                                held_train = self.train_map[decision['train_to_hold']]
                                held_train.status = "HOLDING"
                                held_train.waiting_for_train_id = decision['train_to_proceed']
                                held_train.hold_start_time = self.sim_time
                                self.events.append(decision)
            for train in self.trains:
                if train.status == "HOLDING":
                    passing_train = self.train_map.get(train.waiting_for_train_id)
                    if not passing_train or passing_train.status == "COMPLETED" or passing_train.position_km > train.position_km + 15:
                        train.status = "RUNNING"
                        delay_duration = (self.sim_time - train.hold_start_time).total_seconds() / 60
                        event = next((e for e in self.events if e.get('train_to_hold') == train.id and 'delay_minutes' not in e), None)
                        if event: event['delay_minutes'] = round(delay_duration)
            if not any(t.status in ["SCHEDULED", "RUNNING", "HOLDING"] for t in self.trains): break


# --- API Endpoints ---
@app.get("/")
def read_root(): return {"message": "Train Control API is running."}

@app.get("/api/trains/section")
def get_section_trains(start_station: str = "NDLS", end_station: str = "MTJ"):
    if not all_trains_data: raise HTTPException(status_code=500, detail="Train data could not be loaded on the server.")
    section_trains = filter_trains_for_section(all_trains_data, start_station, end_station)
    processed_list = []
    for train_id, details in section_trains.items():
        attributes = get_train_attributes(details.get("name", ""))
        enriched_train = {**details, **attributes}
        processed_list.append(enriched_train)
    return processed_list

@app.post("/api/run-simulation")
def run_simulation_endpoint(request: SimulationRequest):
    if not all_trains_data: raise HTTPException(status_code=500, detail="Train data could not be loaded on the server.")
    section_trains_data = {tid: all_trains_data[tid] for tid in request.train_ids if tid in all_trains_data}
    if len(section_trains_data) != len(request.train_ids): raise HTTPException(status_code=404, detail="One or more of the provided train IDs were not found in the database.")

    try:
        section_controller = SectionController(all_trains_data, request.start_station, request.end_station)
        platform_model = PlatformAvailabilityModel(STATION_PLATFORM_CONFIG)
        resolution_model = ConflictResolutionModel()
        scheduler = SchedulingModel(all_trains_data)
        simulation = Simulation(section_controller, platform_model, resolution_model, section_trains_data)
        simulation.run()

        recommendations = []
        schedules = {}
        
        delayed_trains = set()
        for event in simulation.events:
            if event['action'] == 'HOLD':
                delay_mins = event.get('delay_minutes', 10)
                train_id = event['train_to_hold']
                station = event['hold_at_station']
                recommendations.append({"train": train_id, "action": "HOLD", "at": station, "duration_minutes": delay_mins, "reason": f"Overtake by higher-priority train {event['train_to_proceed']}."})
                schedules[train_id] = {
                    "original": scheduler.get_original_schedule(train_id),
                    "updated": scheduler.apply_delay(train_id, station, delay_mins)
                }
                delayed_trains.add(train_id)
        
        for train_id in request.train_ids:
            if train_id not in delayed_trains:
                schedules[train_id] = {
                    "original": scheduler.get_original_schedule(train_id),
                    "updated": scheduler.get_original_schedule(train_id) # No delay, so updated is same as original
                }

        return { "timestamp": datetime.now().isoformat(), "section": f"{request.start_station}-{request.end_station}", "recommendations": recommendations, "schedules": schedules }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during simulation: {e}")

# --- Server Execution ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

