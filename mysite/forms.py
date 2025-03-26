# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SelectField, TextAreaField, IntegerField, ValidationError, SelectMultipleField, SubmitField, DateTimeField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from datetime import datetime, date

# User Management
# User Management Roles grouped by production area
WARPING_ROLES = ['Warper']
SIZING_ROLES = ['Sizer']
BEAM_ROLES = ['Beam Knotter & Drawer', 'Beam Getter', 'Beam QC']
GREY_ROLES = ['Grey Weaver', 'Grey Reliever', 'Grey Foreman', 'QC Checker']

# Combined roles list
ROLES = WARPING_ROLES + SIZING_ROLES + BEAM_ROLES + GREY_ROLES

# Role groupings for template rendering
ROLE_GROUPS = {
    'Warping Production Roles': WARPING_ROLES,
    'Sizing Production Roles': SIZING_ROLES,
    'Beam on Loom Roles': BEAM_ROLES,
    'Grey Production Roles': GREY_ROLES
}

# def update_form_choices(form):
#     """Update form choices based on user roles"""
#     if hasattr(form, 'warper_name'):
#         warpers = get_users_by_role('Warper')
#         form.warper_name.choices = [('', 'Select Warper')] + [(name, name) for name in warpers]

#     if hasattr(form, 'sizer_name'):
#         sizers = get_users_by_role('Sizer')
#         form.sizer_name.choices = [('', 'Select Sizer')] + [(name, name) for name in sizers]

#     if hasattr(form, 'weaver_name'):
#         weavers = get_users_by_role('Grey Weaver')
#         form.weaver_name.choices = [('', 'Select Weaver')] + [(name, name) for name in weavers]

#     if hasattr(form, 'reliever_name'):
#         relievers = get_users_by_role('Grey Reliever')
#         form.reliever_name.choices = [('', 'Select Reliever')] + [(name, name) for name in relievers]

#     if hasattr(form, 'foreman_name'):
#         foremen = get_users_by_role('Grey Foreman')
#         form.foreman_name.choices = [('', 'Select Foreman')] + [(name, name) for name in foremen]

#     if hasattr(form, 'qc_name'):
#         qc_checkers = get_users_by_role('Grey QC')
#         form.qc_name.choices = [('', 'Select QC Checker')] + [(name, name) for name in qc_checkers]

#     # For Beam on Loom roles
#     if hasattr(form, 'beam_knotter_name'):
#         knotters = get_users_by_role('Beam Knotter / Drawer')
#         form.beam_knotter_name.choices = [('', 'Select Knotter/Drawer')] + [(name, name) for name in knotters]

#     if hasattr(form, 'beam_getter_name'):
#         getters = get_users_by_role('Beam Getter')
#         form.beam_getter_name.choices = [('', 'Select Getter')] + [(name, name) for name in getters]

#     if hasattr(form, 'beam_qc_name'):
#         qc_checkers = get_users_by_role('Beam QC')
#         form.beam_qc_name.choices = [('', 'Select QC')] + [(name, name) for name in qc_checkers]

class UserManagementForm(FlaskForm):
    """Form for user management"""
    name = StringField('Name', validators=[DataRequired()])
    roles = SelectMultipleField('Roles', choices=[(role, role) for role in ROLES])
    submit = SubmitField('Submit')

