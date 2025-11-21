from flask import Blueprint, request
from .controller import dispatch_drone

drone_bp = Blueprint('drone', __name__)

@drone_bp.route('/drone_dispatch', methods=['POST'])
def drone_dispatch():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    follow = data.get('follow', False)
    if lat and lon:
        dispatch_drone(lat, lon, follow)
        return {'status': 'Drone dispatched'}
    return {'error': 'Missing coordinates'}, 400
