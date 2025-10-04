import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --- Configuration & Helper Functions ---

TRAIN_PREFIX_MAP = {
    'DUR': {'type': 'Duronto'}, 'GAT': {'type': 'Gatimaan'},
    'RJD': {'type': 'Rajdhani'}, 'RAT': {'type': 'Garib Rath'},
    'EXP': {'type': 'Express'}, 'PSG': {'type': 'Passenger'},
    'PAS': {'type': 'Passenger'}, 'VB': {'type': 'Vande Bharat'},
    'RA': {'type': 'Rajdhani'}, 'TE': {'type': 'Tejas'},
    'SH': {'type': 'Shatabdi'}, 'SF': {'type': 'Superfast'},
    'EX': {'type': 'Express'}, 'SP': {'type': 'Special'},
    'ME': {'type': 'MEMU'}
}

def get_train_type(name):
    """Identifies train type from its name."""
    if not name or not name.split(): return "Unknown"
    last_word = name.split()[-1].upper()
    prefix3, prefix2 = last_word[:3], last_word[:2]
    if prefix3 in TRAIN_PREFIX_MAP: return TRAIN_PREFIX_MAP[prefix3]['type']
    if prefix2 in TRAIN_PREFIX_MAP: return TRAIN_PREFIX_MAP[prefix2]['type']
    if 'MAIL' in name.upper(): return 'Express'
    return "Express" # Default for others

def calculate_halt_time(stations):
    """Calculates total halt time in minutes for a train's journey."""
    total_halt = 0
    FMT = '%H:%M:%S'
    for station in stations:
        if station['arrival'] == "00:00:00" or station['departure'] == "00:00:00":
            continue
        try:
            arrival_time = datetime.strptime(station['arrival'], FMT)
            departure_time = datetime.strptime(station['departure'], FMT)
            
            if departure_time < arrival_time:
                departure_time += timedelta(days=1)
                
            tdelta = departure_time - arrival_time
            total_halt += tdelta.total_seconds() / 60
        except (ValueError, TypeError):
            continue
    return total_halt

def calculate_average_speed(stations):
    """Calculates the overall average speed of a train."""
    if len(stations) < 2:
        return None
    
    start_station = stations[0]
    end_station = stations[-1]
    
    total_distance = end_station['distanceFromOrigin'] - start_station['distanceFromOrigin']
    if total_distance <= 0:
        return None
        
    FMT = '%H:%M:%S'
    try:
        start_time = datetime.strptime(start_station['departure'], FMT)
        end_time = datetime.strptime(end_station['arrival'], FMT)
        
        if end_time < start_time:
            end_time += timedelta(days=1)
            
        total_duration_hours = (end_time - start_time).total_seconds() / 3600
        if total_duration_hours <= 0:
            return None
            
        return total_distance / total_duration_hours
    except (ValueError, TypeError):
        return None

def preprocess_data(data):
    """Processes the raw JSON data into a clean pandas DataFrame."""
    processed_list = []
    for train_id, details in data.items():
        
        stations = sorted(details.get('stations', []), key=lambda x: x['distanceFromOrigin'])

        train_type = get_train_type(details.get('name', ''))
        halt_time = calculate_halt_time(stations)
        avg_speed = calculate_average_speed(stations)
        
        if train_type == 'Express' and avg_speed and avg_speed > 110:
            avg_speed = 110
        
        # --- FIX: Cap unrealistic halt times for better visualization ---
        if halt_time > 300: # Cap halts at 5 hours for the chart
            halt_time = 300
        
        if avg_speed and avg_speed < 200:
             processed_list.append({
                'id': train_id,
                'name': details.get('name', ''),
                'type': train_type,
                'total_halt_minutes': halt_time,
                'average_speed_kmh': avg_speed,
                'num_stops': len(stations)
            })
    return pd.DataFrame(processed_list)

# --- Visualization Functions ---