class WarpingProductionForm(FlaskForm):
    order_no = SelectField(
        'Order No.',
        validators=[DataRequired()],
        choices=[],  # Will be populated dynamically
        coerce=str,  # Ensure string values are accepted
        render_kw={
            "class": "select2",
            "data-placeholder": "Search and select order number"
        }
    )

    design_no = SelectField(
        'Design No.',
        validators=[DataRequired()],
        choices=[],  # Will be populated dynamically
        coerce=str,  # Ensure string values are accepted
        render_kw={
            "class": "select2",
            "data-placeholder": "Select design number"
        }
    )

    machine_no = SelectField(
        'Machine No.',
        validators=[DataRequired()],
        choices=[('', 'Select Machine No.')] + [(str(i), str(i)) for i in range(1, 8)],
        render_kw={"class": "select2"}
    )

    beam_no = IntegerField(
        'Beam No.',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="Enter a valid Beam Number")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter Beam No"
        }
    )

    start_datetime = DateTimeField(
        'Start Date & Time',
        validators=[DataRequired()],
        # Changed format string to match exactly what Flatpickr will send
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "placeholder": "Select start date and time",
            "data-input": ""  # Required for Flatpickr
        }
    )

    end_datetime = DateTimeField(
        'End Date & Time',
        validators=[DataRequired()],
        # Changed format string to match exactly what Flatpickr will send
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "placeholder": "Select end date and time",
            "data-input": ""  # Required for Flatpickr
        }
    )

    def validate_end_datetime(self, field):
        """Validate that end datetime is after start datetime"""
        if self.start_datetime.data and field.data:
            if field.data <= self.start_datetime.data:
                raise ValidationError('End date & time must be after start date & time')

    rpm = IntegerField(
        'RPM',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="RPM must be greater than 0")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter RPM"
        }
    )

    quantity = IntegerField(
        'Quantity (Meters)',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="Quantity must be greater than 0")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter quantity in meters"
        }
    )

    warper_name = SelectField(
        'Warper Name',
        validators=[DataRequired()],
        choices=[('', 'Select Warper')],  # Choices will be populated dynamically
        render_kw={"class": "select2"}
    )

    sections = IntegerField(
        'Sections',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="Number of sections must be at least 1")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter number of sections"
        }
    )

    breakages = IntegerField(
        'Breakages',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Breakages cannot be negative")
        ],
        render_kw={
            "min": "0",
            "placeholder": "Enter number of breakages"
        }
    )

    comments = TextAreaField(
        'Comments',
        validators=[Optional(), Length(max=500)],
        render_kw={
            "placeholder": "Enter any additional comments or notes",
            "maxlength": "500",
            "rows": "3"
        }
    )

class WarpingDispatchForm(FlaskForm):
    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        coerce=str,
        render_kw={
            "class": "select2",
            "placeholder": "Select beam number"
        }
    )

    dispatch_status = SelectField(
        'Dispatch Status',
        choices=[
            ('', 'Select status'),
            ('Yes', 'Dispatched')
        ],
        default='Yes',
        validators=[DataRequired()],
        render_kw={"class": "select2"}
    )

    date = DateField(
        'Date',
        validators=[DataRequired()],
        default=date.today,
        render_kw={"type": "date"}
    )

    def validate_date(self, field):
        """Validate that dispatch date is not in the future"""
        if field.data > date.today():
            raise ValidationError('Dispatch date cannot be in the future')

class SizingProductionForm(FlaskForm):
    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        coerce=str,
        render_kw={
            "class": "select2",
            "placeholder": "Select beam number"
        }
    )

    status = SelectField(
        'Status',
        choices=[
            ('', 'Select status'),
            ('Yes', 'Sized')
        ],
        default='Yes',
        validators=[DataRequired()],
        render_kw={"class": "select2"}
    )

    sizer_name = SelectField(
        'Sizer Name',
        validators=[DataRequired()],
        choices=[('', 'Select Sizer')],  # Choices will be populated dynamically
        render_kw={"class": "form-control"}
    )

    start_datetime = DateTimeField(
        'Start Date & Time',
        validators=[DataRequired()],
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "data-input": "",
            "placeholder": "Select start date and time"
        }
    )

    end_datetime = DateTimeField(
        'End Date & Time',
        validators=[DataRequired()],
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "data-input": "",
            "placeholder": "Select end date and time"
        }
    )

    rf = FloatField(
        'RF',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="RF must be greater than or equal to 0")
        ],
        render_kw={
            "min": "0",
            "step": "0.1",
            "placeholder": "Enter RF value"
        }
    )

    moisture = FloatField(
        'Moisture',
        validators=[
            DataRequired(),
            NumberRange(min=0, max=100, message="Moisture must be between 0 and 100")
        ],
        render_kw={
            "min": "0",
            "max": "100",
            "step": "0.1",
            "placeholder": "Enter moisture percentage"
        }
    )

    speed = FloatField(
        'Speed',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Speed must be greater than 0")
        ],
        render_kw={
            "min": "0",
            "step": "0.1",
            "placeholder": "Enter speed"
        }
    )

    comments = TextAreaField(
        'Comments',
        validators=[Optional(), Length(max=500)],
        render_kw={
            "placeholder": "Enter any additional comments or notes",
            "maxlength": "500",
            "rows": "3"
        }
    )

    def validate_end_datetime(self, field):
        """Validate that end datetime is after start datetime"""
        if self.start_datetime.data and field.data:
            if field.data <= self.start_datetime.data:
                raise ValidationError('End date & time must be after start date & time')

