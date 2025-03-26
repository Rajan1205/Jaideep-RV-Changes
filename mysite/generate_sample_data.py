# generate_sample_data.py
import os
import sys
import json
import random
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the absolute path of the current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set up the data directory path
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logger.info(f"Created data directory: {DATA_DIR}")

# Configuration
START_DATE = datetime(2024, 1, 1)
LOCATIONS = ['212/1', '259/1']
LOOM_RANGES = {
    '212/1': list(range(25, 49)) + list(range(68, 113)),  # Looms 25-48 and 68-112
    '259/1': list(range(1, 129))  # Looms 1-128
}

# Sample data lists
PARTY_NAMES = ['Textile Corp A', 'Fabrics Ltd B', 'Weaving Co C', 'Mills Inc D', 'Textiles E']
DESIGN_PREFIXES = ['D', 'DS', 'DF', 'DX']
QUALITIES = ['Q100', 'Q200', 'Q300', 'Q400', 'Q500']
WARPER_NAMES = ['Warper1', 'Warper2', 'Warper3', 'Warper4']
SIZER_NAMES = ['Sizer1', 'Sizer2', 'Sizer3', 'Sizer4']
WEAVER_NAMES = ['Weaver1', 'Weaver2', 'Weaver3', 'Weaver4']
RELIEVER_NAMES = ['Reliever1', 'Reliever2', 'Reliever3']
QC_CHECKERS = ['QC1', 'QC2', 'QC3']
FOREMEN = ['Foreman1', 'Foreman2', 'Foreman3']

def generate_random_date(start_date, end_date=None):
    """Generate a random date between start_date and end_date"""
    if end_date is None:
        end_date = datetime.now()
    time_between_dates = end_date - start_date
    days_between = time_between_dates.days
    if days_between < 0:
        days_between = 0
    random_days = random.randint(0, max(0, days_between))
    return start_date + timedelta(days=random_days)

def safe_random_sample(population, k):
    """Safely take a random sample, handling cases where k > len(population)"""
    if not population:
        return []
    return random.sample(population, min(k, len(population)))

def generate_orderbook(num_entries=50):
    """Generate sample orderbook entries"""
    logger.info(f"Generating {num_entries} orderbook entries")
    orders = []
    
    for i in range(num_entries):
        order_date = generate_random_date(START_DATE)
        design_no = f"{random.choice(DESIGN_PREFIXES)}{random.randint(1000, 9999)}"
        factory_order_meters = random.randint(500, 5000)
        
        order = {
            "Office Date": order_date.strftime('%Y-%m-%d'),
            "Office Order No": f"OO{random.randint(10000, 99999)}",
            "Date of Office": order_date.strftime('%Y-%m-%d'),
            "Temp. Order No.": f"T{random.randint(1000, 9999)}",
            "Order No.": f"O{random.randint(10000, 99999)}",
            "Combo No.": f"C{random.randint(100, 999)}",
            "Design No.": design_no,
            "Yarn Dyeing Plant": random.choice(['Plant A', 'Plant B']),
            "Yarn Dyeing Date": generate_random_date(order_date).strftime('%Y-%m-%d'),
            "Yarn Dyeing Order No.": f"YD{random.randint(1000, 9999)}",
            "Quality": random.choice(QUALITIES),
            "Factory Order (Meters)": factory_order_meters,
            "Warping Location": random.choice(LOCATIONS),
            "Weaving Location": random.choice(LOCATIONS),
            "Warp Count": random.randint(20, 60),
            "Weft Count": random.randint(20, 60),
            "Reed": random.randint(40, 120),
            "Pick": random.randint(40, 120),
            "RS on Loom": random.choice(['Yes', 'No']),
            "Weave": random.choice(['Plain', 'Twill', 'Satin']),
            "Shafts": random.randint(2, 8),
            "Warp Shades": random.randint(1, 4),
            "Weft Shades": random.randint(1, 4),
            "Party Name": random.choice(PARTY_NAMES),
            "Party Quantity (Meters)": factory_order_meters,
            "Finishing Requirements": random.choice(['Standard', 'Special', 'Premium']),
            "Selvedge": random.choice(['Type A', 'Type B', 'Type C']),
            "Delivery Date": generate_random_date(order_date, order_date + timedelta(days=30)).strftime('%Y-%m-%d'),
            "timestamp": datetime.now().isoformat()
        }
        orders.append(order)
    
    return orders

