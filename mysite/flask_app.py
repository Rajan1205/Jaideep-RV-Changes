# =============================================================================
# Imports and Configuration
# =============================================================================
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import json
import os
import io
from datetime import datetime, date, timedelta
import traceback
import logging
import sys
from forms import *
from access import setup_access_management, init_access_routes, init_access_users, roles_required
from flask_login import login_required, current_user
from collections import defaultdict

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# =============================================================================
# App Configuration
# =============================================================================
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
DATA_DIR = os.path.join(os.getcwd(), 'data')

# After creating the Flask app
setup_access_management(app)
init_access_routes(app)
init_access_users()

@app.context_processor
def utility_processor():
    return {
        'current_user': current_user
    }

# =============================================================================
# Utility Classes
# =============================================================================
class DateEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling date objects"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# =============================================================================
# Data Management Functions
# =============================================================================
def read_df(filename):
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    return pd.read_json(filepath)

def write_df(filename, data):
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    data.to_json(filepath,orient='records',indent=4)

def formulate_select_frm_df(data,col):
    """Get unique values from data and ensure consistent string format"""
    lst = []
    for record in data[f'{col}']:
      lst.append((record,record))
    return lst

def init_json_file(filename):
    """Initialize JSON file if it doesn't exist"""
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    try:
        with open(filepath, 'r') as f:
            json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(filepath, 'w') as f:
            json.dump([], f, cls=DateEncoder)

def read_json_file(filename):
    """Read data from JSON file"""
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_json_file(filename, data):
    """Write data to JSON file"""
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4, cls=DateEncoder)

def load_json_data(file_path):
    """Load JSON data with error handling"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, file_path)
        logger.debug(f"Loading file from: {full_path}")

        if not os.path.exists(full_path):
            logger.debug(f"File not found: {full_path}")
            return []

        with open(full_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}")
        return []

# =============================================================================
# Time and Date Handling Functions
# =============================================================================
def convert_to_24hr(time_str):
    """Convert 12-hour time format to 24-hour format"""
    if not time_str:
        return '00:00'
    try:
        time_str = time_str.strip().upper()
        formats = ['%I:%M %p', '%I:%M%p', '%I:%M', '%H:%M']

        for fmt in formats:
            try:
                parsed_time = datetime.strptime(time_str, fmt)
                return parsed_time.strftime('%H:%M')
            except ValueError:
                continue

        return '00:00'
    except (ValueError, TypeError, AttributeError):
        return '00:00'

def sort_records(records, reverse=True):
    """Sort records by date and time with proper error handling"""
    try:
        def sort_key(x):
            try:
                date_str = x.get('date', '')
                time_str = x.get('time_24', '00:00')
                if not date_str:
                    date_str = '1900-01-01'
                if not time_str:
                    time_str = '00:00'
                return (str(date_str), str(time_str))
            except Exception as e:
                logger.error(f"Error in sort_key: {e}")
                return ('1900-01-01', '00:00')

        return sorted(records, key=sort_key, reverse=reverse)
    except Exception as e:
        logger.error(f"Error in sort_records: {e}")
        return records


# =============================================================================
# User Management Functions
# =============================================================================

def get_users_by_role(role):
    """Get list of users for a specific role"""
    try:
        users = read_json_file('user_management')
        return [user['name'] for user in users if role in user['roles']]
    except Exception as e:
        logger.error(f'Error getting users by role: {str(e)}')
        return []

def update_form_choices(form):
    """Update form choices based on user roles"""
    if hasattr(form, 'warper_name'):
        warpers = get_users_by_role('Warper')
        form.warper_name.choices = [('', 'Select Warper')] + [(name, name) for name in warpers]

    if hasattr(form, 'sizer_name'):
        sizers = get_users_by_role('Sizer')
        form.sizer_name.choices = [('', 'Select Sizer')] + [(name, name) for name in sizers]

    if hasattr(form, 'weaver_name'):
        weavers = get_users_by_role('Grey Weaver')
        form.weaver_name.choices = [('', 'Select Weaver')] + [(name, name) for name in weavers]

    if hasattr(form, 'reliever_name'):
        relievers = get_users_by_role('Grey Reliever')
        form.reliever_name.choices = [('', 'Select Reliever')] + [(name, name) for name in relievers]

    if hasattr(form, 'foreman'):
        foremen = get_users_by_role('Grey Foreman')
        form.foreman.choices = [('', 'Select Foreman')] + [(name, name) for name in foremen]

    if hasattr(form, 'qc_checker'):
        qc_checkers = get_users_by_role('Grey QC')
        form.qc_checker.choices = [('', 'Select QC Checker')] + [(name, name) for name in qc_checkers]

# Add these new routes
@app.route('/user-management', methods=['GET', 'POST', 'DELETE'])
@login_required
@roles_required('admin', 'manager')
def user_management():
    """Handle user management operations"""
    try:
        form = UserManagementForm()

        if request.method == 'DELETE':
            data = request.get_json()
            users = read_json_file('user_management')
            users = [user for user in users if user['name'] != data['name']]
            write_json_file('user_management', users)
            return jsonify({'success': True})

        if request.method == 'POST' and form.validate_on_submit():
            data = {
                'name': form.name.data,
                'roles': form.roles.data,
                'timestamp': datetime.now().isoformat()
            }

            users = read_json_file('user_management')
            existing_user_index = next((idx for idx, user in enumerate(users)
                                     if user['name'] == data['name']), None)

            if existing_user_index is not None:
                users[existing_user_index].update(data)
                flash('User updated successfully', 'success')
            else:
                users.append(data)
                flash('User added successfully', 'success')

            write_json_file('user_management', users)
            return redirect(url_for('user_management'))

        users = read_json_file('user_management')
        return render_template('user_management.html',
                             form=form,
                             users=users,
                             role_groups=ROLE_GROUPS)

    except Exception as e:
        logger.error(f'Error in user management: {str(e)}')
        flash('An error occurred', 'error')
        return redirect(url_for('user_management'))

# @app.route('/api/users/<name>')
# def get_user(name):
#     """API endpoint to get user details"""
#     try:
#         users = read_json_file('user_management')
#         user = next((user for user in users if user['name'] == name), None)
#         if user:
#             return jsonify({'success': True, 'user': user})
#         return jsonify({'success': False, 'error': 'User not found'}), 404
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# Business Logic Functions
# =============================================================================
def get_unique_design_numbers():
    """Get unique design numbers from orderbook data"""
    orderbook_data = read_json_file('orderbook')
    design_numbers = []
    for record in orderbook_data:
        design_no = str(record.get('Design No.', '')).strip()
        if design_no:
            design_numbers.append(design_no)
    return sorted(set(design_numbers), key=str)

def get_production_details(beam_no):
    """Get production details for a specific beam number"""
    production_records = read_json_file('warping_production')
    for record in production_records:
        if record['beam_no'] == beam_no:
            return {
                'design_no': record['design_no'],
                'quantity': record['quantity'],
                'machine_no': record['machine_no'],
                'warper_name': record['warper_name'],
                'sections': record['sections'],
                'breakages': record['breakages']
            }
    return None

def get_available_beams():
    """Get list of beam numbers from warping production that haven't been dispatched"""
    production_records = read_json_file('warping_production')
    dispatch_records = read_json_file('warping_dispatch')

    dispatched_beams = {record['beam_no'] for record in dispatch_records
                       if record['dispatch_status'] == 'Yes'}

    available_beams = []
    for record in production_records:
        if record['beam_no'] not in dispatched_beams:
            available_beams.append(record['beam_no'])

    return sorted(set(available_beams))

def get_available_sized_beams():
    """Get list of beam numbers available for sizing"""
    try:
        # Get all dispatched beams from warping
        dispatch_records = read_json_file('warping_dispatch')
        sizing_records = read_json_file('sizing_production')

        # Create a set of beams that have already been sized
        sized_beams = {record['beam_no'] for record in sizing_records}

        # Get beams that have been dispatched from warping but not yet sized
        available_beams = []
        for record in dispatch_records:
            if record['dispatch_status'] == 'Yes' and record['beam_no'] not in sized_beams:
                available_beams.append(record['beam_no'])

        return sorted(set(available_beams))
    except Exception as e:
        logger.error(f'Error getting available sized beams: {str(e)}')
        return []

def get_available_sized_beams_for_dispatch():
    """Get list of sized beams available for dispatch"""
    sizing_records = read_json_file('sizing_production')
    dispatch_records = read_json_file('sizing_dispatch')

    dispatched_beams = {record['beam_no'] for record in dispatch_records
                       if record['dispatch_status'] == 'Yes'}

    available_beams = []
    for record in sizing_records:
        if record['status'] == 'Yes' and record['beam_no'] not in dispatched_beams:
            available_beams.append(record['beam_no'])

    return sorted(set(available_beams))

def get_available_beams_for_loom():
    """Get list of beams available for putting on loom"""
    try:
        dispatch_records = read_json_file('sizing_dispatch')
        loom_records = read_json_file('beam_on_loom')

        completed_beams = set()
        for record in loom_records:
            if record.get('process') == 'Beam End' and record.get('process_update') == 'End':
                completed_beams.add(record['beam_no'])

        available_beams = []
        for record in dispatch_records:
            if record.get('dispatch_status') == 'Yes' and record['beam_no'] not in completed_beams:
                available_beams.append(record['beam_no'])

        return sorted(set(available_beams))
    except Exception as e:
        logger.error(f'Error getting available beams for loom: {str(e)}')
        return []

def get_available_beams_for_grey_production():
    """Get list of beams available for grey production"""
    try:
        beam_records = read_json_file('beam_on_loom')

        completed_beams = set()
        for record in beam_records:
            if (record.get('process') == 'QC' and
                record.get('process_update') == 'End'):
                completed_beams.add(record['beam_no'])

        grey_records = read_json_file('grey_production')
        processed_beams = {record['beam_no'] for record in grey_records}

        available_beams = completed_beams - processed_beams
        return sorted(available_beams)
    except Exception as e:
        logger.error(f'Error getting available beams for grey production: {str(e)}')
        return []

def formulate_select(file,column):
    """Get unique design numbers from orderbook data and ensure consistent string format"""
    data = read_json_file(file)
    lst = []
    for record in data:
        # Convert value to string and strip any whitespace
        column_strp = str(record.get(column, '')).strip()
        if column_strp:  # Only add non-empty values
                lst.append(column_strp)
    # Convert to set for uniqueness and sort
    lst = sorted(set(lst), key=str)
    return lst

def read_df(filename):
    DATA_DIR = os.path.join(os.getcwd(),'data')
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    return pd.read_json(filepath)

def write_df(filename, data):
    DATA_DIR = os.path.join(os.getcwd(),'data')
    filepath = os.path.join(DATA_DIR, f'{filename}.json')
    data.to_json(filepath,orient='records',indent=4)