class SizingDispatchForm(FlaskForm):
    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        coerce=str,
        choices=[],  # Choices will be populated in the route
        render_kw={
            "class": "select2",
            "placeholder": "Select beam number"
        }
    )

    dispatch_status = SelectField(
        'Dispatch Status',
        choices=[
            ('', 'Select status'),
            ('Yes', 'Dispatched')
        ],
        default='Yes',
        validators=[DataRequired()],
        render_kw={"class": "select2"}
    )

    date = DateField(
        'Date',
        validators=[DataRequired()],
        default=date.today,
        render_kw={"type": "date"}
    )

    def validate_date(self, field):
        """Validate that dispatch date is not in the future"""
        if field.data > date.today():
            raise ValidationError('Dispatch date cannot be in the future')

class BeamOnLoomForm(FlaskForm):
    location = SelectField(
        'Location',
        validators=[DataRequired()],
        choices=[
            ('', 'Select Location'),
            ('212/1', 'Unit 212/1'),
            ('259/1', 'Unit 259/1')
        ],
        render_kw={"class": "select2"}
    )

    loom_no = SelectField(
        'Loom No.',
        validators=[DataRequired()],
        choices=[],  # Populated dynamically
        render_kw={"class": "select2"}
    )

    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        choices=[],  # Populated dynamically
        render_kw={"class": "select2"}
    )

    status = StringField(
        'Status',
        render_kw={"readonly": True}
    )

    status_datetime = DateTimeField(
        'Status Date & Time',
        validators=[DataRequired()],
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "data-input": "",
            "placeholder": "Select date and time"
        }
    )

    role = SelectField(
        'Role',
        validators=[DataRequired()],
        choices=[
            ('', 'Select Role'),
            ('Beam Knotter & Drawer', 'Beam Knotter & Drawer'),
            ('Beam Getter', 'Beam Getter'),
            ('Beam QC', 'Beam QC')
        ],
        render_kw={"class": "select2"}
    )

    name = SelectField(
        'Name',
        validators=[DataRequired()],
        choices=[],  # Populated dynamically based on role
        render_kw={"class": "select2"}
    )

    def validate_status_datetime(self, field):
        if field.data > datetime.now():
            raise ValidationError('Status date & time cannot be in the future')

# class BeamOnLoomForm(FlaskForm):
#     beam_no = SelectField(
#         'Beam No.',
#         validators=[DataRequired(message="Please select a beam number")],
#         coerce=str,
#         choices=[],  # Choices populated in route
#         render_kw={
#             "class": "select2",
#             "data-placeholder": "Select beam number"
#         }
#     )

#     loom_no = IntegerField(
#         'Loom No.',
#         validators=[
#             DataRequired(message=""),
#             NumberRange(min=1, message="Loom number must be greater than 0")
#         ],
#         render_kw={
#             "min": "1",
#             "placeholder": "Enter loom number"
#         }
#     )

#     status = SelectField(
#         'Status',
#         choices=[
#             ('', 'Select Status'),
#             ('Beam on Loom', 'Beam on Loom'),
#             ('Knotting / Drawing', 'Knotting / Drawing'),
#             ('Getting', 'Getting'),
#             ('QC', 'QC'),
#             ('Beam End', 'Beam End')
#         ],
#         validators=[DataRequired(message="Please select a status")],
#         render_kw={
#             "class": "select2",
#             "data-placeholder": "Select status"
#         }
#     )