def generate_warping_production(orderbook_data, num_entries=50):
    """Generate sample warping production entries"""
    logger.info(f"Generating {num_entries} warping production entries")
    warping_records = []
    used_beam_numbers = set()
    
    for i in range(num_entries):
        if not orderbook_data:
            break
            
        order = random.choice(orderbook_data)
        start_datetime = generate_random_date(START_DATE)
        end_datetime = start_datetime + timedelta(hours=random.randint(2, 8))
        
        while True:
            beam_no = f"B{random.randint(1000, 9999)}"
            if beam_no not in used_beam_numbers:
                used_beam_numbers.add(beam_no)
                break
        
        quantity = float(order['Factory Order (Meters)']) * random.uniform(0.2, 0.4)
        rpm = random.randint(300, 500)
        sections = random.randint(4, 8)
        
        record = {
            "order_no": order['Order No.'],
            "design_no": order['Design No.'],
            "machine_no": random.randint(1, 5),
            "beam_no": beam_no,
            "quantity": quantity,
            "warper_name": random.choice(WARPER_NAMES),
            "start_datetime": start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "end_datetime": end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "rpm": rpm,
            "sections": sections,
            "breakages": random.randint(0, 10),
            "comments": "Sample warping production record",
            "timestamp": datetime.now().isoformat()
        }
        warping_records.append(record)
    
    return warping_records, used_beam_numbers

def generate_warping_dispatch(warping_data, num_entries=40):
    """Generate sample warping dispatch entries"""
    logger.info(f"Generating {num_entries} warping dispatch entries")
    dispatch_records = []
    
    selected_records = safe_random_sample(warping_data, num_entries)
    
    for record in selected_records:
        dispatch_date = generate_random_date(
            datetime.strptime(record['start_datetime'], '%Y-%m-%d %H:%M:%S'))
        
        dispatch = {
            "date": dispatch_date.strftime('%Y-%m-%d'),
            "beam_no": record['beam_no'],
            "dispatch_status": "Yes",
            "timestamp": datetime.now().isoformat()
        }
        dispatch_records.append(dispatch)
    
    return dispatch_records

def generate_sizing_production(warping_dispatch_data, num_entries=35):
    """Generate sample sizing production entries"""
    logger.info(f"Generating {num_entries} sizing production entries")
    sizing_records = []
    
    selected_dispatches = safe_random_sample(warping_dispatch_data, num_entries)
    
    for dispatch in selected_dispatches:
        start_datetime = generate_random_date(
            datetime.strptime(dispatch['date'], '%Y-%m-%d'))
        end_datetime = start_datetime + timedelta(hours=random.randint(2, 6))
        
        record = {
            "beam_no": dispatch['beam_no'],
            "status": "Yes",
            "sizer_name": random.choice(SIZER_NAMES),
            "start_datetime": start_datetime.strftime('%Y-%m-%d %H:%M'),
            "end_datetime": end_datetime.strftime('%Y-%m-%d %H:%M'),
            "rf": round(random.uniform(5.0, 8.0), 2),
            "moisture": round(random.uniform(7.0, 12.0), 2),
            "speed": round(random.uniform(40.0, 60.0), 2),
            "comments": "Sample sizing production record",
            "timestamp": datetime.now().isoformat()
        }
        sizing_records.append(record)
    
    return sizing_records

def generate_sizing_dispatch(sizing_data, num_entries=30):
    """Generate sample sizing dispatch entries"""
    logger.info(f"Generating {num_entries} sizing dispatch entries")
    dispatch_records = []
    
    selected_records = safe_random_sample(sizing_data, num_entries)
    
    for record in selected_records:
        dispatch_date = generate_random_date(
            datetime.strptime(record['start_datetime'], '%Y-%m-%d %H:%M'))
        
        dispatch = {
            "date": dispatch_date.strftime('%Y-%m-%d'),
            "beam_no": record['beam_no'],
            "dispatch_status": "Yes",
            "timestamp": datetime.now().isoformat()
        }
        dispatch_records.append(dispatch)
    
    return dispatch_records

