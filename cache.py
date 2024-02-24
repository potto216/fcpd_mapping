import folium
from folium import plugins
import geopandas as gpd
import pandas as pd
import openpolicedata as opd
from shapely.geometry import Point
import streamlit as st

from config import geo_data

def hash_df(df: gpd.GeoDataFrame):
    return pd.util.hash_pandas_object(df)


@st.cache_data(show_spinner=False, hash_funcs={gpd.GeoDataFrame: hash_df})
def get_statute_options(df):
    vc = df['Statute Full'].value_counts().to_frame().reset_index()
    return vc.apply(lambda x: f"{x['Statute Full']} ({x['count']})", axis=1)


@st.cache_data(show_spinner=False)
def map_to_html(plot_dual, map_type, statutes, races, _m):
    return _m.get_root().render()


@st.cache_data(show_spinner="Loading boundaries")
def load_geojson(geojson_link):
    bounds = gpd.read_file(geojson_link)
    return bounds.to_crs(epsg=4326)


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

    cols_keeps = ['Statute Full', 'geometry', opd.defs.columns.RE_GROUP_SUBJECT]
    cols_keeps.extend([x['df_on'] for x in geo_data.values() if 'df_on' in x])
    df = df[cols_keeps]
    return df


@st.cache_data(show_spinner="Loading County Boundary")
def get_county_bounds():
    geojson_link = 'https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/Fairfax_County_Boundary/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson'
    fairfax_county_boundary = gpd.read_file(geojson_link)
    return fairfax_county_boundary.to_crs(epsg=4326)