# --- MODIFIED: Reverted to a clear horizontal bar chart ---
def plot_train_type_barchart(df, output_path="visual_1_train_types.png"):
    """Generates and saves a clear horizontal bar chart of train type distribution."""
    plt.style.use('seaborn-v0_8-whitegrid')
    type_counts = df['type'].value_counts().sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = sns.color_palette("viridis_r", len(type_counts))
    bars = ax.barh(type_counts.index, type_counts.values, color=colors)
    
    ax.set_title('Number of Trains by Type in Dataset', fontsize=18, weight='bold', pad=20)
    ax.set_xlabel('Count of Trains', fontsize=12)
    ax.set_ylabel('Train Type', fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add data labels to each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 3, bar.get_y() + bar.get_height()/2, f'{int(width)}', va='center', ha='left')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"Saved train type bar chart to {output_path}")

def plot_top_halt_times(df, output_path="visual_2_halt_times.png"):
    """Generates and saves a horizontal bar chart for trains with the longest halt times."""
    plt.style.use('seaborn-v0_8-whitegrid')
    top_15_halts = df.nlargest(15, 'total_halt_minutes')
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.barplot(x='total_halt_minutes', y='name', data=top_15_halts, palette='magma', ax=ax)
    
    ax.set_title('Top 15 Trains by Total Scheduled Halt Time', fontsize=18, weight='bold', pad=20)
    ax.set_xlabel('Total Halt Time (Minutes)', fontsize=12)
    ax.set_ylabel('Train Name', fontsize=12)
    
    for p in ax.patches:
        width = p.get_width()
        # Add a '+' for capped values to indicate "and more"
        label = f'{int(width)}+ min' if width >= 300 else f'{int(width)} min'
        ax.text(width + 5, p.get_y() + p.get_height()/2., label, va='center')
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"Saved top halt times chart to {output_path}")

def plot_speed_distribution_raincloud(df, output_path="visual_3_speed_distribution.png"):
    """
    Generates a sophisticated and clear raincloud plot to show speed distribution.
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    
    main_types = ['Rajdhani', 'Shatabdi', 'Superfast', 'Express', 'Passenger', 'Special']
    df_filtered = df[df['type'].isin(main_types)].sort_values(by="average_speed_kmh", ascending=False)
    
    type_order = df_filtered.groupby('type')['average_speed_kmh'].median().sort_values(ascending=False).index

    fig, ax = plt.subplots(figsize=(14, 8))

    sns.violinplot(x='average_speed_kmh', y='type', data=df_filtered, order=type_order,
                   palette='Set2', inner=None, orient='h', ax=ax, cut=0)
    
    sns.stripplot(x='average_speed_kmh', y='type', data=df_filtered, order=type_order,
                  color='black', size=3, alpha=0.5, jitter=0.2, ax=ax)
    
    sns.boxplot(x='average_speed_kmh', y='type', data=df_filtered, order=type_order,
                width=0.15, boxprops={'zorder': 2}, ax=ax, fliersize=0,
                palette=['#DDDDDD']*len(type_order))

    ax.set_title('Speed Distribution by Train Type', fontsize=18, weight='bold', pad=20)
    ax.set_xlabel('Average Speed (km/h)', fontsize=12)
    ax.set_ylabel('Train Type', fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    ax.set_xlim(0, 160)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"Saved improved speed distribution plot to {output_path}")


# --- Main Execution ---
if __name__ == "__main__":
    try:
        with open("train_data_cleaned.json", "r") as file:
            train_data = json.load(file)
    except FileNotFoundError:
        print("Error: 'train_data_cleaned.json' not found. Please ensure it's in the same directory.")
        exit()

    df = preprocess_data(train_data)
    
    # MODIFIED: Call the clearer bar chart function for the first visual
    plot_train_type_barchart(df)
    plot_top_halt_times(df)
    plot_speed_distribution_raincloud(df)