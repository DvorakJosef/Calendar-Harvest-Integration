"""
Input validation and sanitization module
Provides comprehensive validation for all API endpoints
"""

from marshmallow import Schema, fields, validate, ValidationError, pre_load
from flask import jsonify
from functools import wraps
import re
import html
from datetime import datetime, date


class SecurityValidationError(Exception):
    """Custom exception for security validation failures"""
    pass


def sanitize_string(value):
    """Sanitize string input to prevent XSS"""
    if not isinstance(value, str):
        return value
    
    # HTML escape
    value = html.escape(value)
    
    # Remove potentially dangerous characters
    value = re.sub(r'[<>"\']', '', value)
    
    # Limit length
    if len(value) > 1000:
        raise ValidationError("Input too long (max 1000 characters)")
    
    return value.strip()


def sanitize_email(value):
    """Sanitize and validate email"""
    if not isinstance(value, str):
        return value
    
    value = value.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError("Invalid email format")
    
    return value


class BaseSchema(Schema):
    """Base schema with common validation"""
    
    @pre_load
    def sanitize_inputs(self, data, **kwargs):
        """Sanitize all string inputs"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = sanitize_string(value)
        return data


class MappingSchema(BaseSchema):
    """Schema for project mapping validation"""
    calendar_label = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=200),
            validate.Regexp(r'^[a-zA-Z0-9\s\-_\.]+$', error="Invalid characters in label")
        ]
    )
    harvest_project_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=999999999)
    )
    harvest_project_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200)
    )
    harvest_task_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=999999999)
    )
    harvest_task_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200)
    )


class ProcessingOptionsSchema(BaseSchema):
    """Schema for processing options validation"""
    dry_run = fields.Bool(load_default=False)
    force_overwrite = fields.Bool(load_default=False)
    round_hours = fields.Bool(load_default=False)
    preview_mode = fields.Bool(load_default=False)


class ProcessingSchema(BaseSchema):
    """Schema for timesheet processing validation"""
    week_start = fields.Date(required=True)
    timesheet_entries = fields.List(fields.Dict(), required=True)
    options = fields.Nested(ProcessingOptionsSchema, load_default={})


class PatternRuleSchema(BaseSchema):
    """Schema for pattern rule validation"""
    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=100),
            validate.Regexp(r'^[a-zA-Z0-9\s\-_\.]+$', error="Invalid characters in name")
        ]
    )
    pattern_type = fields.Str(
        required=True,
        validate=validate.OneOf(['contains', 'starts_with', 'ends_with', 'regex'])
    )
    pattern_value = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200)
    )
    harvest_project_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=999999999)
    )
    harvest_task_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=999999999)
    )
    case_sensitive = fields.Bool(load_default=False)


class BulkAssignmentSchema(BaseSchema):
    """Schema for bulk assignment validation"""
    assignments = fields.List(
        fields.Dict(keys=fields.Str(), values=fields.Raw()),
        required=True,
        validate=validate.Length(min=1, max=100)
    )


class ImportDataSchema(BaseSchema):
    """Schema for import data validation"""
    import_data = fields.List(
        fields.Dict(),
        required=True,
        validate=validate.Length(min=1, max=1000)
    )
    merge_strategy = fields.Str(
        load_default='update',
        validate=validate.OneOf(['update', 'skip', 'replace'])
    )


def validate_json(schema_class):
    """Decorator to validate JSON input against a schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get JSON data
                from flask import request
                data = request.get_json()
                
                if data is None:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON data'
                    }), 400
                
                # Validate against schema
                schema = schema_class()
                validated_data = schema.load(data)
                
                # Add validated data to kwargs
                kwargs['validated_data'] = validated_data
                
                return f(*args, **kwargs)
                
            except ValidationError as e:
                print(f"❌ VALIDATION ERROR in {schema_class.__name__}: {e.messages}")
                print(f"📥 Raw data that failed validation: {data}")
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'details': e.messages
                }), 400
            except SecurityValidationError as e:
                return jsonify({
                    'success': False,
                    'error': f'Security validation failed: {str(e)}'
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': 'Validation error occurred'
                }), 500
        
        return decorated_function
    return decorator


def validate_user_id(user_id):
    """Validate user ID parameter"""
    if not isinstance(user_id, int) or user_id <= 0:
        raise SecurityValidationError("Invalid user ID")
    return user_id


def validate_date_range(start_date, end_date=None):
    """Validate date range"""
    if not isinstance(start_date, (date, datetime)):
        raise SecurityValidationError("Invalid start date")
    
    if end_date and not isinstance(end_date, (date, datetime)):
        raise SecurityValidationError("Invalid end date")
    
    if end_date and start_date > end_date:
        raise SecurityValidationError("Start date cannot be after end date")
    
    # Prevent queries for dates too far in the past or future
    from datetime import timedelta
    today = date.today()
    max_past = today - timedelta(days=365 * 2)  # 2 years ago
    max_future = today + timedelta(days=365)    # 1 year ahead
    
    if start_date < max_past:
        raise SecurityValidationError("Date too far in the past")
    
    if start_date > max_future:
        raise SecurityValidationError("Date too far in the future")
    
    return True


def validate_harvest_ids(project_id, task_id):
    """Validate Harvest project and task IDs"""
    if not isinstance(project_id, int) or project_id <= 0:
        raise SecurityValidationError("Invalid project ID")
    
    if not isinstance(task_id, int) or task_id <= 0:
        raise SecurityValidationError("Invalid task ID")
    
    return True


# Export commonly used validators
__all__ = [
    'validate_json',
    'MappingSchema',
    'ProcessingSchema',
    'PatternRuleSchema',
    'BulkAssignmentSchema',
    'ImportDataSchema',
    'validate_user_id',
    'validate_date_range',
    'validate_harvest_ids',
    'SecurityValidationError'
]