#     process_update = SelectField(
#         'Process Update',
#         choices=[
#             ('', 'Select Update'),
#             ('Start', 'Start'),
#             ('End', 'End')
#         ],
#         validators=[DataRequired(message="Please select a process update")],
#         render_kw={
#             "class": "select2",
#             "data-placeholder": "Select update"
#         }
#     )

#     date = DateField(
#         'Date',
#         validators=[DataRequired(message="Date is required")],
#         default=date.today,
#         render_kw={"type": "date"}
#     )

#     time = TimeField(
#         'Time',
#         validators=[DataRequired(message="Time is required")],
#         render_kw={
#             "type": "time",
#             "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
#         }
#     )

#     name = StringField(
#         'Name',
#         validators=[
#             DataRequired(message="Name is required"),
#             Length(min=2, max=50, message="Name must be between 2 and 50 characters")
#         ],
#         render_kw={
#             "placeholder": "Enter name",
#             "class": "form-input"
#         }
#     )

#     role = SelectField(
#         'Role',
#         choices=[
#             ('', 'Select Role'),
#             ('Beam Start', 'Beam Start'),
#             ('Knotter / Drawer', 'Knotter / Drawer'),
#             ('Beam Getter', 'Beam Getter'),
#             ('QC', 'QC'),
#             ('Beam End', 'Beam End')
#         ],
#         validators=[DataRequired(message="Please select a role")],
#         render_kw={
#             "class": "select2",
#             "data-placeholder": "Select role"
#         }
#     )

#     def validate_date(self, field):
#         """Validate that date is not in the future"""
#         if field.data > date.today():
#             raise ValidationError('Date cannot be in the future')

class GreyProductionForm(FlaskForm):
    date = DateField(
        'Date',
        validators=[DataRequired()],
        default=date.today,
        render_kw={"type": "date"}
    )

    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        coerce=str,
        choices=[],  # Will be populated dynamically
        render_kw={
            "class": "select2",
            "data-placeholder": "Select beam number"
        }
    )

    loom_no = IntegerField(
        'Loom No.',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="Loom number must be greater than 0")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter loom number"
        }
    )

    piece_no = StringField(
        'Piece No.',
        validators=[
            DataRequired(),
            Length(min=1, max=20, message="Piece number must be between 1 and 20 characters")
        ],
        render_kw={"placeholder": "Enter piece number"}
    )

    design_no = StringField(
        'Design No.',
        render_kw={
            "readonly": True,
            "placeholder": "Design number will be auto-populated"
        }
    )

    production_meters = FloatField(
        'Production (Meters)',
        validators=[
            DataRequired(),
            NumberRange(min=0.1, message="Production meters must be greater than 0")
        ],
        render_kw={
            "min": "0.1",
            "step": "0.1",
            "placeholder": "Enter production in meters"
        }
    )

    production_weight = FloatField(
        'Production (Weight)',
        validators=[
            DataRequired(),
            NumberRange(min=0.1, message="Production weight must be greater than 0")
        ],
        render_kw={
            "min": "0.1",
            "step": "0.1",
            "placeholder": "Enter production weight"
        }
    )

    remarks = TextAreaField(
        'Remarks',
        validators=[Optional(), Length(max=500)],
        render_kw={
            "placeholder": "Enter any additional remarks",
            "maxlength": "500",
            "rows": "3"
        }
    )

