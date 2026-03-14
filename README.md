# TVARA
## Train Vigilance and AI for Railway Automation

TVARA is an AI-powered decision support system designed to improve traffic management on the Indian Railways network.

The system acts as a **dynamic digital twin of railway sections**, simulating train movements and generating intelligent recommendations to minimize delays and optimize track utilization.

---

# Problem Statement

Railway traffic management faces several operational challenges:

- Heavy reliance on manual decision making
- Cascading delays caused by late trains
- Sub-optimal utilization of track capacity
- Limited tools to simulate future conflicts

TVARA addresses these issues by building a **modular simulation system** capable of modeling railway infrastructure and resolving scheduling conflicts automatically.

---

# System Architecture

TVARA operates through a modular pipeline that simulates train movement and resolves conflicts.

## Priority Score Model

- Calculates the dynamic importance of trains
- Factors considered:
  - Train type
  - Real-time delay
  - Custom bias parameters
- Used to determine which train should receive priority during conflicts

## Block System Model

- Represents the railway track as discrete blocks
- Only one train can occupy a block at a time
- Mirrors real-world railway signaling systems
- Forms the foundation of the simulation environment

## Simulation Engine

- Core orchestrator of the system
- Responsibilities include:
  - Advancing system time
  - Tracking block occupancy
  - Detecting train conflicts
  - Simulating train movement

## Platform Availability & Conflict Resolution

- Detects available station platforms
- Uses priority scores to resolve conflicts
- Generates recommendations such as:
  - Holding lower-priority trains
  - Allowing higher-priority trains to pass first
  - Allocating alternative platforms

## Scheduling & Re-optimization Model

- Applies conflict resolution decisions
- Updates the original timetable
- Propagates delays realistically
- Generates an optimized updated schedule

---

# Key Features

- Digital twin simulation of railway sections
- Intelligent conflict detection
- Dynamic train prioritization
- Platform availability modeling
- Schedule re-optimization
- Realistic delay propagation

---

# Tech Stack

- Python
- Pandas
- Flask
- Next.js
- Tailwind CSS

---

# Benefits

## Increased Throughput

- Improves track utilization
- Can increase the number of trains operating on a section by up to **15%**

## Reduced Delays

- Prevents cascading delays
- Minimizes unnecessary hold times

## Cost Efficiency

- Reduces unnecessary stops
- Leads to:
  - Lower fuel consumption
  - Reduced wear on rolling stock

## Enhanced Safety

- Provides data-driven recommendations
- Helps reduce human error in traffic management

---

# Future Improvements

Planned enhancements include:

- Integration of economic factors
  - Cargo value
  - Fuel consumption

- Machine learning integration
  - Predictive delay analysis
  - Traffic demand prediction

- Multi-section coordination
  - Network-wide optimization
  - Inter-section scheduling

---

