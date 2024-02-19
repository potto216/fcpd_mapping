import folium
from folium import plugins
import geopandas as gpd
import numpy as np
import openpolicedata as opd
import pandas as pd
from shapely.geometry import Point
import streamlit as st
from streamlit_folium import st_folium

# Fairfax Detoxification Center: 44°56'52.6"N 93°14'41.5"W

st.set_page_config(layout='wide')

def hash_df(df: gpd.GeoDataFrame) -> dict:
    return pd.util.hash_pandas_object(df)

@st.cache_data(show_spinner="Fetching data")
def get_data(table_type, year):
    data = opd.Source(source_name="Fairfax County")
    table = data.load(year=year, table_type=table_type)
    table.standardize()
    df = table.table
    df['Patrol Area'] = df['Patrol Area'].apply(lambda x: int(x) if pd.notnull(x) and isinstance(x,str) and x.isdigit() else x)

    df = gpd.GeoDataFrame(df)
    # This reference https://law.lis.virginia.gov/vacodefull/title1/chapter6/ describes the Virginia State Plane North (NAD83) projection
    # The Virginia State Plane is referenced as EPSG:2283 NAD83 / Virginia North (ftUS) in https://epsg.io/2283
    df = df.set_geometry(df.apply(lambda x: Point(x['X Coordinate'], x['Y Coordinate']), axis=1),
                                crs="EPSG:2283").to_crs(epsg=4326)
    
    df['Statute Full'] = df.apply(lambda x: f"{x['Statute']}: {x['Statute Description']}", axis=1)
    return df


@st.cache_data(show_spinner="Loading County Boundary")
def get_county_bounds():
    geojson_link = 'https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/Fairfax_County_Boundary/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson'
    fairfax_county_boundary = gpd.read_file(geojson_link)
    return fairfax_county_boundary.to_crs(epsg=4326)

county_bounds = get_county_bounds()
bounds = county_bounds.total_bounds
lon_center = (bounds[0] + bounds[2]) / 2
lat_center = (bounds[1] + bounds[3]) / 2

@st.cache_data(show_spinner=False, hash_funcs={gpd.GeoDataFrame: hash_df})
def get_statute_options(df):
    vc = df['Statute Full'].value_counts().to_frame().reset_index()
    return vc.apply(lambda x: f"{x['Statute Full']} ({x['count']})", axis=1)


@st.cache_data(show_spinner="Loading boundaries")
def load_geojson(geojson_link):
    bounds = gpd.read_file(geojson_link)
    return bounds.to_crs(epsg=4326)

def Choropleth(geojson_link, df, bounds_on, df_on, data_label, tooltip_labels, test=None, skip_test=True, max_val=None, exclude=[], opacity=0.6):
    bounds = load_geojson(geojson_link)
    
    if len(exclude)>0:
        bounds = bounds[~bounds[bounds_on].isin(exclude)]

    if not skip_test:
        districts = bounds[bounds_on].unique()
        districts_arrests = df[df_on].unique()

        for d in districts_arrests:
            if d not in ['UNVERIFIED',-1, 0] and d not in districts and (not test or test(d)):
                raise ValueError(f"Unknown value: {d}")
        
    
    vc = df[df_on].astype(float).value_counts()
    vc.name = data_label

    bounds = bounds.drop_duplicates(subset=bounds_on)

    bounds = bounds.merge(vc, how='left', left_on=bounds_on, right_on=df_on)

    m = folium.Map(location=[lat_center, lon_center], zoom_start=10, min_zoom=10)

    geo = gpd.GeoSeries(bounds.set_index(bounds_on)['geometry']).to_json()

    num_bins = 10
    if not max_val:
        max_val = bounds[data_label].max()
        bins = np.linspace(0, max_val, num_bins)
    else:
        bins = np.append(np.linspace(0, max_val, num_bins-1), bounds[data_label].max())


    # https://towardsdatascience.com/how-to-step-up-your-folium-choropleth-map-skills-17cf6de7c6fe
    cp = folium.Choropleth(
        geo_data=geo,
        data=bounds,
        columns=[bounds_on, data_label],
        key_on = 'feature.id',
        legend_name = '# of Arrests',
        nan_fill_color='White',
        highlight=True,
        bins=bins,
        name="Data Plot",
        fill_opacity=opacity,
    ).add_to(m)

    # TODO: Replace NaN logos with 0's
    for row in cp.geojson.data['features']:
        row['properties'][bounds_on] = row['id']
        if (tf:=bounds[bounds_on].apply(str)==row['id']).any():
            val = bounds[data_label][tf].iloc[0]
            if pd.notnull(val):
                row['properties'][data_label] = str(int(val))
            else:
                row['properties'][data_label] = '0'
        else:
            row['properties'][data_label] = '0'
        
    folium.GeoJsonTooltip([bounds_on,data_label],aliases=tooltip_labels).add_to(cp.geojson)
    return m