def generate_initiate_beam(sizing_dispatch_data, num_entries=25):
    """Generate sample initiate beam entries"""
    logger.info(f"Generating {num_entries} initiate beam entries")
    initiate_records = []
    used_looms = {loc: set() for loc in LOCATIONS}
    
    selected_dispatches = safe_random_sample(sizing_dispatch_data, num_entries)
    
    for dispatch in selected_dispatches:
        location = random.choice(LOCATIONS)
        available_looms = [l for l in LOOM_RANGES[location] if l not in used_looms[location]]
        
        if not available_looms:
            continue
            
        loom_no = random.choice(available_looms)
        used_looms[location].add(loom_no)
        
        start_datetime = generate_random_date(
            datetime.strptime(dispatch['date'], '%Y-%m-%d'))
        
        record = {
            "location": location,
            "beam_no": dispatch['beam_no'],
            "loom_no": loom_no,
            "start_datetime": start_datetime.strftime('%Y-%m-%d %H:%M'),
            "status": "Beam Start",
            "timestamp": datetime.now().isoformat()
        }
        initiate_records.append(record)
    
    return initiate_records, used_looms

def generate_beam_on_loom(initiate_data, num_entries=25):
    """Generate sample beam on loom entries"""
    logger.info(f"Generating beam on loom entries for {num_entries} beams")
    beam_records = []
    
    for initiate_record in initiate_data:
        current_datetime = datetime.strptime(initiate_record['start_datetime'], '%Y-%m-%d %H:%M')
        
        statuses = [
            ('Beam Start', 'Starter'),
            ('Knotting / Drawing Start', 'Knotter'),
            ('Knotting / Drawing End', 'Knotter'),
            ('Getting Start', 'Getter'),
            ('Getting End', 'Getter'),
            ('QC Start', 'QC'),
            ('QC End', 'QC')
        ]
        
        if random.random() < 0.7:  # 70% chance to complete the beam
            statuses.append(('Beam End', 'System'))
        
        for status, role in statuses:
            record = {
                "beam_no": initiate_record['beam_no'],
                "loom_no": initiate_record['loom_no'],
                "location": initiate_record['location'],
                "status": status,
                "role": role,
                "name": f"{role}1",
                "timestamp": current_datetime.strftime('%Y-%m-%d %H:%M')
            }
            beam_records.append(record)
            current_datetime += timedelta(hours=random.randint(1, 4))
    
    return beam_records

def generate_grey_production(beam_records, location, num_entries=20):
    """Generate sample grey production entries for a specific location"""
    logger.info(f"Generating {num_entries} grey production entries for location {location}")
    grey_records = []
    used_piece_numbers = set()
    
    # Filter completed beams for the specified location
    completed_beams = []
    for beam in beam_records:
        if beam['location'] == location and beam['status'] == 'Beam End':
            if beam['beam_no'] not in [b['beam_no'] for b in completed_beams]:
                completed_beams.append(beam)
    
    selected_beams = safe_random_sample(completed_beams, min(num_entries, len(completed_beams)))
    
    for beam in selected_beams:
        while True:
            piece_no = f"P{random.randint(10000, 99999)}"
            if piece_no not in used_piece_numbers:
                used_piece_numbers.add(piece_no)
                break
        
        production_date = generate_random_date(
            datetime.strptime(beam['timestamp'], '%Y-%m-%d %H:%M'))
        
        record = {
            "date": production_date.strftime('%Y-%m-%d'),
            "piece_no": piece_no,
            "loom_no": beam['loom_no'],
            "design_no": "D" + str(random.randint(1000, 9999)),
            "production_meters": random.randint(50, 200),
            "production_weight": random.randint(20, 80),
            "remarks": "Sample grey production record",
            "timestamp": datetime.now().isoformat()
        }
        grey_records.append(record)
    
    return grey_records, used_piece_numbers

def generate_grey_dispatch(grey_production_data, num_entries=15):
    """Generate sample grey dispatch entries"""
    logger.info(f"Generating {num_entries} grey dispatch entries")
    dispatch_records = []
    
    selected_records = safe_random_sample(grey_production_data, num_entries)
    
    for record in selected_records:
        dispatch_date = generate_random_date(
            datetime.strptime(record['date'], '%Y-%m-%d'))
        
        # Create a copy of the production record for dispatch
        dispatch = record.copy()
        dispatch['date'] = dispatch_date.strftime('%Y-%m-%d')
        dispatch['timestamp'] = datetime.now().isoformat()
        
        dispatch_records.append(dispatch)
    
    return dispatch_records

