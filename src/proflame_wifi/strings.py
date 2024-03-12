"""
Internal messages to be used in logging and error handling.
"""

BAD_ADDITION = 'Cannot add objects of type %s and %s'
BAD_SUBTRACTION = 'Cannot subtract objects of type %s and %s'
CONNECTION_ACKNOWLEDGED = 'Connection acknowledged'
INVALID_TEMPERATURE = 'Got invalid target temperature with no temperature unit - %s'
JSON_MSG_INVALID_SCHEMA = 'JSON message is not in a recognized format - %s'
JSON_MSG_INVALID_TYPE = 'JSON messaged is not an object - %s'
PING_ACKNOWLEDGED = 'Ping acknowledged'
UNKNOWN_CONTROL_MSG = 'Received unexpected control message - %s'
UNKNOWN_TEMPERATURE_UNIT = 'Failed to return temperature because temperature unit is unavailable'