geo_units = ['Supervisor District','Police District','Patrol Area','Emergency Service Zone', 'Individual Locations']
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
    }
}

with st.sidebar:
    table_type = st.selectbox("Data Type", ['ARRESTS'], help='Currently, only arrests 2022 data is available. More data will be available in the future '+
                              'Please notify if there is an immediate need for more data')
    
    year = st.selectbox("Data Year", [2022], help='Currently, only arrests 2022 data is available. More data will be available in the future '+
                              'Please notify if there is an immediate need for more data')
    
    map_type = st.selectbox('Geographic Unit (Most General to Most Specific)',
                            geo_units,
                            index=[k for k,x in enumerate(geo_units) if x=='Patrol Area'][0])
    
    df = get_data(table_type, year)

    options = get_statute_options(df)
    default = [x for x in options if x.startswith('5/1/2001: DRUNK IN PUBLIC OR PROFANE')]
    statutes = st.multiselect("Statutes", options, default=default, 
                   help='Type in this box to search for statutes')
    
    statutes = [x[:x.rfind(" (")] for x in statutes]

    df_rem = df[df['Statute Full'].isin(statutes)]

    races = st.multiselect("Race/Ethnicity", df_rem[opd.defs.columns.RE_GROUP_SUBJECT].unique(),
                           default=df_rem[opd.defs.columns.RE_GROUP_SUBJECT].unique(),
                           help='More demographics filters (gender, age) can be added')
    
    df_rem = df_rem[df_rem[opd.defs.columns.RE_GROUP_SUBJECT].isin(races)]

    st.text(f"Total Selected: {len(df_rem)}")

if map_type=='Individual Locations':
    m = folium.Map(location=[lat_center, lon_center], zoom_start=10)

    geo_j = gpd.GeoSeries(county_bounds.iloc[0]['geometry']).to_json()
    geo_j = folium.GeoJson(data=geo_j, style_function=lambda x: {"fillOpacity": 0.0}, name='County Boundary')

    points = [[point.xy[1][0], point.xy[0][0]] for point in df_rem.geometry]
    plugins.HeatMap(points, radius = 4, blur = 1, name="Data Plot").add_to(m)
    geo_j.add_to(m)
else:
    opacity = st.slider('Opacity', 0.0, 1.0, 0.6, step=0.05)
    m = Choropleth(geo_data[map_type]['geojson'], df_rem, geo_data[map_type]['bounds_on'], geo_data[map_type]['df_on'], 
               'ARRESTS', [f'{map_type}:','# of Arrests:'], opacity=opacity)
    
folium.LayerControl().add_to(m)   
st_data = st_folium(m, use_container_width=True)

st.divider()
st.markdown("The dashboard is generated using data from the "+
            "[Fairfax County Police Open Data Portal](https://www.fcpod.org/pages/crime-data). "+
            "[OpenPoliceData](https://openpolicedata.readthedocs.io/) was used to load data into this dashboard " +
            "and is freely available for others to easily download the raw data.")