class Unit259ProductionForm(FlaskForm):
    date = DateField(
        'Date',
        validators=[DataRequired()],
        default=date.today,
        render_kw={"type": "date"}
    )

    shift = SelectField(
        'Shift',
        validators=[DataRequired()],
        choices=[
            ('', 'Select Shift'),
            ('Day', 'Day (8am - 8pm)'),
            ('Night', 'Night (8pm - 8am)')
        ],
        render_kw={"class": "select2"}
    )

    loom_no = SelectField(
        'Loom No.',
        validators=[DataRequired()],
        choices=[],  # Will be populated dynamically
        render_kw={"class": "select2"}
    )

    design_no = StringField(
        'Design No.',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-populated from Beam on Loom"
        }
    )

    order_no = StringField(
        'Order No.',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-populated from Orderbook"
        }
    )

    reed = StringField(
        'Reed',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-populated from Orderbook"
        }
    )

    rpm = IntegerField(
        'RPM',
        validators=[
            DataRequired(),
            NumberRange(min=1, message="RPM must be greater than 0")
        ],
        render_kw={
            "min": "1",
            "placeholder": "Enter RPM"
        }
    )

    ppi = StringField(
        'PPI',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-populated from Orderbook"
        }
    )

    reading = FloatField(
        'Reading',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Reading cannot be negative")
        ],
        render_kw={
            "min": "0",
            "step": "0.01",
            "placeholder": "Enter reading"
        }
    )

    warp = IntegerField(
        'Warp',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Warp cannot be negative")
        ],
        render_kw={
            "min": "0",
            "placeholder": "Enter warp"
        }
    )

    weft = IntegerField(
        'Weft',
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Weft cannot be negative")
        ],
        render_kw={
            "min": "0",
            "placeholder": "Enter weft"
        }
    )

    efficiency = FloatField(
        'Efficiency',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-calculated"
        }
    )

    shift_hours = SelectField(
        'Shift Hours',
        validators=[DataRequired()],
        choices=[(str(i), str(i)) for i in range(13)],  # 0-12 hours
        render_kw={"class": "select2"}
    )

    shift_minutes = SelectField(
        'Shift Minutes',
        validators=[DataRequired()],
        choices=[(str(i), str(i)) for i in range(0, 60, 10)],  # 0-50 minutes in steps of 10
        default='0',
        render_kw={"class": "select2"}
    )

    production_meters = FloatField(
        'Production (Mtrs.)',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-calculated"
        }
    )

    loss_meters = FloatField(
        'Loss (Mtrs.)',
        render_kw={
            "readonly": True,
            "placeholder": "Auto-calculated"
        }
    )

    weaver_name = SelectField(
        'Weaver Name',
        validators=[DataRequired()],
        choices=[('', 'Select Weaver')],  # Choices will be populated dynamically
        render_kw={"class": "select2"}
    )

    reliever_name = SelectField(
        'Reliever Name',
        validators=[DataRequired()],
        choices=[('', 'Select Reliever')],  # Choices will be populated dynamically
        render_kw={"class": "select2"}
    )

    foreman = SelectField(
        'Foreman',
        validators=[DataRequired()],
        choices=[('', 'Select Foreman')],  # Choices will be populated dynamically
        render_kw={"class": "select2"}
    )

    qc_checker = SelectField(
        'Grey QCr',
        validators=[DataRequired()],
        choices=[('', 'Select QC Checker')],  # Choices will be populated dynamically
        render_kw={"class": "select2"}
    )

    comments = TextAreaField(
        'Comments',
        validators=[Optional(), Length(max=500)],
        render_kw={
            "placeholder": "Enter any additional comments",
            "maxlength": "500",
            "rows": "3"
        }
    )

class InitiateBeamForm(FlaskForm):
    location = SelectField(
        'Location',
        validators=[DataRequired()],
        choices=[
            ('', 'Select Location'),
            ('212/1', 'Unit 212/1'),
            ('259/1', 'Unit 259/1')
        ],
        render_kw={"class": "select2"}
    )

    beam_no = SelectField(
        'Beam No.',
        validators=[DataRequired()],
        choices=[],  # Populated dynamically
        render_kw={"class": "select2"}
    )

    loom_no = SelectField(
        'Loom No.',
        validators=[DataRequired()],
        choices=[],  # Populated dynamically
        render_kw={"class": "select2"}
    )

    start_datetime = DateTimeField(
        'Start Date & Time',
        validators=[DataRequired()],
        format='%Y-%m-%d %H:%M',
        render_kw={
            "class": "datetimepicker",
            "data-input": "",
            "placeholder": "Select start date and time"
        }
    )

    status = StringField(
        'Status',
        default='Beam Start',
        render_kw={"readonly": True}
    )
    
class close_order(FlaskForm):
    order_no = SelectField(label = 'Order No.',
    validators=[DataRequired()],render_kw={"class": "select2"})
    submit = SubmitField(label="Close Order")