# =============================================================================
# Route Handlers
# =============================================================================

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# Production routes
@app.route('/grey-production', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'production')
def grey_production():
    """Handle grey production data upload and display"""
    try:
        if request.method == 'POST':
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400

            if not file.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'error': 'Invalid file type. Only Excel files are allowed.'}), 400

            # Read the Excel file
            df = pd.read_excel(file)

            required_columns = [
                'Date', 'Piece No.', 'Loom No.', 'Design No.',
                'Grey Production (Meters)', 'Grey Production (Weight)', 'Remarks'
            ]

            # Check for missing columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return jsonify({
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }), 400

            # Read existing records
            existing_records = read_json_file('grey_production')

            # Create a set of existing piece numbers
            existing_pieces = {str(record.get('piece_no')).strip().upper() for record in existing_records}

            # Process new records and check for duplicates
            new_records = []
            duplicate_pieces = []
            validation_errors = []

            for index, row in df.iterrows():
                try:
                    # Basic data validation
                    if pd.isna(row['Piece No.']):
                        validation_errors.append(f"Row {index + 2}: Piece number cannot be empty")
                        continue

                    piece_no = str(row['Piece No.']).strip().upper()

                    # Validate date
                    if pd.isna(row['Date']):
                        validation_errors.append(f"Row {index + 2}: Date is required for piece number {piece_no}")
                        continue

                    try:
                        date_val = pd.to_datetime(row['Date'])
                        if date_val > pd.Timestamp.now():
                            validation_errors.append(f"Row {index + 2}: Date cannot be in the future for piece number {piece_no}")
                            continue
                    except Exception:
                        validation_errors.append(f"Row {index + 2}: Invalid date format for piece number {piece_no}")
                        continue

                    # Validate numeric fields
                    loom_no = row['Loom No.']
                    if pd.isna(loom_no) or not str(loom_no).strip().isdigit():
                        validation_errors.append(f"Row {index + 2}: Invalid loom number for piece number {piece_no}")
                        continue

                    prod_meters = row['Grey Production (Meters)']
                    if pd.isna(prod_meters) or not isinstance(prod_meters, (int, float)) or prod_meters <= 0:
                        validation_errors.append(f"Row {index + 2}: Invalid production meters for piece number {piece_no}")
                        continue

                    prod_weight = row['Grey Production (Weight)']
                    if pd.isna(prod_weight) or not isinstance(prod_weight, (int, float)) or prod_weight <= 0:
                        validation_errors.append(f"Row {index + 2}: Invalid production weight for piece number {piece_no}")
                        continue

                    # Check for duplicate piece numbers in existing records
                    if piece_no in existing_pieces:
                        duplicate_pieces.append(piece_no)
                        continue

                    # Check for duplicate piece numbers within new records
                    if piece_no in {record['piece_no'] for record in new_records}:
                        duplicate_pieces.append(piece_no)
                        continue

                    # Prepare record
                    record = {
                        'date': date_val.strftime('%Y-%m-%d'),
                        'piece_no': piece_no,
                        'loom_no': int(loom_no),
                        'design_no': str(row['Design No.']).strip(),
                        'production_meters': float(prod_meters),
                        'production_weight': float(prod_weight),
                        'remarks': str(row['Remarks']) if pd.notna(row['Remarks']) else '',
                        'timestamp': datetime.now().isoformat()
                    }

                    new_records.append(record)

                except Exception as e:
                    validation_errors.append(f"Row {index + 2}: Error processing row: {str(e)}")

            # Compile all errors
            error_messages = []
            if validation_errors:
                error_messages.extend(validation_errors)
            if duplicate_pieces:
                error_messages.append(f"Duplicate piece numbers found: {', '.join(duplicate_pieces)}")

            if error_messages:
                return jsonify({
                    'error': 'Validation errors occurred',
                    'details': error_messages
                }), 400

            if not new_records:
                return jsonify({
                    'error': 'No valid records to process'
                }), 400

            # Save valid records
            existing_records.extend(new_records)
            existing_records.sort(key=lambda x: x.get('date', ''), reverse=True)
            write_json_file('grey_production', existing_records)

            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(new_records)} records'
            })

        # GET request handling
        records = read_json_file('grey_production')
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        return render_template('grey_production.html', records=records)

    except Exception as e:
        logger.error(f'Error in grey production: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': f'Error processing file: {str(e)}'
        }), 500

def format_date(date_value):
    if pd.isna(date_value):
        return None
    try:
        if isinstance(date_value, str):
            date_value = pd.to_datetime(date_value)
        return date_value.strftime('%Y-%m-%d')
    except:
        return None

def get_latest_loom_design(loom_no, location='259/1'):
    """Get latest design info for a loom with location consideration"""
    try:
        loom_no = int(loom_no)
        logger.debug(f"Getting design info for loom: {loom_no} at location: {location}")

        # Get required data
        beam_records = read_json_file('beam_on_loom')
        initiate_records = read_json_file('initiate_beam')
        orderbook_records = read_json_file('orderbook')

        # First check initiate_beam records for this location
        sorted_initiate_records = sorted(
            [r for r in initiate_records if r.get('location') == location],
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )

        # Find the latest initiated beam for this loom at this location
        latest_beam = None
        for record in sorted_initiate_records:
            if int(record.get('loom_no', 0)) == loom_no:
                latest_beam = record.get('beam_no')
                logger.debug(f"Found latest initiated beam: {latest_beam} for location: {location}")
                break

        if not latest_beam:
            logger.debug(f"No initiated beam found for loom {loom_no} at location {location}")
            return None

        # Check if this beam has ended
        sorted_beam_records = sorted(
            beam_records,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )

        for record in sorted_beam_records:
            if record.get('beam_no') == latest_beam:
                if record.get('status') == 'Beam End':
                    logger.debug(f"Beam {latest_beam} has ended")
                    return None
                break

        # Get design number from warping_production
        warping_records = read_json_file('warping_production')

        design_no = None
        order_no = None
        for record in warping_records:
            if record.get('beam_no') == latest_beam:
                design_no = record.get('design_no')
                order_no = record.get('order_no')
                logger.debug(f"Found design number: {design_no} and order number: {order_no}")
                break

        if not design_no:
            logger.debug("No design number found for this beam")
            return None

        # Get order details from orderbook
        # Make sure to match both design number and location
        order_details = None
        for record in orderbook_records:
            if (str(record.get('Design No.', '')).strip() == str(design_no).strip() and
                str(record.get('Weaving Location', '')).strip() == location.strip()):
                order_details = record
                logger.debug(f"Found order details for design: {design_no} at location: {location}")
                break

        if not order_details:
            logger.debug(f"No order details found for design {design_no} at location {location}")
            return None

        response = {
            'success': True,
            'design_no': design_no,
            'order_no': order_no or order_details.get('Order No.'),
            'reed': order_details.get('Reed'),
            'pick': order_details.get('Pick'),  # This is PPI in the orderbook
            'beam_no': latest_beam
        }

        logger.debug(f"Returning response: {response}")
        return response

    except Exception as e:
        logger.error(f'Error in get_latest_loom_design: {str(e)}')
        logger.error(traceback.format_exc())
        return None

@app.route('/api/loom/<loom_no>/latest', methods=['GET'])
def get_loom_latest(loom_no):
    """API endpoint to get latest design info for a loom"""
    try:
        logger.debug(f"API call for loom: {loom_no}")
        # For unit259 production, always use location 259/1
        loom_info = get_latest_loom_design(loom_no, location='259/1')

        if loom_info:
            logger.debug(f"Returning loom info: {loom_info}")
            return jsonify(loom_info)
        else:
            logger.debug("No design found for loom")
            return jsonify({
                'success': False,
                'error': 'No design found for this loom'
            }), 404

    except Exception as e:
        logger.error(f'Error in loom latest API: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File is too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {str(e)}')
    return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# Main Application Entry
# =============================================================================
if __name__ == '__main__':
    # Initialize data directory
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Initialize JSON files
    json_files = ['orderbook', 'warping_production', 'warping_dispatch',
                  'sizing_production', 'sizing_dispatch', 'beam_on_loom',
                  'grey_production', 'unit259_production', 'user_management',
                  'initiate_beam', 'grey_dispatch']

    # Initialize all JSON files
    for file in json_files:
        init_json_file(file)

    # Start the application
    app.run(host='0.0.0.0', port=8080, debug=True)

# =============================================================================
# Production Routes (continued)
# =============================================================================
@app.route('/unit259-production', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'production')
def unit259_production():
    try:
        form = Unit259ProductionForm()
        update_form_choices(form)

        # Get available looms
        try:
            beam_records = read_json_file('beam_on_loom')
            available_looms = set()

            # Track latest status for each loom
            loom_status = {}
            for record in beam_records:
                loom_no = record.get('loom_no')
                timestamp = record.get('timestamp')
                if loom_no and timestamp:
                    if loom_no not in loom_status or timestamp > loom_status[loom_no]['timestamp']:
                        loom_status[loom_no] = {
                            'status': record.get('status'),
                            'timestamp': timestamp,
                            'location': record.get('location')
                        }

            # Add looms with QC End status and correct location
            for loom_no, status in loom_status.items():
                if status['status'] == 'QC End' and status.get('location') == '259/1':
                    available_looms.add(str(loom_no))

            form.loom_no.choices = [('', 'Select Loom No.')] + [(loom, loom) for loom in sorted(available_looms)]
        except Exception as e:
            logger.error(f"Error getting available looms: {str(e)}")
            form.loom_no.choices = [('', 'Select Loom No.')]

        if request.method == 'POST' and form.validate_on_submit():
            try:
                # Calculate shift time in hours
                shift_time = float(form.shift_hours.data) + (float(form.shift_minutes.data) / 60)

                # Calculate efficiency and production values
                rpm = float(form.rpm.data)
                reading = float(form.reading.data)
                ppi = float(form.ppi.data)

                efficiency = ((reading * 100) / (rpm * 720)) * (12 / float(form.shift_hours.data))
                production_meters = reading / (ppi * 39.37)
                potential_production = (rpm * 720) / (ppi * 39.37)
                loss_meters = potential_production - production_meters

                # Store shift timing based on shift selection
                shift_timing = "08:00-20:00" if form.shift.data == "Day" else "20:00-08:00"

                data = {
                    'date': form.date.data.isoformat(),
                    'shift': form.shift.data,
                    'shift_timing': shift_timing,
                    'location': '259/1',
                    'loom_no': int(form.loom_no.data),
                    'design_no': form.design_no.data,
                    'order_no': form.order_no.data,
                    'reed': form.reed.data,
                    'rpm': rpm,
                    'ppi': ppi,
                    'reading': reading,
                    'warp': form.warp.data,
                    'weft': form.weft.data,
                    'efficiency': round(efficiency, 2),
                    'shift_hours': int(form.shift_hours.data),
                    'shift_minutes': int(form.shift_minutes.data),
                    'shift_time': shift_time,
                    'production_meters': round(production_meters, 2),
                    'loss_meters': round(loss_meters, 2),
                    'weaver_name': form.weaver_name.data,
                    'reliever_name': form.reliever_name.data,
                    'foreman': form.foreman.data,
                    'qc_checker': form.qc_checker.data,
                    'comments': form.comments.data,
                    'timestamp': datetime.now().isoformat()
                }

                # Read existing records and append new one
                records = read_json_file('unit259_production')
                records.append(data)

                # Sort by date and shift
                records.sort(key=lambda x: (x['date'], x['shift']), reverse=True)

                # Write back to file
                write_json_file('unit259_production', records)

                return jsonify({
                    'success': True,
                    'message': 'Production record added successfully'
                })

            except Exception as e:
                logger.error(f'Error saving production record: {str(e)}')
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        # Get records for display
        records = read_json_file('unit259_production')
        records.sort(key=lambda x: (x['date'], x['shift']), reverse=True)

        return render_template('unit259_production.html', form=form, records=records)

    except Exception as e:
        logger.error(f'Unexpected error in unit259_production: {str(e)}')
        return f"Error: {str(e)}", 500