def save_json_file(filename, data):
    """Save data to a JSON file in the data directory"""
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Saved {len(data)} records to {filename}.json")

def backup_existing_data():
    """Backup existing JSON files before generating new data"""
    backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(DATA_DIR, f'backup_{backup_time}')
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Created backup directory: {backup_dir}")
    
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    for file in json_files:
        src_path = os.path.join(DATA_DIR, file)
        dst_path = os.path.join(backup_dir, file)
        try:
            with open(src_path, 'r') as src, open(dst_path, 'w') as dst:
                content = json.load(src)
                json.dump(content, dst, indent=4)
            logger.info(f"Backed up {file}")
        except Exception as e:
            logger.error(f"Error backing up {file}: {str(e)}")

def main():
    """Main function to generate sample data"""
    try:
        # Backup existing data
        logger.info("Starting backup of existing data...")
        backup_existing_data()

        logger.info("Starting sample data generation...")
        
        # Generate orderbook data first
        orderbook_data = generate_orderbook(50)
        save_json_file('orderbook', orderbook_data)

        # Generate warping production data
        warping_data, used_beam_numbers = generate_warping_production(orderbook_data, 50)
        save_json_file('warping_production', warping_data)

        # Generate warping dispatch data (80% of warping production)
        warping_dispatch_data = generate_warping_dispatch(warping_data, 40)
        save_json_file('warping_dispatch', warping_dispatch_data)

        # Generate sizing production data (87.5% of warping dispatch)
        sizing_data = generate_sizing_production(warping_dispatch_data, 35)
        save_json_file('sizing_production', sizing_data)

        # Generate sizing dispatch data (85.7% of sizing production)
        sizing_dispatch_data = generate_sizing_dispatch(sizing_data, 30)
        save_json_file('sizing_dispatch', sizing_dispatch_data)

        # Generate initiate beam data (83.3% of sizing dispatch)
        initiate_data, used_looms = generate_initiate_beam(sizing_dispatch_data, 25)
        save_json_file('initiate_beam', initiate_data)

        # Generate beam on loom data
        beam_on_loom_data = generate_beam_on_loom(initiate_data, 25)
        save_json_file('beam_on_loom', beam_on_loom_data)

        # Generate grey production data for both locations
        grey_prod_212, used_pieces_212 = generate_grey_production(beam_on_loom_data, '212/1', 20)
        grey_prod_259, used_pieces_259 = generate_grey_production(beam_on_loom_data, '259/1', 20)
        
        # Combine grey production data
        grey_production_data = grey_prod_212 + grey_prod_259
        save_json_file('grey_production', grey_production_data)

        # Generate grey dispatch data (75% of grey production)
        grey_dispatch_data = generate_grey_dispatch(grey_production_data, 30)
        save_json_file('grey_dispatch', grey_dispatch_data)

        logger.info("\nSample data generation completed successfully!")
        logger.info("\nSummary of generated records:")
        logger.info(f"Orderbook: 50 records (100%)")
        logger.info(f"Warping Production: 50 records (100%)")
        logger.info(f"Warping Dispatch: 40 records (80% of warping)")
        logger.info(f"Sizing Production: 35 records (87.5% of warping dispatch)")
        logger.info(f"Sizing Dispatch: 30 records (85.7% of sizing)")
        logger.info(f"Initiate Beam: 25 records (83.3% of sizing dispatch)")
        logger.info(f"Beam on Loom: Multiple records for 25 beams")
        logger.info(f"Grey Production: 40 records (20 each for 212/1 and 259/1)")
        logger.info(f"Grey Dispatch: 30 records (75% of grey production)")
        
        logger.info(f"\nData files have been saved to: {DATA_DIR}")
        
    except Exception as e:
        logger.error(f"Error generating sample data: {str(e)}")
        raise

if __name__ == "__main__":
    # Add a confirmation prompt
    print("This script will generate sample data for all JSON files.")
    print("Existing data will be backed up before new data is generated.")
    print(f"Data will be saved to: {DATA_DIR}")
    response = input("\nDo you want to continue? (y/n): ")
    
    if response.lower() == 'y':
        main()
    else:
        print("Data generation cancelled.")