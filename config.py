geo_data = {
    'Supervisor District': {
        'geojson' : 'https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services/OpenData_S1/FeatureServer/17/query?outFields=*&where=1%3D1&f=geojson',
        'bounds_on' : 'DISTRICT',
        'df_on' : 'DISTRICT_1'
    },
    'Police District': {
        'geojson' : 'https://services9.arcgis.com/kYvfX7YK8OobHItA/ArcGIS/rest/services/FairfaxPoliceStationBoundaries/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson',
        'bounds_on' : 'STATION_NAME',
        'df_on' : 'Station Name'
    },
    'Patrol Area': {
        'geojson' : 'https://services9.arcgis.com/kYvfX7YK8OobHItA/ArcGIS/rest/services/FairfaxPolicePatrolAreas/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson',
        'bounds_on' : 'PATROL_AREA', 
        'df_on' : 'Patrol Area'
    },
    'Emergency Service Zone': {
        'geojson' : 'https://services9.arcgis.com/kYvfX7YK8OobHItA/ArcGIS/rest/services/Police_ESZ_EmergencyServiceZone/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson',
        'bounds_on' : 'cad_esz',  
        'df_on' : 'ESZ (Emergency Service Zones)'
    },
    'Individual Locations': {}
}

crs = "EPSG:2283"