def get_unit259_looms(exclude_maintenance=True):
    """Get all looms for Unit 259/1, optionally excluding those under maintenance"""
    try:
        # Define all looms for 259/1
        all_looms = list(range(1, 129))  # Looms 1-128

        if not exclude_maintenance:
            return sorted(all_looms)

        # Get looms under maintenance from unit259_production records
        production_records = read_json_file('unit259_production')

        # Track looms currently under maintenance
        maintenance_looms = set()

        # Get the latest status for each loom
        loom_latest_status = {}
        for record in production_records:
            loom_no = record.get('loom_no')
            timestamp = record.get('timestamp')
            if loom_no and timestamp:
                if loom_no not in loom_latest_status or timestamp > loom_latest_status[loom_no]['timestamp']:
                    loom_latest_status[loom_no] = {
                        'status': record.get('status'),
                        'timestamp': timestamp
                    }

        # Add looms with latest status as 'u/Maintenance' to maintenance set
        for loom_no, status_info in loom_latest_status.items():
            if status_info['status'] == 'u/Maintenance':
                maintenance_looms.add(loom_no)

        # Remove maintenance looms from available looms
        available_looms = [loom for loom in all_looms if loom not in maintenance_looms]

        return sorted(available_looms)

    except Exception as e:
        logger.error(f"Error getting Unit 259 looms: {str(e)}")
        return []

@app.route('/grey-dispatch', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'production')
def grey_dispatch():
    """Handle grey dispatch data upload and display"""
    try:
        if request.method == 'POST':
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400

            if not file.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'error': 'Invalid file type. Only Excel files are allowed.'}), 400

            # Read the Excel file
            df = pd.read_excel(file)

            required_columns = [
                'Date', 'Piece No.', 'Loom No.', 'Design No.',
                'Grey Production (Meters)', 'Grey Production (Weight)', 'Remarks'
            ]

            # Check for missing columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return jsonify({
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }), 400

            # Read existing records
            existing_records = read_json_file('grey_dispatch')

            # Create a set of existing piece numbers
            existing_pieces = {str(record.get('piece_no')).strip().upper() for record in existing_records}

            # Process new records and check for duplicates
            new_records = []
            duplicate_pieces = []
            validation_errors = []

            for index, row in df.iterrows():
                try:
                    # Basic data validation
                    if pd.isna(row['Piece No.']):
                        validation_errors.append(f"Row {index + 2}: Piece number cannot be empty")
                        continue

                    piece_no = str(row['Piece No.']).strip().upper()

                    # Validate date
                    if pd.isna(row['Date']):
                        validation_errors.append(f"Row {index + 2}: Date is required for piece number {piece_no}")
                        continue

                    try:
                        date_val = pd.to_datetime(row['Date'])
                        if date_val > pd.Timestamp.now():
                            validation_errors.append(f"Row {index + 2}: Date cannot be in the future for piece number {piece_no}")
                            continue
                    except Exception:
                        validation_errors.append(f"Row {index + 2}: Invalid date format for piece number {piece_no}")
                        continue

                    # Validate numeric fields
                    loom_no = row['Loom No.']
                    if pd.isna(loom_no) or not str(loom_no).strip().isdigit():
                        validation_errors.append(f"Row {index + 2}: Invalid loom number for piece number {piece_no}")
                        continue

                    prod_meters = row['Grey Production (Meters)']
                    if pd.isna(prod_meters) or not isinstance(prod_meters, (int, float)) or prod_meters <= 0:
                        validation_errors.append(f"Row {index + 2}: Invalid production meters for piece number {piece_no}")
                        continue

                    prod_weight = row['Grey Production (Weight)']
                    if pd.isna(prod_weight) or not isinstance(prod_weight, (int, float)) or prod_weight <= 0:
                        validation_errors.append(f"Row {index + 2}: Invalid production weight for piece number {piece_no}")
                        continue

                    # Check for duplicate piece numbers
                    if piece_no in existing_pieces:
                        duplicate_pieces.append(piece_no)
                        continue

                    # Check for duplicate piece numbers within new records
                    if piece_no in {record['piece_no'] for record in new_records}:
                        duplicate_pieces.append(piece_no)
                        continue

                    # Prepare record
                    record = {
                        'date': date_val.strftime('%Y-%m-%d'),
                        'piece_no': piece_no,
                        'loom_no': int(loom_no),
                        'design_no': str(row['Design No.']).strip(),
                        'production_meters': float(prod_meters),
                        'production_weight': float(prod_weight),
                        'remarks': str(row['Remarks']) if pd.notna(row['Remarks']) else '',
                        'timestamp': datetime.now().isoformat()
                    }

                    new_records.append(record)

                except Exception as e:
                    validation_errors.append(f"Row {index + 2}: Error processing row: {str(e)}")

            # Compile all errors
            error_messages = []
            if validation_errors:
                error_messages.extend(validation_errors)
            if duplicate_pieces:
                error_messages.append(f"Duplicate piece numbers found: {', '.join(duplicate_pieces)}")

            if error_messages:
                return jsonify({
                    'error': 'Validation errors occurred',
                    'details': error_messages
                }), 400

            if not new_records:
                return jsonify({
                    'error': 'No valid records to process'
                }), 400

            # Save valid records
            existing_records.extend(new_records)
            existing_records.sort(key=lambda x: x.get('date', ''), reverse=True)
            write_json_file('grey_dispatch', existing_records)

            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(new_records)} records'
            })

        # GET request handling
        records = read_json_file('grey_dispatch')
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        return render_template('grey_dispatch.html', records=records)

    except Exception as e:
        logger.error(f'Error in grey dispatch: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': f'Error processing file: {str(e)}'
        }), 500

# @app.route('/grey-dispatch/export', methods=['GET'])
# @login_required
# @roles_required('admin', 'manager', 'production')
# def export_grey_dispatch():
#     """Export grey dispatch data to Excel"""
#     try:
#         records = read_json_file('grey_dispatch')
#         df = pd.DataFrame(records)

#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#             df.to_excel(writer, index=False, sheet_name='Grey Dispatch')
#             workbook = writer.book
#             worksheet = writer.sheets['Grey Dispatch']

#             # Add header formatting
#             header_format = workbook.add_format({
#                 'bold': True,
#                 'text_wrap': True,
#                 'valign': 'top',
#                 'bg_color': '#D3D3D3'
#             })

#             for col_num, value in enumerate(df.columns.values):
#                 worksheet.write(0, col_num, value, header_format)

#             # Auto-adjust column widths
#             for i, col in enumerate(df.columns):
#                 max_length = max(df[col].astype(str).apply(len).max(), len(col))
#                 worksheet.set_column(i, i, min(max_length + 2, 50))

#         output.seek(0)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         return send_file(
#             output,
#             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#             as_attachment=True,
#             download_name=f'grey_dispatch_export_{timestamp}.xlsx'
#         )

#     except Exception as e:
#         logger.error(f'Error exporting grey dispatch data: {str(e)}')
#         flash('Error exporting grey dispatch data', 'error')
#         return redirect(url_for('grey_dispatch'))

def check_data_directory():
    """Verify DATA_DIR exists and is accessible"""
    try:
        # Print current working directory and DATA_DIR path
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"DATA_DIR path: {DATA_DIR}")
        logger.info(f"DATA_DIR absolute path: {os.path.abspath(DATA_DIR)}")

        # Check if directory exists
        if not os.path.exists(DATA_DIR):
            logger.error(f"DATA_DIR does not exist: {DATA_DIR}")
            return False

        # Check if it's a directory
        if not os.path.isdir(DATA_DIR):
            logger.error(f"DATA_DIR is not a directory: {DATA_DIR}")
            return False

        # Check read/write permissions
        test_file = os.path.join(DATA_DIR, 'test.txt')
        try:
            # Test write
            with open(test_file, 'w') as f:
                f.write('test')

            # Test read
            with open(test_file, 'r') as f:
                f.read()

            # Cleanup
            os.remove(test_file)

            logger.info("DATA_DIR is accessible with read/write permissions")
            return True
        except Exception as e:
            logger.error(f"Permission error on DATA_DIR: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error checking DATA_DIR: {str(e)}")
        return False

def get_warper_choices():
    users = read_json_file('user_management')
    warpers = [(user['name'], user['name']) for user in users if 'Warper' in user['roles']]
    return [('', 'Select Warper Name')] + sorted(warpers)

@app.route('/warping-production', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'warping')
def warping_production():
    # Initialize data directory and files
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.debug(f"Data directory: {DATA_DIR}")
        for file in ['orderbook.json', 'warping_production.json']:
            filepath = os.path.join(DATA_DIR, file)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    json.dump([], f)
                logger.debug(f"Created empty file: {filepath}")

    form = WarpingProductionForm()
    orderbook_data = read_json_file('orderbook')
    warping_records = read_json_file('warping_production')

    try:
        # Update form choices
        order_choices = set()
        design_by_order = {}
        order_groups = {}

        # Group orders
        for record in orderbook_data:
            order_no = str(record.get('Order No.', ''))
            if order_no not in order_groups:
                order_groups[order_no] = []
            order_groups[order_no].append(record)

        # Process groups
        for order_no, records in order_groups.items():
            if order_no:
                order_choices.add(order_no)
                design_by_order[order_no] = {}
                design_groups = {}

                for record in records:
                    design_no = str(record.get('Design No.', ''))
                    quantity = float(record.get('Factory Order (Meters)', 0))

                    if design_no not in design_groups:
                        design_groups[design_no] = {
                            'design_no': design_no,
                            'total_quantity': 0,
                            'orders': []
                        }
                    design_groups[design_no]['total_quantity'] += quantity
                    design_groups[design_no]['orders'].append({
                        'quantity': quantity,
                        'order_details': record
                    })

                for design_no, info in design_groups.items():
                    design_key = f"{design_no} (Total: {info['total_quantity']}m)"
                    design_by_order[order_no][design_key] = {
                        'design_no': design_no,
                        'quantity': info['total_quantity'],
                        'individual_orders': info['orders']
                    }

        # Update form choices
        form.warper_name.choices = get_warper_choices()
        form.order_no.choices = [('', 'Select Order No.')] + [(no, no) for no in sorted(order_choices)]

        if request.method == 'POST':
            selected_order = request.form.get('order_no')
            if selected_order in design_by_order:
                design_choices = [('', 'Select Design No.')] + [
                    (design_info['design_no'], design_key)
                    for design_key, design_info in sorted(design_by_order[selected_order].items())
                ]
                form.design_no.choices = design_choices

            if not form.validate_on_submit():
                logger.error(f"Form validation errors: {form.errors}")
                return jsonify({
                    'success': False,
                    'errors': form.errors
                }), 400

            # Check duplicate beam number
            if any(r['beam_no'] == form.beam_no.data for r in warping_records):
                return jsonify({
                    'success': False,
                    'error': f'Beam number {form.beam_no.data} already exists'
                }), 400

            existing_warping_qty = 0

            # Validate quantities
            if len(warping_records) > 0:
                for r in warping_records:
                    if r['order_no'] == form.order_no.data and r['design_no'] == form.design_no.data:
                        existing_warping_qty += float(r['quantity'])

            total_factory_qty = sum(
                float(record.get('Factory Order (Meters)', 0))
                for record in orderbook_data
                if str(record.get('Order No.')) == form.order_no.data
                and str(record.get('Design No.')) == form.design_no.data
            )

            new_qty = float(form.quantity.data)
            if (existing_warping_qty + new_qty) > total_factory_qty:
                return jsonify({
                    'success': False,
                    'error': 'Total warping quantity exceeds factory order quantity'
                }), 400

            # Calculate metrics
            start_time = form.start_datetime.data
            end_time = form.end_datetime.data
            session_time = (end_time - start_time).total_seconds() / 60
            warping_time = ((new_qty / form.rpm.data) * form.sections.data) + (form.breakages.data * 5)
            efficiency = ((warping_time + 30) / session_time) * 100

            # Get design info
            selected_design = form.design_no.data
            selected_order = form.order_no.data
            design_info = next(
                (info for key, info in design_by_order[selected_order].items()
                 if info['design_no'] == selected_design),
                None
            )

            total_quantity = design_info['quantity'] if design_info else 0

            # Prepare record data
            data = {
                'order_no': form.order_no.data,
                'design_no': form.design_no.data,
                'total_order_quantity': total_quantity,
                'machine_no': form.machine_no.data,
                'beam_no': form.beam_no.data,
                'quantity': new_qty,
                'warper_name': form.warper_name.data,
                'start_datetime_display': start_time.strftime('%d-%m-%Y %I:%M %p'),
                'end_datetime_display': end_time.strftime('%d-%m-%Y %I:%M %p'),
                'start_datetime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_datetime': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'rpm': form.rpm.data,
                'sections': form.sections.data,
                'breakages': form.breakages.data,
                'comments': form.comments.data,
                'warping_time_minutes': warping_time,
                'efficiency': round(efficiency, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Save record
            print(data)
            warping_records.append(data)
            write_json_file('warping_production', warping_records)

            return jsonify({
                'success': True,
                'message': 'Production record added successfully'
            })

        else:
            selected_order = request.form.get('order_no')
            if selected_order in design_by_order:
                design_choices = [('', 'Select Design No.')] + [
                    (design_info['design_no'], design_key)
                    for design_key, design_info in sorted(design_by_order[selected_order].items())
                ]
                form.design_no.choices = design_choices
            else:
                form.design_no.choices = [('', 'Select Design No.')]

        # Sort records for display
        warping_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return render_template(
            'warping_production.html',
            form=form,
            records=warping_records,
            design_by_order=json.dumps(design_by_order)
        )

    except Exception as e:
        logger.error(f'Error in warping production: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# @app.route('/warping-production', methods=['GET', 'POST'])
# def warping_production():
#     form = WarpingProductionForm()
#     update_form_choices(form)

#     if request.method == 'POST':
#         if not form.validate_on_submit():
#             return jsonify({
#                 'success': False,
#                 'errors': form.errors
#             }), 400

#         try:
#             # Validate beam number uniqueness
#             if any(r['beam_no'] == form.beam_no.data for r in read_json_file('warping_production')):
#                 return jsonify({
#                     'success': False,
#                     'error': f'Beam number {form.beam_no.data} already exists'
#                 }), 400

#             # Calculate metrics
#             start_time = form.start_datetime.data
#             end_time = form.end_datetime.data
#             session_time = (end_time - start_time).total_seconds() / 60
#             new_qty = float(form.quantity.data)
#             warping_time = ((new_qty / form.rpm.data) * form.sections.data)
#             efficiency = ((warping_time + 30) / session_time) * 100

#             data = {
#                 'order_no': form.order_no.data,
#                 'design_no': form.design_no.data,
#                 'machine_no': form.machine_no.data,
#                 'beam_no': form.beam_no.data,
#                 'quantity': new_qty,
#                 'warper_name': form.warper_name.data,
#                 'start_datetime': start_time.isoformat(),
#                 'end_datetime': end_time.isoformat(),
#                 'rpm': form.rpm.data,
#                 'sections': form.sections.data,
#                 'breakages': form.breakages.data,
#                 'comments': form.comments.data,
#                 'warping_time_minutes': warping_time,
#                 'efficiency': round(efficiency, 2),
#                 'timestamp': datetime.now().isoformat()
#             }

#             # Atomic write operation
#             records = read_json_file('warping_production')
#             records.append(data)
#             write_json_file('warping_production', records)

#             cache.delete('warping_records')
#             return jsonify({
#                 'success': True,
#                 'message': 'Production record added successfully'
#             })

#         except Exception as e:
#             logger.error(f'Error saving record: {str(e)}')
#             return jsonify({
#                 'success': False,
#                 'error': f'Error saving record: {str(e)}'
#             }), 500

#     # GET request handling
#     @cache.cached(timeout=300, key_prefix='warping_records')
#     def get_warping_records():
#         records = read_json_file('warping_production')
#         return sorted(records, key=lambda x: x.get('timestamp', ''), reverse=True)

#     records = get_warping_records()
#     return render_template(
#         'warping_production.html',
#         form=form,
#         records=records,
#         design_by_order=json.dumps(get_design_by_order())
#     )

#     # Initialize data directory and files
#     if not os.path.exists(DATA_DIR):
#         os.makedirs(DATA_DIR)

#         # Debug logging
#         logger.debug(f"Current working directory: {os.getcwd()}")
#         logger.debug(f"Data directory: {DATA_DIR}")

#         for file in ['orderbook.json', 'warping_production.json']:
#             filepath = os.path.join(DATA_DIR, file)
#             logger.debug(f"Checking file: {filepath}")
#             if not os.path.exists(filepath):
#                 with open(filepath, 'w') as f:
#                     json.dump([], f)
#                 logger.debug(f"Created empty file: {filepath}")

#         # Get orderbook data
#         orderbook_data = read_json_file('orderbook')
#         warping_records = read_json_file('warping_production')

#         # Prepare order choices and design mapping
#         order_choices = set()
#         design_by_order = {}

#         # Group by order number to consolidate designs
#         order_groups = {}
#         for record in orderbook_data:
#             order_no = str(record.get('Order No.', ''))
#             if order_no not in order_groups:
#                 order_groups[order_no] = []
#             order_groups[order_no].append(record)

#         # Process grouped records
#         for order_no, records in order_groups.items():
#             if order_no:
#                 order_choices.add(order_no)
#                 design_by_order[order_no] = {}

#                 # Group designs by design number to combine quantities
#                 design_groups = {}
#                 for record in records:
#                     design_no = str(record.get('Design No.', ''))
#                     quantity = float(record.get('Factory Order (Meters)', 0))

#                     if design_no not in design_groups:
#                         design_groups[design_no] = {
#                             'design_no': design_no,
#                             'total_quantity': 0,
#                             'orders': []
#                         }
#                     design_groups[design_no]['total_quantity'] += quantity
#                     design_groups[design_no]['orders'].append({
#                         'quantity': quantity,
#                         'order_details': record
#                     })

#                 # Store consolidated design information
#                 for design_no, info in design_groups.items():
#                     design_key = f"{design_no} (Total: {info['total_quantity']}m)"
#                     design_by_order[order_no][design_key] = {
#                         'design_no': design_no,
#                         'quantity': info['total_quantity'],
#                         'individual_orders': info['orders']
#                     }

#         # Update form choices for order_no
#         form.order_no.choices = [('', 'Select Order No.')] + [(no, no) for no in sorted(order_choices)]

#         # In your form choices update
#         if request.method == 'POST':
#             selected_order = request.form.get('order_no')
#             if selected_order in design_by_order:
#                 design_choices = [('', 'Select Design No.')] + [
#                     (design_no, design_no)  # Changed from design_key to design_no
#                     for _, design_info in sorted(design_by_order[selected_order].items())
#                     for design_no in [design_info['design_no']]
#                 ]
#                 form.design_no.choices = design_choices

#         # Handle POST request
#         if request.method == 'POST':
#             if not form.validate_on_submit():
#                 logger.error(f"Form validation errors: {form.errors}")
#                 return jsonify({
#                     'success': False,
#                     'errors': form.errors
#                 }), 400

#             try:
#                 # Check for duplicate beam number
#                 if any(r['beam_no'] == form.beam_no.data for r in warping_records):
#                     return jsonify({
#                         'success': False,
#                         'error': f'Beam number {form.beam_no.data} already exists'
#                     }), 400

#                 # Calculate total warping quantity for this order-design combination
#                 existing_warping_qty = sum(
#                     float(r['quantity'])
#                     for r in warping_records
#                     if r['order_no'] == form.order_no.data and r['design_no'] == form.design_no.data
#                 )

#                 # Get total factory order quantity
#                 total_factory_qty = sum(
#                     float(record.get('Factory Order (Meters)', 0))
#                     for record in orderbook_data
#                     if str(record.get('Order No.')) == form.order_no.data
#                     and str(record.get('Design No.')) == form.design_no.data
#                 )

#                 # Validate against factory order quantity
#                 new_qty = float(form.quantity.data)
#                 if (existing_warping_qty + new_qty) > total_factory_qty:
#                     return jsonify({
#                         'success': False,
#                         'error': 'Total warping quantity exceeds factory order quantity'
#                     }), 400

#                 # Calculate session time in minutes
#                 start_time = form.start_datetime.data
#                 end_time = form.end_datetime.data
#                 session_time = (end_time - start_time).total_seconds() / 60

#                 # Calculate warping time in minutes
#                 warping_time = ((new_qty / form.rpm.data) * form.sections.data)

#                 # Calculate efficiency
#                 efficiency = ((warping_time + 30) / session_time) * 100
#                 selected_design = form.design_no.data
#                 selected_order = form.order_no.data
#                 design_info = next(
#                     (info for key, info in design_by_order[selected_order].items()
#                      if info['design_no'] == selected_design),
#                     None
#                 )

#                 if design_info:
#                     total_quantity = design_info['quantity']
#                     individual_orders = design_info['individual_orders']
#                 else:
#                     total_quantity = 0
#                     individual_orders = []

#                 data = {
#                     'order_no': form.order_no.data,
#                     'design_no': form.design_no.data,
#                     'total_order_quantity': total_quantity,
#                     'machine_no': form.machine_no.data,
#                     'beam_no': form.beam_no.data,
#                     'quantity': new_qty,
#                     'warper_name': form.warper_name.data,
#                     'start_datetime_display': form.start_datetime.data.strftime('%d-%m-%Y %I:%M %p'),
#                     'end_datetime_display': form.end_datetime.data.strftime('%d-%m-%Y %I:%M %p'),
#                     'start_datetime': form.start_datetime.data.strftime('%Y-%m-%d %H:%M:%S'),
#                     'end_datetime': form.end_datetime.data.strftime('%Y-%m-%d %H:%M:%S'),
#                     'rpm': form.rpm.data,
#                     'sections': form.sections.data,
#                     'breakages': form.breakages.data,
#                     'comments': form.comments.data,
#                     'warping_time_minutes': warping_time,
#                     'efficiency': round(efficiency, 2),
#                     'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 }

#                 warping_records.append(data)
#                 write_json_file('warping_production', warping_records)

#                 return jsonify({
#                     'success': True,
#                     'message': 'Production record added successfully'
#                 })

#             except Exception as e:
#                 logger.error(f'Error saving record: {str(e)}')
#                 return jsonify({'success': False,
#                     'error': f'Error saving record: {str(e)}'
#                 }), 500

#         else:
#             selected_order = request.form.get('order_no') if request.method == 'POST' else None
#             if selected_order in design_by_order:
#                 design_choices = [('', 'Select Design No.')] + [
#                     (design_info['design_no'], design_key)
#                     for design_key, design_info in sorted(design_by_order[selected_order].items())
#                 ]
#                 form.design_no.choices = design_choices
#             else:
#                 form.design_no.choices = [('', 'Select Design No.')]

#         # Sort records by timestamp for display
#         warping_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

#         # Debug logging for template context
#         logger.debug(f"Number of warping records: {len(warping_records)}")
#         logger.debug(f"Number of order choices: {len(order_choices)}")
#         logger.debug(f"Design by order mapping: {json.dumps(design_by_order, indent=2)}")

#         return render_template(
#             'warping_production.html',
#             form=form,
#             records=warping_records,
#             design_by_order=json.dumps(design_by_order)
#         )

#     except Exception as e:
#         logger.error(f'Error in warping production: {str(e)}\n{traceback.format_exc()}')
#         return jsonify({
#             'success': False,
#             'error': f'Server error: {str(e)}'
#         }), 500

@app.route('/api/designs-by-order/<order_no>')
def get_designs_by_order(order_no):
    """API endpoint to get designs for an order number"""
    try:
        orderbook_data = read_json_file('orderbook')
        logger.debug(f"Fetching designs for order: {order_no}")

        # Get unique designs for the order
        available_designs = set()

        for record in orderbook_data:
            if str(record.get('Order No.')) == str(order_no):  # Convert both to string for comparison
                design_no = record.get('Design No.')
                if design_no:
                    available_designs.add(str(design_no))  # Convert to string

        # Convert to list and sort for consistent ordering
        designs_list = sorted(list(available_designs))
        logger.debug(f"Found designs for order {order_no}: {designs_list}")

        response_data = {
            'success': True,
            'designs': [{'id': design, 'text': design} for design in designs_list]
        }

        logger.debug(f"Returning response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f'Error in get_designs_by_order: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/beam/<beam_no>', methods=['GET'])
def get_beam_details(beam_no):
    """API endpoint to get beam details"""
    try:
        production_details = get_production_details(beam_no)
        if production_details:
            return jsonify({
                'success': True,
                'production_details': production_details
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Beam not found'
            }), 404
    except Exception as e:
        logger.error(f'Error fetching beam details: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/data/<filename>', methods=['GET'])
def get_json_data(filename):
    """API endpoint to fetch JSON data"""
    try:
        if not filename.endswith('.json'):
            filename = f"{filename}.json"

        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({
                'error': 'File not found',
                'available_files': [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
            }), 404

        with open(filepath, 'r') as f:
            data = json.load(f)
        return jsonify(data)

    except Exception as e:
        logger.error(f'Error accessing JSON data: {str(e)}')
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Orderbook Routes
# =============================================================================
@app.route('/close-orders', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager')
def close_orders():
    form = close_order()
    form.order_no.choices = formulate_select('orderbook','Order No.')
    records = []
    if request.method == 'POST' and form.validate_on_submit():
        data = {'Order No.':form.order_no.data,'Del':'Yes'}
        records = read_json_file('orders_closed')
        records.append(data)
        df = pd.DataFrame(records)
        df.drop_duplicates(inplace=True)
        orders = read_df('orderbook')
        orders['Order No.'] = orders['Order No.'].astype(int)
        df['Order No.'] = df['Order No.'].astype(int)
        df = df[['Order No.','Del']]
        df.drop_duplicates(inplace=True)
        output_df = orders.merge(df,on=['Order No.'],how='left')
        tally_df = output_df[(output_df['Del'].isnull() == True)]
        archive_df = output_df[~(output_df['Del'].isnull() == True)]
        col_lst = orders.columns.to_list()
        write_df('orders_closed',archive_df[col_lst])
        write_df('orderbook',tally_df[col_lst])
        return render_template("close_orders.html",form=form)
    return render_template("close_orders.html",form=form)

@app.route('/orderbook', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager')
def orderbook():
    """Handle orderbook operations"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400

            if not file.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'error': 'Invalid file type. Only Excel files are allowed.'}), 400

            # Read the Excel file
            df = pd.read_excel(file)

            required_columns = [
                'Office Date', 'Office Order No', 'Date of Office',
                'Temp. Order No.', 'Order No.', 'Combo No.', 'Design No.',
                'Yarn Dyeing Plant', 'Yarn Dyeing Date', 'Yarn Dyeing Order No.',
                'Quality', 'Factory Order (Meters)', 'Warping Location',
                'Weaving Location', 'Warp Count', 'Weft Count', 'Reed',
                'Pick', 'RS on Loom', 'Weave', 'Shafts', 'Warp Shades',
                'Weft Shades', 'Party Name', 'Party Quantity (Meters)',
                'Finishing Requirements', 'Selvedge', 'Delivery Date'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return jsonify({
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }), 400

            # Read existing records
            existing_records = read_json_file('orderbook')

            # Create a set of existing order-design combinations
            existing_combinations = {
                (str(record.get('Order No.')), str(record.get('Design No.')))
                for record in existing_records
            }

            # Process new records and check for duplicates
            new_records = []
            duplicate_combinations = set()

            for _, row in df.iterrows():
                record = {}
                for key in required_columns:
                    value = row.get(key)
                    if key in ['Office Date', 'Date of Office', 'Yarn Dyeing Date', 'Delivery Date']:
                        record[key] = format_date(value)
                    elif pd.isna(value):
                        record[key] = None
                    elif isinstance(value, (int, float)):
                        if key in ['Factory Order (Meters)', 'Party Quantity (Meters)']:
                            record[key] = float(value)
                        else:
                            record[key] = value
                    else:
                        record[key] = str(value).strip()

                # Check for duplicate order-design combination
                order_design = (str(record.get('Order No.')), str(record.get('Design No.')))
                if order_design in existing_combinations:
                    duplicate_combinations.add(order_design)
                else:
                    record['timestamp'] = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
                    record['upload_filename'] = secure_filename(file.filename)
                    new_records.append(record)
                    existing_combinations.add(order_design)

            if duplicate_combinations:
                duplicate_msg = [f"Order No: {od[0]}, Design No: {od[1]}"
                               for od in duplicate_combinations]
                return jsonify({
                    'error': 'Duplicate order-design combinations found:',
                    'duplicates': duplicate_msg
                }), 400

            if new_records:
                existing_records.extend(new_records)
                existing_records.sort(key=lambda x: x.get('Office Date', ''), reverse=True)
                write_json_file('orderbook', existing_records)
                return jsonify({
                    'success': True,
                    'message': f'Successfully processed {len(new_records)} records'
                })
            else:
                return jsonify({
                    'error': 'No new records to process - all entries were duplicates'
                }), 400

        except Exception as e:
            logger.error(f'Error processing file: {str(e)}')
            logger.error(traceback.format_exc())
            return jsonify({
                'error': f'Error processing file: {str(e)}'
            }), 500

    try:
        records = read_json_file('orderbook')
        records.sort(key=lambda x: x.get('Office Date', ''), reverse=True)
        return render_template('orderbook.html', records=records)
    except Exception as e:
        logger.error(f'Error rendering orderbook: {str(e)}')
        return render_template('orderbook.html', records=[], error=str(e))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def format_date(date_value):
    if pd.isna(date_value):
        return None
    try:
        if isinstance(date_value, str):
            date_value = pd.to_datetime(date_value)
        return date_value.strftime('%d-%m-%Y')
    except:
        return None

@app.route('/orderbook/export', methods=['GET'])
def export_orderbook():
    """Export orderbook data to Excel"""
    try:
        records = read_json_file('orderbook')
        df = pd.DataFrame(records)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Orderbook')
            workbook = writer.book
            worksheet = writer.sheets['Orderbook']

            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#D3D3D3'
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col))
                worksheet.set_column(i, i, min(max_length + 2, 50))

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'orderbook_export_{timestamp}.xlsx'
        )

    except Exception as e:
        logger.error(f'Error exporting orderbook: {str(e)}')
        flash('Error exporting orderbook data', 'error')
        return redirect(url_for('orderbook'))

@app.route('/orderbook/delete/<order_no>', methods=['POST'])
def delete_order(order_no):
    """Delete an order from orderbook"""
    try:
        records = read_json_file('orderbook')
        original_count = len(records)
        records = [r for r in records if r.get('Order No.') != order_no]

        if len(records) < original_count:
            write_json_file('orderbook', records)
            return jsonify({
                'success': True,
                'message': f'Order {order_no} deleted successfully'
            })
        else:
            return jsonify({
                'error': f'Order {order_no} not found'
            }), 404

    except Exception as e:
        return jsonify({
            'error': 'Error deleting order',
            'details': str(e)
        }), 500

# =============================================================================
# Warping and Sizing Routes
# =============================================================================
@app.route('/warping-dispatch', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'warping')
def warping_dispatch():
    try:
        form = WarpingDispatchForm()
        available_beams = get_available_beams()
        form.beam_no.choices = [('', 'Select Beam No.')] + [(beam, beam) for beam in available_beams]

        if request.method == 'POST':
            if not form.validate_on_submit():
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'errors': {field.name: field.errors[0] for field in form if field.errors}
                }), 400

            data = {
                'date': form.date.data.isoformat(),
                'beam_no': form.beam_no.data,
                'dispatch_status': form.dispatch_status.data,
                'timestamp': datetime.now().isoformat()
            }

            production_details = get_production_details(form.beam_no.data)
            if production_details:
                data['production_details'] = production_details

            records = read_json_file('warping_dispatch')
            existing_record_index = next((idx for idx, record in enumerate(records)
                                       if record['beam_no'] == data['beam_no']), None)

            if existing_record_index is not None:
                records[existing_record_index].update(data)
                message = 'Dispatch record updated successfully'
            else:
                records.append(data)
                message = 'New dispatch record added successfully'

            write_json_file('warping_dispatch', records)
            return jsonify({'success': True, 'message': message})

        records = read_json_file('warping_dispatch')
        records.sort(key=lambda x: x.get('date', ''), reverse=True)

        for record in records:
            if 'production_details' not in record or record['production_details'] is None:
                record['production_details'] = get_production_details(record['beam_no'])

        return render_template('warping_dispatch.html', form=form, records=records)

    except Exception as e:
        logger.error(f'Error in warping dispatch: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sizing-production', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'sizing')
def sizing_production():
    try:
        form = SizingProductionForm()
        update_form_choices(form)

        # Get available beams (excluding already sized ones)
        available_beams = get_available_sized_beams()
        form.beam_no.choices = [('', 'Select Beam No.')] + [(beam, beam) for beam in available_beams]

        if request.method == 'POST':
            if form.validate_on_submit():
                # Double check that the beam hasn't been sized yet
                existing_records = read_json_file('sizing_production')
                if any(r['beam_no'] == form.beam_no.data for r in existing_records):
                    return jsonify({
                        'success': False,
                        'error': f'Beam number {form.beam_no.data} has already been sized'
                    }), 400

                data = {
                    'beam_no': form.beam_no.data,
                    'status': form.status.data,
                    'sizer_name': form.sizer_name.data,
                    'start_datetime': form.start_datetime.data.strftime('%Y-%m-%d %H:%M') if form.start_datetime.data else None,
                    'end_datetime': form.end_datetime.data.strftime('%Y-%m-%d %H:%M') if form.end_datetime.data else None,
                    'rf': float(form.rf.data) if form.rf.data else 0.0,
                    'moisture': float(form.moisture.data) if form.moisture.data else 0.0,
                    'speed': float(form.speed.data) if form.speed.data else 0.0,
                    'comments': form.comments.data,
                    'timestamp': datetime.now().isoformat()
                }

                existing_records.append(data)
                existing_records.sort(key=lambda x: x.get('start_datetime', ''), reverse=True)
                write_json_file('sizing_production', existing_records)

                return jsonify({
                    'success': True,
                    'message': 'Production record added successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'errors': form.errors
                }), 400

        records = read_json_file('sizing_production')
        records.sort(key=lambda x: x.get('start_datetime', ''), reverse=True)
        return render_template('sizing_production.html', form=form, records=records)

    except Exception as e:
        logger.error(f'Error in sizing production: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/sizing-dispatch', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'sizing')
def sizing_dispatch():
    """Handle sizing dispatch operations"""
    try:
        form = SizingDispatchForm()
        available_beams = get_available_sized_beams_for_dispatch()
        logger.debug(f"Available beams: {available_beams}")
        form.beam_no.choices = [('', 'Select Beam No.')] + [(beam, beam) for beam in available_beams]

        if request.method == 'POST' and form.validate_on_submit():
            try:
                data = {
                    'date': form.date.data.isoformat(),
                    'beam_no': form.beam_no.data,
                    'dispatch_status': form.dispatch_status.data,
                    'timestamp': datetime.now().isoformat()
                }

                sizing_records = read_json_file('sizing_production')
                sizing_details = next(
                    (record for record in sizing_records if record['beam_no'] == form.beam_no.data),
                    None
                )
                if sizing_details:
                    data['sizing_details'] = sizing_details

                records = read_json_file('sizing_dispatch')
                existing_record_index = next((idx for idx, record in enumerate(records)
                                           if record['beam_no'] == data['beam_no']), None)

                if existing_record_index is not None:
                    records[existing_record_index].update(data)
                else:
                    records.append(data)

                write_json_file('sizing_dispatch', records)
                message = 'Dispatch record added successfully'
                return jsonify({'success': True, 'message': message})

            except Exception as e:
                logger.error(f'Error saving dispatch record: {str(e)}')
                return jsonify({'success': False, 'error': str(e)}), 500

        records = read_json_file('sizing_dispatch')
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        return render_template('sizing_dispatch.html', form=form, records=records)

    except Exception as e:
        logger.error(f'Unexpected error in sizing_dispatch: {str(e)}')
        return f"Error: {str(e)}", 500

# =============================================================================
# Beam Management Routes
# =============================================================================

def get_available_beams_by_location(location):
    """Get list of beams available for a specific location"""
    try:
        logger.debug(f"Starting beam search for location: {location}")

        # Get all required data
        sizing_dispatch = read_json_file('sizing_dispatch')
        orderbook = read_json_file('orderbook')
        beam_on_loom = read_json_file('beam_on_loom')
        initiate_beam = read_json_file('initiate_beam')

        # Log the data for debugging
        logger.debug(f"Sizing dispatch records: {len(sizing_dispatch)}")
        logger.debug(f"Orderbook records: {len(orderbook)}")
        logger.debug(f"Beam on loom records: {len(beam_on_loom)}")
        logger.debug(f"Initiate beam records: {len(initiate_beam)}")

        # 1. Get all dispatched beams
        dispatched_beams = set()
        for record in sizing_dispatch:
            if record.get('dispatch_status') == 'Yes':
                dispatched_beams.add(record['beam_no'])
        logger.debug(f"Dispatched beams: {dispatched_beams}")

        # 2. Remove beams that are already on looms or initiated
        used_beams = set()
        for record in beam_on_loom:
            used_beams.add(record['beam_no'])
        for record in initiate_beam:
            used_beams.add(record['beam_no'])
        logger.debug(f"Used beams: {used_beams}")

        # 3. Get initially available beams
        available_beams = dispatched_beams - used_beams
        logger.debug(f"Initially available beams: {available_beams}")

        # 4. Filter beams based on weaving location
        location_filtered_beams = set()
        for beam in available_beams:
            # Get the sizing details for this beam
            sizing_record = next(
                (record for record in sizing_dispatch if record['beam_no'] == beam),
                None
            )

            if sizing_record:
                # Find matching orderbook record
                orderbook_records = [
                    record for record in orderbook
                    if record['Weaving Location'].strip() == location.strip()
                ]

                if orderbook_records:
                    location_filtered_beams.add(beam)
                    logger.debug(f"Added beam {beam} for location {location}")

        logger.debug(f"Final available beams for location {location}: {location_filtered_beams}")
        return sorted(location_filtered_beams)

    except Exception as e:
        logger.error(f"Error in get_available_beams_by_location: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def get_available_looms_by_location(location):
    """Get list of looms available for a specific location"""
    try:
        # Define loom ranges for each location
        loom_ranges = {
            '212/1': list(range(25, 49)) + list(range(68, 113)),  # Looms 25-48 and 68-112
            '259/1': list(range(1, 129))  # Looms 1-128
        }

        # Get all possible looms for this location
        all_looms = loom_ranges.get(location.strip(), [])
        logger.debug(f"All possible looms for location {location}: {all_looms}")

        # Get currently used looms from beam_on_loom and initiate_beam records
        beam_records = read_json_file('beam_on_loom')
        initiate_records = read_json_file('initiate_beam')

        used_looms = set()

        # Check beam_on_loom records
        for record in beam_records:
            if record['status'] != 'Beam End':  # Only consider active beams
                used_looms.add(record['loom_no'])

        # Check initiate_beam records
        for record in initiate_records:
            if record['location'] == location:
                used_looms.add(record['loom_no'])

        logger.debug(f"Used looms: {used_looms}")

        # Get available looms (all possible looms minus used looms)
        available_looms = [loom for loom in all_looms if loom not in used_looms]
        logger.debug(f"Available looms: {available_looms}")

        return sorted(available_looms)

    except Exception as e:
        logger.error(f"Error in get_available_looms_by_location: {str(e)}")
        return []

# @app.route('/check-data')
# def check_data():
#     try:
#         # Check directory
#         logger.debug(f"Data Directory: {DATA_DIR}")
#         files = os.listdir(DATA_DIR)

#         # Read each file separately
#         data = {}
#         for file in ['sizing_dispatch.json', 'warping_production.json', 'orderbook.json', 'beam_on_loom.json']:
#             try:
#                 filepath = os.path.join(DATA_DIR, file)
#                 if os.path.exists(filepath):
#                     with open(filepath, 'r') as f:
#                         content = f.read()
#                         data[file] = json.loads(content)
#                         logger.debug(f"Successfully read {file}")
#                 else:
#                     data[file] = f"File not found: {filepath}"
#             except Exception as e:
#                 data[file] = f"Error reading file: {str(e)}"

#         return jsonify({
#             'data_dir': DATA_DIR,
#             'files_found': files,
#             'contents': data
#         })
#     except Exception as e:
#         return jsonify({'error': str(e), 'type': type(e).__name__})

@app.route('/fix-test-data')
def fix_test_data():
    try:
        test_data = {
            'sizing_dispatch.json': [{
                "beam_no": "B123",
                "dispatch_status": "Yes",
                "date": "2024-01-20",
                "timestamp": "2024-01-20T10:00:00"
            }],
            'warping_production.json': [{
                "beam_no": "B123",
                "design_no": "D456",
                "quantity": 1000,
                "timestamp": "2024-01-19T10:00:00"
            }],
            'orderbook.json': [{
                "Design No.": "D456",
                "Weaving Location": "212/1",
                "Order No.": "O789",
                "Factory Order (Meters)": 1000,
                "timestamp": "2024-01-18T10:00:00"
            }],
            'beam_on_loom.json': []
        }

        for filename, data in test_data.items():
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        return jsonify({"message": "Test data written successfully"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/initiate-beam', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'production')
def initiate_beam():
   try:
       form = InitiateBeamForm()

       # Update form choices based on location
       if form.location.data:
           beams = get_available_beams_by_location(form.location.data)
           looms = get_available_looms_by_location(form.location.data)
           form.beam_no.choices = [('', 'Select Beam No.')] + [(str(beam), str(beam)) for beam in beams]
           form.loom_no.choices = [('', 'Select Loom No.')] + [(str(loom), str(loom)) for loom in looms]

       if request.method == 'POST' and form.validate_on_submit():
           # Prepare initiate beam data
           initiate_data = {
               'location': form.location.data,
               'beam_no': form.beam_no.data,
               'loom_no': int(form.loom_no.data),
               'start_datetime': form.start_datetime.data.strftime('%Y-%m-%d %H:%M'),
               'status': 'Beam Start',
               'timestamp': datetime.now().isoformat()
           }

           # Get existing records
           initiate_records = read_json_file('initiate_beam')
           beam_records = read_json_file('beam_on_loom')

           # Validate beam not already initiated
           if any(r['beam_no'] == initiate_data['beam_no'] for r in initiate_records):
               return jsonify({
                   'success': False,
                   'error': 'Beam already initiated'
               }), 400

           # Validate loom not in use
           if any(r['loom_no'] == initiate_data['loom_no'] and r['location'] == initiate_data['location']
                 for r in initiate_records):
               return jsonify({
                   'success': False,
                   'error': 'Loom already in use'
               }), 400

           # Add to initiate_beam records
           initiate_records.append(initiate_data)
           write_json_file('initiate_beam', initiate_records)

           # Add initial beam on loom record
           beam_record = {
               'beam_no': initiate_data['beam_no'],
               'loom_no': initiate_data['loom_no'],
               'status': initiate_data['status'],
               'role': 'Beam Start',
               'name': 'System',
               'timestamp': initiate_data['start_datetime']
           }
           beam_records.append(beam_record)
           write_json_file('beam_on_loom', beam_records)

           return jsonify({
               'success': True,
               'message': 'Beam initiated successfully'
           })

       # Get records for display
       records = read_json_file('initiate_beam')
       records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
       return render_template('initiate_beam.html', form=form, records=records)

   except Exception as e:
       logger.error(f'Error in initiate beam: {str(e)}')
       return jsonify({
           'success': False,
           'error': str(e)
       }), 500

@app.route('/api/beam-records')
def get_beam_records():
    """API endpoint to get initiated beam records"""
    try:
        records = read_json_file('initiate_beam')

        # Transform datetime strings for display
        for record in records:
            if 'start_datetime' in record:
                dt = datetime.strptime(record['start_datetime'], '%Y-%m-%d %H:%M')
                record['start_datetime'] = dt.strftime('%d-%m-%Y %I:%M %p')

        records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify({
            'success': True,
            'records': records
        })
    except Exception as e:
        logger.error(f'Error fetching beam records: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/looms/<path:location>')
def get_looms(location):
    """API endpoint to get available looms for a location"""
    try:
        looms = get_available_looms_by_location(location)
        return jsonify({
            'success': True,
            'looms': [{'id': str(loom), 'text': str(loom)} for loom in looms]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/beams/<path:location>')
def get_beams(location):
    """API endpoint to get available beams for a location"""
    try:
        logger.debug(f"Fetching beams for location: {location}")
        beams = get_available_beams_by_location(location)
        logger.debug(f"Found beams: {beams}")

        response_data = {
            'success': True,
            'beams': [{'id': str(beam), 'text': str(beam)} for beam in beams]
        }
        logger.debug(f"Sending response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_beams API: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# def datetime_handler(x):
#     if isinstance(x, datetime):
#         return x.isoformat()
#     return str(x)

# beams = json.loads(json.dumps(read_json_file('initiate_beam'), default=datetime_handler))

# @app.route('/api/looms/<location>')
# def get_looms(location):
#     """API endpoint to get available looms for a location"""
#     try:
#         looms = get_available_looms_by_location(location)
#         return jsonify({
#             'success': True,
#             'looms': [{'id': str(loom), 'text': str(loom)} for loom in looms]
#         })
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         }), 500

# @app.route('/api/beams/<location>')
# def get_beams(location):
#     """API endpoint to get available beams for a location"""
#     try:
#         beams = get_available_beams_by_location(location)
#         return jsonify({
#             'success': True,
#             'beams': [{'id': beam, 'text': beam} for beam in beams]
#         })
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         }), 500


def get_next_status(current_status):
    status_flow = [
        'Beam Start',
        'Knotting / Drawing Start',
        'Knotting / Drawing End',
        'Getting Start',
        'Getting End',
        'QC Start',
        'QC End',
        'Beam End'
    ]
    try:
        current_index = status_flow.index(current_status)
        if current_index < len(status_flow) - 1:
            return status_flow[current_index + 1]
    except ValueError:
        pass
    return 'Beam Start'

def get_available_looms_by_location_v2(location):
    """Get loom numbers based on location"""
    loom_ranges = {
        '212/1': list(range(25, 49)) + list(range(68, 113)),
        '259/1': list(range(1, 129))
    }
    return loom_ranges.get(location.replace('%2F', '/'), [])

def get_available_looms_v2(location):
    """Get looms that need status updates"""
    beam_records = read_json_file('beam_on_loom')
    initiate_records = read_json_file('initiate_beam')
    all_looms = get_available_looms_by_location_v2(location)

    # Get looms with active beams (non-ended status)
    already_used_looms = set()

    # Track which looms have active beams (not ended)
    for record in sorted(beam_records, key=lambda x: x.get('timestamp', ''), reverse=True):
        loom_no = record['loom_no']
        if loom_no not in already_used_looms:
            if record['status'] != 'Beam End':
                already_used_looms.add(loom_no)

    # Add looms from initiate records that aren't marked as ended
    for record in initiate_records:
        if record['location'] == location:
            loom_no = record['loom_no']
            if loom_no not in already_used_looms:
                already_used_looms.add(loom_no)

    # Get all available looms for the location that aren't in use
    available_looms = [loom for loom in all_looms if loom in already_used_looms]

    return sorted(available_looms)

def get_beam_for_loom_v2(loom_no):
    """Get current beam number for a loom"""
    try:
        # Convert loom_no to integer for comparison
        loom_no = int(loom_no)

        logger.debug(f"Getting beam for loom: {loom_no}")

        initiate_records = read_json_file('initiate_beam')
        beam_records = read_json_file('beam_on_loom')

        logger.debug(f"Found {len(initiate_records)} initiate records")
        logger.debug(f"Found {len(beam_records)} beam records")

        # Sort and get latest initiated beam
        sorted_initiate_records = sorted(initiate_records,
                                      key=lambda x: x.get('timestamp', ''),
                                      reverse=True)
        latest_beam = None

        for record in sorted_initiate_records:
            try:
                # Convert record's loom_no to integer for comparison
                record_loom_no = int(record['loom_no'])
                if record_loom_no == loom_no:
                    latest_beam = record['beam_no']
                    logger.debug(f"Found latest beam {latest_beam} for loom {loom_no}")
                    break
            except ValueError:
                logger.error(f"Invalid loom number in record: {record}")
                continue

        if latest_beam:
            # Check beam status
            sorted_beam_records = sorted(beam_records,
                                      key=lambda x: x.get('timestamp', ''),
                                      reverse=True)

            for record in sorted_beam_records:
                if record['beam_no'] == latest_beam:
                    if record['status'] == 'Beam End':
                        logger.debug(f"Beam {latest_beam} has ended")
                        return None
                    logger.debug(f"Returning active beam {latest_beam}")
                    return latest_beam

        logger.debug(f"Returning latest beam {latest_beam}")
        return latest_beam

    except Exception as e:
        logger.error(f"Error in get_beam_for_loom_v2: {str(e)}")
        return None

def get_current_status(loom_no):
    """Get current status for a loom"""
    beam_records = read_json_file('beam_on_loom')

    # Find latest process for the loom
    latest_record = None
    for record in sorted(beam_records, key=lambda x: x.get('timestamp', ''), reverse=True):
        if record['loom_no'] == loom_no:
            latest_record = record
            break

    if latest_record:
        if latest_record['status'] == 'Beam End':
            return None  # Loom is available for new beam
        return latest_record['status']

    # If no beam_on_loom record, check initiate_beam
    initiate_records = read_json_file('initiate_beam')
    for record in sorted(initiate_records, key=lambda x: x['timestamp'], reverse=True):
        if record['loom_no'] == loom_no:
            return 'Beam Start'

    return None

@app.route('/beam-on-loom', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager', 'production')
def beam_on_loom():
    """Handle beam on loom operations"""
    try:
        form = BeamOnLoomForm()
        logger.debug("Starting beam_on_loom route")

        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
                logger.debug(f"Received JSON data: {data}")

                # Validate required fields
                required_fields = ['location', 'loom_no', 'beam_no', 'status', 'status_datetime', 'role', 'name']
                for field in required_fields:
                    if not data.get(field):
                        logger.error(f"Missing required field: {field}")
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400

                try:
                    # Parse loom number
                    loom_no = int(data['loom_no'])
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid loom number format'
                    }), 400

                # Validate status transition
                current_status = get_current_status(loom_no)
                next_valid_status = get_next_status(current_status)
                if data['status'] != next_valid_status:
                    logger.error(f"Invalid status transition. Current: {current_status}, Received: {data['status']}, Expected: {next_valid_status}")
                    return jsonify({
                        'success': False,
                        'error': f'Invalid status transition. Expected: {next_valid_status}'
                    }), 400

                try:
                    # Parse the datetime string in the format provided by Flatpickr
                    status_datetime = datetime.strptime(data['status_datetime'], '%Y-%m-%d %H:%M')
                    logger.debug(f"Parsed datetime: {status_datetime}")

                    # Validate datetime is not in future
                    if status_datetime > datetime.now():
                        return jsonify({
                            'success': False,
                            'error': 'Status datetime cannot be in the future'
                        }), 400
                except ValueError as e:
                    logger.error(f"Error parsing datetime: {e}")
                    return jsonify({
                        'success': False,
                        'error': 'Invalid datetime format. Expected format: YYYY-MM-DD HH:MM'
                    }), 400

                # Create record
                record = {
                    'beam_no': data['beam_no'],
                    'loom_no': loom_no,
                    'location': data['location'],
                    'status': data['status'],
                    'role': data['role'],
                    'name': data['name'],
                    'timestamp': status_datetime.strftime('%Y-%m-%d %H:%M')
                }

                try:
                    # Save the record
                    records = read_json_file('beam_on_loom')
                    records.append(record)
                    write_json_file('beam_on_loom', records)
                    logger.info(f"Successfully added new record for beam {data['beam_no']} on loom {loom_no}")

                    return jsonify({
                        'success': True,
                        'message': 'Status updated successfully'
                    })
                except Exception as e:
                    logger.error(f"Error saving record: {e}")
                    return jsonify({
                        'success': False,
                        'error': 'Error saving record'
                    }), 500

        # Handle GET request
        elif request.method == 'GET':
            if form.location.data:
                logger.debug(f"Getting looms for location: {form.location.data}")
                looms = get_available_looms_v2(form.location.data)
                logger.debug(f"Available looms returned: {looms}")
                form.loom_no.choices = [('', 'Select Loom')] + [(str(l), str(l)) for l in looms]

            if form.loom_no.data:
                logger.debug(f"Getting beam for loom: {form.loom_no.data}")
                beam_no = get_beam_for_loom_v2(int(form.loom_no.data))
                logger.debug(f"Got beam_no: {beam_no}")
                if beam_no:
                    form.beam_no.choices = [(beam_no, beam_no)]
                    current_status = get_current_status(int(form.loom_no.data))
                    logger.debug(f"Current status for loom {form.loom_no.data}: {current_status}")
                    if current_status:
                        next_status = get_next_status(current_status)
                        logger.debug(f"Setting next status to: {next_status}")
                        form.status.data = next_status
                else:
                    form.beam_no.choices = [('', 'Select Beam No')]

            if form.role.data:
                users = get_users_by_role(form.role.data)
                form.name.choices = [('', 'Select Name')] + [(u, u) for u in users]

        # Get records for display
        records = read_json_file('beam_on_loom')
        records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Render template
        return render_template('beam_on_loom.html', form=form, records=records)

    except Exception as e:
        logger.error(f'Error in beam_on_loom: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/looms-v2/<path:location>')
def get_looms_v2(location):
    """API endpoint to get available looms for beam on loom page"""
    try:
        logger.debug(f"Fetching looms for location (v2): {location}")
        looms = get_available_looms_v2(location)
        logger.debug(f"Found looms (v2): {looms}")
        return jsonify({
            'success': True,
            'looms': [{'id': str(loom), 'text': str(loom)} for loom in looms]
        })
    except Exception as e:
        logger.error(f"Error in get_looms_v2 API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/beam-v2/<int:loom_no>')
def get_beam_info(loom_no):
    """Get beam number and next status for a loom"""
    try:
        beam_no = get_beam_for_loom_v2(loom_no)  # Using new version
        current_status = get_current_status(loom_no)
        next_status = get_next_status(current_status) if current_status else 'Beam Start'

        return jsonify({
            'success': True,
            'beam_no': beam_no,
            'next_status': next_status
        })
    except Exception as e:
        logger.error(f'Error getting beam info: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/users/<role>')
def get_users_for_role(role):
    """API endpoint to get users for a specific role"""
    try:
        logger.debug(f"Fetching users for role: {role}")

        # Check if data directory exists
        if not os.path.exists(DATA_DIR):
            logger.error(f"Data directory not found: {DATA_DIR}")
            return jsonify({
                'success': False,
                'error': 'Data directory not found'
            }), 500

        # Check if user management file exists
        user_file = os.path.join(DATA_DIR, 'user_management.json')
        if not os.path.exists(user_file):
            logger.error(f"User management file not found: {user_file}")
            return jsonify({
                'success': False,
                'error': 'User management file not found'
            }), 500

        # Read user data
        with open(user_file, 'r') as f:
            users = json.load(f)

        logger.debug(f"Loaded {len(users)} users from file")

        # Filter users by role
        matching_users = []
        for user in users:
            user_roles = user.get('roles', [])
            logger.debug(f"Checking user {user.get('name')} with roles: {user_roles}")
            if role in user_roles:
                matching_users.append(user['name'])

        logger.debug(f"Found {len(matching_users)} matching users for role {role}")

        return jsonify({
            'success': True,
            'users': matching_users
        })

    except Exception as e:
        logger.error(f"Error in get_users_for_role: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/check-users')
def check_users():
    """Debug endpoint to check user management data"""
    try:
        user_file = os.path.join(DATA_DIR, 'user_management.json')
        if not os.path.exists(user_file):
            return jsonify({
                'success': False,
                'error': 'User management file not found',
                'path': user_file
            })

        with open(user_file, 'r') as f:
            users = json.load(f)

        return jsonify({
            'success': True,
            'user_count': len(users),
            'users': users,
            'data_dir': DATA_DIR,
            'user_file': user_file
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# =============================================================================
# Dashboard Routes and Utilities
# =============================================================================
from datetime import datetime, timedelta
from collections import defaultdict

def calculate_combo_delay(order_date, stages):
    """Calculate delay for a production combo based on stages and thresholds"""
    if not order_date:
        return 0

    # Convert order_date string to datetime if needed
    if isinstance(order_date, str):
        order_date = datetime.strptime(order_date, '%Y-%m-%d')

    today = datetime.now().date()
    days_since_order = (today - order_date.date()).days

    # Expected timeline thresholds (in days)
    STAGE_THRESHOLDS = {
        'warping': 3,
        'sizing': 5,
        'beam_on_loom': 7,
        'grey': 10
    }

    # Find the last completed stage
    completed_stages = sum(1 for stage in stages.values() if stage)

    if completed_stages == 0:
        threshold = STAGE_THRESHOLDS['warping']
    elif completed_stages == len(stages):
        return 0  # All stages complete, no delay
    else:
        # Get threshold for the current incomplete stage
        stage_names = list(STAGE_THRESHOLDS.keys())
        current_stage = stage_names[completed_stages]
        threshold = STAGE_THRESHOLDS[current_stage]

    delay = max(0, days_since_order - threshold)
    return delay

@app.route('/dashboards')
@login_required
def dashboards():
    """Main dashboard page showing summary metrics"""
    try:
        # Placeholder for summary metrics
        summary_metrics = {
            'total_orders': 0,
            'delayed_combos': 0,
            'active_beams': 0,
            'production_efficiency': 0
        }

        return render_template('dashboards/summary.html', metrics=summary_metrics)
    except Exception as e:
        logger.error(f'Error in main dashboard: {str(e)}')
        return str(e), 500

@app.route('/dashboards/delayed-combos')
@login_required
def delayed_combos_dashboard():
    """Detailed dashboard showing delayed production combinations"""
    try:
        # Get required data
        orderbook = read_json_file('orderbook')
        warping_production = read_json_file('warping_production')
        sizing_production = read_json_file('sizing_production')
        beam_on_loom = read_json_file('beam_on_loom')
        grey_production = read_json_file('grey_production')

        # Process production stages by combo
        combo_stages = defaultdict(lambda: {
            'warping': None,
            'sizing': None,
            'beam_on_loom': None,
            'grey': None
        })

        # Track earliest dates for each stage
        for record in warping_production:
            combo = f"{record['order_no']}_{record['design_no']}"
            date = datetime.strptime(record['timestamp'][:10], '%Y-%m-%d')
            if not combo_stages[combo]['warping'] or date < combo_stages[combo]['warping']:
                combo_stages[combo]['warping'] = date

        for record in sizing_production:
            # Find corresponding warping record to get order/design
            warping_record = next((w for w in warping_production if w['beam_no'] == record['beam_no']), None)
            if warping_record:
                combo = f"{warping_record['order_no']}_{warping_record['design_no']}"
                date = datetime.strptime(record['timestamp'][:10], '%Y-%m-%d')
                if not combo_stages[combo]['sizing'] or date < combo_stages[combo]['sizing']:
                    combo_stages[combo]['sizing'] = date

        for record in beam_on_loom:
            # Find corresponding warping record
            warping_record = next((w for w in warping_production if w['beam_no'] == record['beam_no']), None)
            if warping_record:
                combo = f"{warping_record['order_no']}_{warping_record['design_no']}"
                date = datetime.strptime(record['timestamp'][:10], '%Y-%m-%d')
                if not combo_stages[combo]['beam_on_loom'] or date < combo_stages[combo]['beam_on_loom']:
                    combo_stages[combo]['beam_on_loom'] = date

        for record in grey_production:
            design_no = record['design_no']
            # Find matching orderbook record for order number
            order_record = next((o for o in orderbook if o['Design No.'] == design_no), None)
            if order_record:
                combo = f"{order_record['Order No.']}_{design_no}"
                date = datetime.strptime(record['date'], '%Y-%m-%d')
                if not combo_stages[combo]['grey'] or date < combo_stages[combo]['grey']:
                    combo_stages[combo]['grey'] = date

        # Process orderbook and add delays
        delayed_items = []
        for item in orderbook:
            if not item.get('Office Date'):
                continue

            order_date = datetime.strptime(item['Office Date'], '%Y-%m-%d')
            combo = f"{item['Order No.']}_{item['Design No.']}"
            stages = combo_stages[combo]

            delay = calculate_combo_delay(order_date, stages)
            if delay >= 10:  # Only show items delayed 10 or more days
                item_data = dict(item)
                item_data['stages'] = stages
                item_data['combo_delay'] = delay
                delayed_items.append(item_data)

        # Sort by delay (descending)
        delayed_items.sort(key=lambda x: x['combo_delay'], reverse=True)

        return render_template(
            'dashboards/delayed_combos.html',
            data=delayed_items,
            total_delayed=len(delayed_items)
        )

    except Exception as e:
        logger.error(f'Error in delayed combos dashboard: {str(e)}')
        logger.error(traceback.format_exc())
        return str(e), 500


@app.route('/dashboards/status-update')
@login_required
def status_update_dashboard():
    """Status Update Dashboard showing current production status of all orders"""
    try:
        return render_template('dashboards/status_update.html')
    except Exception as e:
        logger.error(f'Error in status update dashboard: {str(e)}')
        logger.error(traceback.format_exc())
        return str(e), 500

@app.route('/api/orderbook')
def get_orderbook():
    """API endpoint to get orderbook data"""
    try:
        with open('data/orderbook.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded orderbook data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading orderbook: {str(e)}")
        return jsonify([])

@app.route('/api/warping-production')
def get_warping_production():
    """API endpoint to get warping production data"""
    try:
        with open('data/warping_production.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded warping data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading warping data: {str(e)}")
        return jsonify([])

@app.route('/api/beam-on-loom')
def get_beam_on_loom():
    """API endpoint to get beam on loom data"""
    try:
        with open('data/beam_on_loom.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded beam data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading beam data: {str(e)}")
        return jsonify([])

@app.route('/api/unit259-production')
def get_unit259_production():
    """API endpoint to get unit 259 production data"""
    try:
        with open('data/unit259_production.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded unit259 data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading unit259 data: {str(e)}")
        return jsonify([])

@app.route('/api/sizing-production')
def get_sizing_production():
    """API endpoint to get sizing production data"""
    try:
        with open('data/sizing_production.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded sizing data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading sizing data: {str(e)}")
        return jsonify([])

@app.route('/api/grey-production')
def get_grey_production():
    """API endpoint to get grey production data"""
    try:
        with open('data/grey_production.json', 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded grey production data: {len(data)} records")
            return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading grey production data: {str(e)}")
        return jsonify([])

@app.route('/grey-efficiency')
@login_required
@roles_required('admin', 'manager', 'production')
def grey_efficiency():
    return render_template('grey_efficiency.html')



